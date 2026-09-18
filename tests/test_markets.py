import csv
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from sports_stats_analyzer import markets
from sports_stats_analyzer.cli import app
from sports_stats_analyzer.normalization import normalize
from sports_stats_analyzer.storage import save_snapshot


def game(identifier, kickoff, status="FINISHED", home=1, away=2):
    return {
        "id": identifier,
        "utcDate": kickoff.isoformat(),
        "status": status,
        "competition": {"id": 2013, "code": "BSA", "name": "Brasileirão"},
        "season": {"id": 100, "startDate": "2026-01-01", "endDate": "2026-12-31"},
        "homeTeam": {"id": home, "name": f"T{home}"},
        "awayTeam": {"id": away, "name": f"T{away}"},
        "score": {
            "duration": "REGULAR",
            "fullTime": {
                "home": 2 if status == "FINISHED" else None,
                "away": 1 if status == "FINISHED" else None,
            },
        },
    }


def snapshot(db, games, observed):
    sid = save_snapshot(db, "competitions/BSA/matches", {}, {"matches": games})
    with sqlite3.connect(db) as connection:
        connection.execute(
            "UPDATE snapshots SET fetched_at=? WHERE id=?", (observed.isoformat(), sid)
        )
    normalize(db)
    return sid


@pytest.fixture
def setup(tmp_path, monkeypatch):
    db = tmp_path / "sports.db"
    current = datetime(2026, 6, 1, 12, tzinfo=UTC)
    monkeypatch.setattr(markets, "now", lambda: current)
    past = [
        game(i + 1, current - timedelta(days=120 - i), home=i % 4 + 1, away=(i + 1) % 4 + 1)
        for i in range(120)
    ]
    future = [game(1000 + i, current + timedelta(days=1), status="TIMED") for i in range(6)]
    snapshot(db, past + future, current - timedelta(minutes=1))
    return db, current, future


def quote(current, match_id=1000, **kwargs):
    return markets.Quote.model_validate(
        {
            "match_id": match_id,
            "market": "1x2",
            "selection": "home",
            "odds": "2.50",
            "line": None,
            "bookmaker": "Synthetic",
            "observed_at": current,
            "source": "synthetic-test",
            **kwargs,
        }
    )


def prepare(db, current, match_id=1000):
    forecast = markets.create_forecast(db, match_id)
    qid = markets.import_quotes(db, [quote(current, match_id)])["quote_ids"][0]
    return qid, forecast["id"]


@pytest.mark.parametrize("odds", ["NaN", "Infinity", "-1", "1", "1001"])
def test_invalid_odds(odds):
    with pytest.raises(ValidationError):
        quote(datetime(2026, 1, 1, tzinfo=UTC), odds=odds)


@pytest.mark.parametrize(
    "values",
    [
        {"market": "btts", "selection": "home"},
        {"line": "2.5"},
        {"market": "total_goals", "selection": "over", "line": "3"},
        {"source": " "},
        {"observed_at": "2026-06-01T12:00:00"},
    ],
)
def test_invalid_quote_contract(values):
    with pytest.raises(ValidationError):
        quote(datetime(2026, 1, 1, tzinfo=UTC), **values)


def test_expected_value_and_complete_market():
    assert markets.expected_value(0.6, Decimal("1.8")) == pytest.approx(0.08)
    current = datetime(2026, 1, 1, tzinfo=UTC)
    quotes = [
        quote(current, selection=s, odds=o)
        for s, o in (("home", "2"), ("draw", "3"), ("away", "4"))
    ]
    result = markets.fair_market(quotes)
    assert result["overround"] == pytest.approx(1 / 12)
    assert sum(result["probabilities"].values()) == pytest.approx(1)
    assert result["probabilities"]["home"] == pytest.approx(6 / 13)
    assert markets.fair_market(quotes[:2]) is None
    assert markets.fair_market(quotes + quotes[:1]) is None
    assert (
        markets.fair_market([*quotes[:2], quote(current + timedelta(seconds=1), selection="away")])
        is None
    )


def test_import_idempotent_conflicts_atomicity_and_expiration(setup):
    db, current, _ = setup
    first = markets.import_quotes(db, [quote(current)])
    assert first["inserted"] == 1
    assert markets.import_quotes(db, [quote(current, odds="2.500")])["duplicates"] == 1
    with pytest.raises(ValueError, match="conflitantes"):
        markets.import_quotes(db, [quote(current, 1001), quote(current, odds="3")])
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM market_quotes").fetchone()[0] == 1
    with pytest.raises(ValueError, match="vencida"):
        markets.import_quotes(db, [quote(current - timedelta(minutes=16))])
    with pytest.raises(ValueError, match="futura"):
        markets.import_quotes(db, [quote(current + timedelta(seconds=1))])


