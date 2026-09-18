import json
import sqlite3
from datetime import UTC, datetime

import httpx
import pytest
from typer.testing import CliRunner

from sports_stats_analyzer.cli import app
from sports_stats_analyzer.context import (
    collect_detail,
    coverage,
    lineup,
    match_context,
    player_context,
    player_list,
    squad_context,
)
from sports_stats_analyzer.providers.football_data import FootballDataClient, ProviderError
from sports_stats_analyzer.storage import save_snapshot


def store(db, endpoint, payload, day=1, params=None):
    sid = save_snapshot(db, endpoint, params or {}, payload)
    with sqlite3.connect(db) as conn:
        conn.execute(
            "UPDATE snapshots SET fetched_at=? WHERE id=?",
            (datetime(2025, 1, day, tzinfo=UTC).isoformat(), sid),
        )
    return sid


def match():
    return {
        "id": 1,
        "status": "TIMED",
        "utcDate": "2025-01-05T12:00:00Z",
        "competition": {"id": 2013, "code": "BSA"},
        "season": {"startDate": "2025-01-01"},
        "homeTeam": {"id": 10, "name": "A"},
        "awayTeam": {"id": 20, "name": "B"},
    }


def players():
    return [{"id": i, "name": f"Player {i}", "position": "Midfield"} for i in range(1, 12)]


def test_unfold_headers_do_not_leak_to_next_request(monkeypatch):
    requests = []
    monkeypatch.setattr("sports_stats_analyzer.providers.football_data.time.sleep", lambda _: None)

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={})

    with FootballDataClient("secret", transport=httpx.MockTransport(handler)) as client:
        client.get("matches/1", unfold=True)
        client.get("teams/10")
    for field in ("Lineups", "Subs", "Goals", "Bookings"):
        assert requests[0].headers[f"X-Unfold-{field}"] == "true"
        assert f"X-Unfold-{field}" not in requests[1].headers


@pytest.mark.parametrize(
    "container,state",
    [
        ({}, "missing"),
        ({"lineup": None}, "null"),
        ({"lineup": []}, "empty"),
        ({"lineup": "bad"}, "invalid"),
        ({"lineup": [{"id": -1, "name": "bad"}]}, "invalid"),
    ],
)
def test_missing_null_empty_invalid_are_distinct(container, state):
    assert player_list(container, "lineup")["state"] == state


def test_reported_xi_is_not_independently_confirmed():
    report = lineup({"lineup": players(), "squad": players()}, "TIMED")
    assert report["state"] == "reported_starting_xi"
    assert report["confirmation"] == "not_independently_verified"
    assert lineup({"squad": players()}, "TIMED")["state"] == "missing"
    assert lineup({"lineup": players()[:3]}, "TIMED")["state"] == "partial"
    assert lineup({"lineup": players(), "bench": players()[:1]}, "TIMED")["state"] == "invalid"


def test_asof_and_first_observation_are_preserved(tmp_path):
    db = tmp_path / "s.db"
    payload = match()
    store(db, "matches/1", payload)
    payload["homeTeam"]["lineup"] = players()
    store(db, "matches/1", payload, day=2)
    store(db, "matches/1", payload, day=3)
    assert (
        match_context(db, 1, datetime(2025, 1, 1, tzinfo=UTC))["sides"]["homeTeam"]["state"]
        == "missing"
    )
    report = match_context(db, 1, datetime(2025, 1, 4, tzinfo=UTC))
    assert report["sides"]["homeTeam"]["first_observed_xi_at"].startswith("2025-01-02")
    assert report["observed_before_kickoff"]
    assert report["probability_adjustment"] is None
    assert match_context(db, 1, datetime(2024, 1, 1, tzinfo=UTC))["state"] == "not_observed"


def test_folded_list_does_not_erase_detail_but_empty_detail_does(tmp_path):
    db = tmp_path / "s.db"
    payload = match()
    payload["homeTeam"]["lineup"] = players()
    store(db, "matches/1", payload)
    store(db, "competitions/BSA/matches", {"matches": [match()]}, day=2)
    report = match_context(db, 1, datetime(2025, 1, 2, tzinfo=UTC))
    assert report["sides"]["homeTeam"]["state"] == "reported_starting_xi"
    assert report["evidence"]["snapshot_id"] != report["latest_match_evidence"]["snapshot_id"]
    payload["homeTeam"]["lineup"] = []
    store(db, "matches/1", payload, day=3)
    assert (
        match_context(db, 1, datetime(2025, 1, 4, tzinfo=UTC))["sides"]["homeTeam"]["state"]
        == "empty"
    )


