import copy
import json
import sqlite3
from datetime import UTC, datetime

import pytest
from typer.testing import CliRunner

from sports_stats_analyzer.analytics import quality, team_report
from sports_stats_analyzer.cli import app
from sports_stats_analyzer.normalization import normalize
from sports_stats_analyzer.repository import match_versions
from sports_stats_analyzer.storage import save_snapshot


def game(identifier=1, kickoff="2025-01-01T12:00:00Z", status="FINISHED", home=2, away=1):
    return {
        "id": identifier,
        "utcDate": kickoff,
        "status": status,
        "competition": {"id": 2013, "code": "BSA", "name": "Brasileirão"},
        "season": {"id": 100, "startDate": "2025-01-01", "endDate": "2025-12-31"},
        "homeTeam": {"id": 10, "name": "A"},
        "awayTeam": {"id": 20, "name": "B"},
        "score": {"duration": "REGULAR", "fullTime": {"home": home, "away": away}},
    }


def snapshot(db, matches, observed="2025-01-02T00:00:00+00:00"):
    sid = save_snapshot(db, "competitions/BSA/matches", {}, {"matches": matches})
    with sqlite3.connect(db) as connection:
        connection.execute("UPDATE snapshots SET fetched_at=? WHERE id=?", (observed, sid))
    return sid


def test_idempotency_and_revision_asof(tmp_path):
    db = tmp_path / "test.db"
    snapshot(db, [game()])
    assert normalize(db)["accepted"] == 1
    assert normalize(db)["processed_snapshots"] == 0
    snapshot(db, [game(home=0)], "2025-01-04T00:00:00+00:00")
    normalize(db)
    assert match_versions(db)[0]["home_goals"] == 0
    earlier = match_versions(db, datetime(2025, 1, 3, tzinfo=UTC))
    assert earlier[0]["home_goals"] == 2
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT count(*) FROM matches").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM schema_migrations").fetchone()[0] == 1


def test_status_and_regulation_scores(tmp_path):
    db = tmp_path / "test.db"
    extra = game(6)
    extra["score"] = {"duration": "EXTRA_TIME", "fullTime": {"home": 4, "away": 3}}
    penalties = game(7)
    penalties["score"] = {
        "duration": "PENALTY_SHOOTOUT",
        "fullTime": {"home": 6, "away": 5},
        "regularTime": {"home": 1, "away": 1},
    }
    snapshot(
        db,
        [
            game(1),
            game(2, status="TIMED", home=None, away=None),  # type: ignore
            game(3, status="POSTPONED"),
            game(4, status="CANCELLED"),
            game(5, status="AWARDED"),
            extra,
            penalties,
        ],
    )
    normalize(db)
    report = quality(db)["groups"][0]
    assert report["matches"] == 7
    assert report["eligible_results"] == 2
    assert report["finished_without_regulation_score"] == 1
    games = {g["external_id"]: g for g in match_versions(db)}
    assert games[2]["home_goals"] is None
    assert games[6]["home_goals"] is None
    assert games[7]["home_goals"] == 1


@pytest.mark.parametrize(
    "field,value", [("id", -1), ("utcDate", "2025-01-01T12:00:00"), ("status", "UNKNOWN")]
)
def test_invalid_records_quarantined(tmp_path, field, value):
    db = tmp_path / "test.db"
    bad = game(2)
    bad[field] = value
    snapshot(db, [game(), bad])
    assert normalize(db)["rejected"] == 1
    assert len(match_versions(db)) == 1
    assert len(quality(db)["normalization_issues_all_snapshots"]) == 1
    assert normalize(db)["processed_snapshots"] == 0


def test_temporal_features_and_small_samples(tmp_path):
    db = tmp_path / "test.db"
    snapshot(db, [game(), game(2, "2025-01-05T12:00:00Z"), game(3, "2025-01-03T12:00:00Z")])
    normalize(db)
    report = team_report(db, 10, datetime(2025, 1, 3, 12, tzinfo=UTC), window=5)
    assert report["available_matches"] == 1
    assert report["overall"]["points_per_match"] == 3
    assert report["sample_status"] == "insufficient"
    assert report["away"]["goals_for_per_match"] is None
    assert report["days_since_last_kickoff_in_scope"] == 2
    assert team_report(db, 99, datetime(2025, 1, 3, tzinfo=UTC))["overall"]["matches"] == 0
    with pytest.raises(ValueError):
        team_report(db, 10, datetime(2025, 1, 3))  # noqa: DTZ001 -- testa rejeição de fuso ausente