def test_csv_import(setup, tmp_path):
    db, current, _ = setup
    path = tmp_path / "odds.csv"
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(markets.Quote.model_fields))
        writer.writeheader()
        writer.writerow(quote(current).model_dump(mode="json"))
    assert markets.import_csv(db, path)["inserted"] == 1
    path.write_text("match_id,odds\n1000,2.5\n")
    with pytest.raises(ValueError, match="CSV"):
        markets.import_csv(db, path)


def test_forecast_prospective_and_versioned(setup):
    db, current, _ = setup
    forecast = markets.create_forecast(db, 1000)
    assert forecast["created_at"] == current.isoformat()
    assert forecast["mode"] == "prospective_paper"
    with sqlite3.connect(db) as connection:
        record = json.loads(connection.execute("SELECT payload FROM paper_forecasts").fetchone()[0])
    assert len(record["training_revisions"]) == 120
    assert record["model_version"]
    assert record["train_sha256"]
    with pytest.raises(ValueError, match="não iniciada"):
        markets.create_forecast(db, 1)


def test_assessment_uncertainty_and_unvalidated_market(setup):
    db, current, _ = setup
    qid, fid = prepare(db, current)
    result = markets.assess(db, qid, fid)
    assert result["decision"] == "eligible_virtual"
    assert result["stress_ev_per_unit"] < result["ev_per_unit"]
    assert result["uncertainty_interval"] is None
    assert result["fair_market"] is None
    other = markets.import_quotes(
        db, [quote(current, market="total_goals", selection="over", line="2.5")]
    )["quote_ids"][0]
    assert "market_or_competition_not_validated" in markets.assess(db, other, fid)["reasons"]


def test_no_future_or_stale_quotes_at_decision(setup, monkeypatch):
    db, current, _ = setup
    qid, fid = prepare(db, current)
    monkeypatch.setattr(markets, "now", lambda: current - timedelta(seconds=10))
    result = markets.assess(db, qid, fid)
    assert result["decision"] == "abstain"
    assert "quote_not_received_at_decision" in result["reasons"]
    assert "forecast_expired_or_future" in result["reasons"]
    monkeypatch.setattr(markets, "now", lambda: current + timedelta(minutes=16))
    assert "quote_expired_or_future" in markets.assess(db, qid, fid)["reasons"]
    assert markets.place_bet(db, qid, fid)["decision"] == "abstain"


def test_duplicate_bet_and_exposure_limits(setup):
    db, current, _ = setup
    for match_id in range(1000, 1005):
        qid, fid = prepare(db, current, match_id)
        assert markets.place_bet(db, qid, fid)["status"] == "open"
    with pytest.raises(ValueError, match="Já existe"):
        markets.place_bet(db, qid, fid)
    qid, fid = prepare(db, current, 1005)
    with pytest.raises(ValueError, match="exposição"):
        markets.place_bet(db, qid, fid)
    wallet = markets.wallet(db)
    assert Decimal(wallet["available_balance"]) == 95
    assert wallet["roi"] is None


def test_win_loss_drawdown_and_settlement_idempotency(setup, monkeypatch):
    db, current, future = setup
    for match_id in (1000, 1001):
        qid, fid = prepare(db, current, match_id)
        markets.place_bet(db, qid, fid)
    future[0]["status"] = "FINISHED"
    future[0]["score"]["fullTime"] = {"home": 2, "away": 1}
    settled = current + timedelta(days=2)
    snapshot(db, [future[0]], settled)
    monkeypatch.setattr(markets, "now", lambda: settled)
    assert markets.settle(db)["settled"][0]["pnl"] == "1.50"
    assert markets.settle(db)["settled"] == []
    future[1]["status"] = "FINISHED"
    future[1]["score"]["fullTime"] = {"home": 0, "away": 0}
    settled += timedelta(minutes=1)
    snapshot(db, [future[1]], settled)
    assert markets.settle(db)["settled"][0]["pnl"] == "-1.00"
    wallet = markets.wallet(db)
    assert Decimal(wallet["realized_balance"]) == Decimal("100.50")
    assert Decimal(wallet["max_realized_drawdown"]) == 1
    assert wallet["roi"] == pytest.approx(0.25)
    assert wallet["roi_bootstrap_ci95"] is None