def test_events_do_not_imply_minutes(tmp_path):
    db = tmp_path / "s.db"
    payload = match()
    payload["substitutions"] = [{"minute": 60, "playerOut": {"id": 1}, "playerIn": {"id": 12}}]
    store(db, "matches/1", payload)
    result = match_context(db, 1, datetime(2025, 1, 2, tzinfo=UTC))
    assert result["events"]["substitutions"] == "present"
    assert result["minutes"] is None
    assert result["per_90_metrics"] is None


def test_transfer_profile_and_squad_are_not_retroactively_rewritten(tmp_path):
    db = tmp_path / "s.db"
    player = {"id": 1, "name": "Player", "currentTeam": {"id": 10, "name": "A"}}
    store(db, "persons/1", player)
    store(db, "teams/10", {"id": 10, "squad": [player]})
    player["currentTeam"] = {"id": 20, "name": "B"}
    store(db, "persons/1", player, day=3)
    store(db, "teams/10", {"id": 10, "squad": []}, day=3)
    earlier, later = datetime(2025, 1, 2, tzinfo=UTC), datetime(2025, 1, 4, tzinfo=UTC)
    assert player_context(db, 1, earlier)["reported_team"]["id"] == 10
    assert player_context(db, 1, later)["reported_team"]["id"] == 20
    assert len(squad_context(db, 10, earlier)["squad"]["players"]) == 1
    assert squad_context(db, 10, later)["squad"]["state"] == "empty"


def test_coverage_separates_expansion_and_distinct_matches(tmp_path):
    db = tmp_path / "s.db"
    store(db, "competitions/BSA/matches", {"matches": [match()]})
    store(db, "competitions/BSA/matches", {"matches": [match()]}, day=2, params={"_unfold": True})
    store(db, "matches/1", match(), day=3)
    report = coverage(db, "BSA", 2025)["match_observations"]
    assert report["folded_list"]["observations"] == 1
    assert report["detail_or_unfolded"]["observations"] == 2
    assert report["detail_or_unfolded"]["distinct_matches"] == 1
    assert coverage(db, "PL")["match_observations"] == {}


def test_cli_and_collection_metadata(tmp_path, monkeypatch):
    db = tmp_path / "s.db"
    monkeypatch.setenv("SPORTS_DATABASE_PATH", str(db))
    monkeypatch.setenv("FOOTBALL_DATA_API_TOKEN", "test")
    monkeypatch.setattr(FootballDataClient, "get", lambda self, endpoint, **kwargs: match())
    runner = CliRunner()
    assert runner.invoke(app, ["collect-context", "match", "1"]).exit_code == 0
    with sqlite3.connect(db) as conn:
        assert json.loads(conn.execute("SELECT params_json FROM snapshots").fetchone()[0]) == {
            "_unfold": True
        }
    assert (
        runner.invoke(app, ["context-report", "1", "--before", "2099-01-01T00:00:00Z"]).exit_code
        == 0
    )
    assert runner.invoke(app, ["context-report", "1", "--before", "bad"]).exit_code == 2
    assert (
        runner.invoke(app, ["squad-report", "10", "--before", "2099-01-01T00:00:00Z"]).exit_code
        == 0
    )
    assert (
        runner.invoke(app, ["player-report", "1", "--before", "2099-01-01T00:00:00Z"]).exit_code
        == 0
    )


def test_failed_collection_does_not_persist(tmp_path, monkeypatch):
    monkeypatch.setenv("FOOTBALL_DATA_API_TOKEN", "test")

    def denied(*args, **kwargs):
        raise ProviderError("Acesso negado")

    monkeypatch.setattr(FootballDataClient, "get", denied)
    db = tmp_path / "s.db"
    with pytest.raises(ValueError, match="Acesso negado"):
        collect_detail(db, "person", 1)
    assert not db.exists()


def test_mismatched_response_is_not_persisted(tmp_path, monkeypatch):
    monkeypatch.setenv("FOOTBALL_DATA_API_TOKEN", "test")
    monkeypatch.setattr(FootballDataClient, "get", lambda *a, **kw: {"id": 999})
    with pytest.raises(ValueError, match="ID"):
        collect_detail(tmp_path / "s.db", "team", 1)