def test_retrospective_requires_opt_in(tmp_path):
    db = tmp_path / "test.db"
    snapshot(db, [game()], "2026-01-01T00:00:00+00:00")
    normalize(db)
    cutoff = datetime(2025, 2, 1, tzinfo=UTC)
    assert team_report(db, 10, cutoff)["overall"]["matches"] == 0
    report = team_report(db, 10, cutoff, retrospective=True)
    assert report["overall"]["matches"] == 1
    assert report["mode"] == "retrospective"


def test_latest_status_selected_before_filter(tmp_path):
    db = tmp_path / "test.db"
    snapshot(db, [game()])
    snapshot(db, [game(status="CANCELLED")], "2025-01-03T00:00:00+00:00")
    normalize(db)
    assert team_report(db, 10, datetime(2025, 2, 1, tzinfo=UTC))["overall"]["matches"] == 0


def test_transaction_rolls_back_when_later_snapshot_is_malformed(tmp_path):
    db = tmp_path / "test.db"
    snapshot(db, [game()])
    normalize(db)
    snapshot(db, [game(2)])
    bad_id = save_snapshot(db, "competitions/BSA/matches", {}, {"matches": "invalid"})
    with pytest.raises(ValueError):
        normalize(db)
    assert len(match_versions(db)) == 1
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT count(*) FROM normalization_runs").fetchone()[0] == 1
        connection.execute("DELETE FROM snapshots WHERE id=?", (bad_id,))
    assert normalize(db)["accepted"] == 1


def test_competitions_teams_and_skipped_standings(tmp_path):
    db = tmp_path / "test.db"
    match = game()
    save_snapshot(db, "competitions", {}, {"competitions": [match["competition"]]})
    save_snapshot(
        db,
        "competitions/BSA/teams",
        {},
        {
            "competition": match["competition"],
            "season": match["season"],
            "teams": [match["homeTeam"], match["awayTeam"]],
        },
    )
    save_snapshot(db, "competitions/BSA/standings", {}, {"standings": []})
    report = normalize(db)
    assert report["accepted"] == 3
    assert report["skipped"] == 1
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT count(*) FROM teams").fetchone()[0] == 2


def test_cli_reports(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setenv("SPORTS_DATABASE_PATH", str(db))
    runner = CliRunner()
    assert runner.invoke(app, ["quality"]).exit_code == 1
    snapshot(db, [game()])
    assert runner.invoke(app, ["normalize"]).exit_code == 0
    result = runner.invoke(app, ["quality", "--competition", "BSA", "--season", "2025"])
    assert json.loads(result.output)["groups"][0]["eligible_results"] == 1
    result = runner.invoke(app, ["team-report", "10", "--before", "2025-01-04T00:00:00Z"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["overall"]["matches"] == 1
    assert runner.invoke(app, ["team-report", "10", "--before", "bad"]).exit_code == 2


def test_negative_goals_rejected_and_unknown_teams_preserved(tmp_path):
    db = tmp_path / "test.db"
    unknown = game(2, status="SCHEDULED", home=None, away=None)  # type: ignore
    unknown["homeTeam"] = {"id": None, "name": None}
    snapshot(db, [game(home=-1), unknown])
    assert normalize(db)["rejected"] == 1
    assert quality(db)["groups"][0]["missing_fields"]["home_id"] == 1


def test_competition_season_filters_and_away_form(tmp_path):
    db = tmp_path / "test.db"
    other = copy.deepcopy(game(2))
    other["competition"] = {"id": 9, "name": "Other", "code": "OTHER"}
    snapshot(db, [game(), other])
    normalize(db)
    report = team_report(db, 20, datetime(2025, 2, 1, tzinfo=UTC), competition="BSA", season=2025)
    assert report["overall"]["matches"] == 1
    assert report["away"]["losses"] == 1
    assert report["overall"]["goals_for"] == 1
    assert quality(db, season=2024)["groups"] == []