@pytest.mark.parametrize("status", ["POSTPONED", "CANCELLED", "AWARDED"])
def test_void_rules(setup, monkeypatch, status):
    db, current, future = setup
    qid, fid = prepare(db, current)
    markets.place_bet(db, qid, fid)
    later = current + timedelta(minutes=1)
    future[0]["status"] = status
    snapshot(db, [future[0]], later)
    monkeypatch.setattr(markets, "now", lambda: later)
    assert markets.settle(db)["settled"][0]["status"] == "void"
    wallet = markets.wallet(db)
    assert wallet["void"] == 1
    assert wallet["roi"] is None
    assert Decimal(wallet["available_balance"]) == 100


def test_suspended_or_extra_time_without_regulation_remains_open(setup, monkeypatch):
    db, current, future = setup
    qid, fid = prepare(db, current)
    markets.place_bet(db, qid, fid)
    later = current + timedelta(days=2)
    future[0]["status"] = "SUSPENDED"
    snapshot(db, [future[0]], later)
    monkeypatch.setattr(markets, "now", lambda: later)
    assert markets.settle(db)["settled"] == []
    future[0]["status"] = "FINISHED"
    future[0]["score"] = {"duration": "EXTRA_TIME", "fullTime": {"home": 3, "away": 2}}
    snapshot(db, [future[0]], later)
    assert markets.settle(db)["settled"] == []


def test_fixture_change_abstains_and_voids(setup, monkeypatch):
    db, current, future = setup
    qid, fid = prepare(db, current)
    markets.place_bet(db, qid, fid)
    later = current + timedelta(minutes=1)
    future[0]["utcDate"] = (current + timedelta(days=3)).isoformat()
    snapshot(db, [future[0]], later)
    monkeypatch.setattr(markets, "now", lambda: later)
    assert "fixture_changed" in markets.assess(db, qid, fid)["reasons"]
    assert markets.settle(db)["settled"][0]["status"] == "void"


def test_cli_manual_quote_and_empty_wallet(setup, monkeypatch):
    db, current, _ = setup
    monkeypatch.setenv("SPORTS_DATABASE_PATH", str(db))
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "odds-add",
            "--match-id",
            "1000",
            "--market",
            "1x2",
            "--selection",
            "home",
            "--odds",
            "2.5",
            "--bookmaker",
            "Synthetic",
            "--observed-at",
            current.isoformat(),
            "--source",
            "test",
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["inserted"] == 1
    assert runner.invoke(app, ["paper-wallet"]).exit_code == 0


def test_stress_can_abstain_despite_positive_point_estimate(setup):
    db, current, _ = setup
    forecast = markets.create_forecast(db, 1000)
    qid = markets.import_quotes(db, [quote(current, odds="1.8")])["quote_ids"][0]
    result = markets.assess(db, qid, forecast["id"])
    # Usa o p estimado pelo modelo para construir o caso limite, sem alterar a previsão.
    borderline = Decimal(str(1.03 / result["probability"]))
    qid = markets.import_quotes(db, [quote(current, odds=str(borderline), source="borderline")])[
        "quote_ids"
    ][0]
    result = markets.assess(db, qid, forecast["id"])
    assert result["ev_per_unit"] > 0.02
    assert result["stress_ev_per_unit"] < 0
    assert result["decision"] == "abstain"


def test_distinct_match_and_stale_fixture_rejected(setup, monkeypatch):
    db, current, _ = setup
    qid = markets.import_quotes(db, [quote(current, 1001)])["quote_ids"][0]
    forecast = markets.create_forecast(db, 1000)
    with pytest.raises(ValueError, match="diferentes"):
        markets.assess(db, qid, forecast["id"])
    monkeypatch.setattr(markets, "now", lambda: current + timedelta(hours=24, minutes=1))
    with pytest.raises(ValueError):
        markets.create_forecast(db, 1000)


def test_prospective_twenty_bet_simulation_and_roi_interval(setup, monkeypatch):
    db, current, _ = setup
    monkeypatch.setattr(markets, "now", lambda: current)
    for index in range(20):
        target = game(2000 + index, current + timedelta(days=1), status="TIMED")
        snapshot(db, [target], current)
        qid, fid = prepare(db, current, target["id"])
        assert markets.place_bet(db, qid, fid)["status"] == "open"
        current += timedelta(days=2)
        target["status"] = "FINISHED"
        target["score"]["fullTime"] = {"home": 2 if index % 2 == 0 else 0, "away": 1}
        snapshot(db, [target], current)
        assert len(markets.settle(db)["settled"]) == 1
    result = markets.wallet(db)
    assert result["settled_nonvoid"] == 20
    assert result["roi"] == pytest.approx(0.25)
    assert result["roi_bootstrap_ci95"] is not None
    assert result["roi_bootstrap_ci95"] == markets.wallet(db)["roi_bootstrap_ci95"]
    assert result["roi_bootstrap_ci95"][0] <= result["roi"] <= result["roi_bootstrap_ci95"][1]
