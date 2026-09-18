import fcntl
import json
import multiprocessing
import sqlite3
import time
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from typer.testing import CliRunner

from sports_stats_analyzer.cli import app
from sports_stats_analyzer.operations import backup, copy_database, health, read_table, update
from sports_stats_analyzer.providers.football_data import FootballDataClient, ProviderError
from sports_stats_analyzer.providers.rate_limit import RateGate
from sports_stats_analyzer.storage import save_snapshot


def test_backup_restore_preserves_data_and_never_overwrites(tmp_path):
    source = tmp_path / "sports.db"
    save_snapshot(source, "competitions", {}, {"competitions": []})
    result = backup(source)
    restored = tmp_path / "restored.db"
    assert copy_database(type(source)(result["target"]), restored)["integrity"] == "ok"
    assert read_table(source, "snapshots") == read_table(restored, "snapshots")
    with pytest.raises(ValueError, match="novo"):
        copy_database(source, restored)
    assert CliRunner().invoke(app, ["restore", str(source), str(source)]).exit_code == 1


def test_corrupt_backup_rejected(tmp_path):
    corrupt = tmp_path / "corrupt.db"
    corrupt.write_text("not a database")
    with pytest.raises(sqlite3.DatabaseError):
        copy_database(corrupt, tmp_path / "new.db")
    assert not (tmp_path / "new.db").exists()


def test_failed_update_preserves_snapshot_and_does_not_log_secret(tmp_path, monkeypatch, caplog):
    db = tmp_path / "sports.db"
    save_snapshot(db, "competitions/BSA/matches", {"season": 2026}, {"matches": []})
    monkeypatch.setenv("FOOTBALL_DATA_API_TOKEN", "DO_NOT_LOG_ME")

    def fail(*args, **kwargs):
        raise ProviderError("DO_NOT_LOG_ME")

    monkeypatch.setattr(FootballDataClient, "get", fail)
    result = update(db, "BSA", 2026)
    assert result["status"] == "failed"
    assert len(read_table(db, "snapshots")) == 1
    assert "DO_NOT_LOG_ME" not in json.dumps(read_table(db, "operation_runs"))
    assert "DO_NOT_LOG_ME" not in caplog.text
    monkeypatch.setenv("SPORTS_DATABASE_PATH", str(db))
    assert CliRunner().invoke(app, ["update-data", "--season", "2026"]).exit_code == 1


def test_successful_update_and_overlap_rejected(tmp_path, monkeypatch):
    db = tmp_path / "sports.db"
    monkeypatch.setenv("FOOTBALL_DATA_API_TOKEN", "test")
    monkeypatch.setattr(FootballDataClient, "get", lambda *a, **kw: {"matches": []})
    assert update(db, "BSA", 2026)["status"] == "success"
    assert health(db, "BSA", 2026)["freshness"] == "fresh"
    with db.with_suffix(".db.update.lock").open("a+") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(ValueError, match="andamento"):
            update(db, "BSA", 2026)


def test_stale_scope_not_hidden_by_recent_other_season(tmp_path):
    db = tmp_path / "s.db"
    sid = save_snapshot(db, "competitions/BSA/matches", {"season": 2026}, {"matches": []})
    with sqlite3.connect(db) as connection:
        connection.execute(
            "UPDATE snapshots SET fetched_at=? WHERE id=?",
            ((datetime.now(UTC) - timedelta(days=3)).isoformat(), sid),
        )
    save_snapshot(db, "competitions/BSA/matches", {"season": 2025}, {"matches": []})
    assert health(db, "BSA", 2026)["freshness"] == "stale"
    assert health(db, "PL", 2026)["freshness"] == "missing"


def test_retries_bound_and_quota_headers(monkeypatch):
    sleeps, requests = [], []
    monkeypatch.setattr("sports_stats_analyzer.providers.football_data.time.sleep", sleeps.append)

    def handler(request):
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(429, headers={"X-RequestCounter-Reset": "12", "Retry-After": "7"})
        return httpx.Response(200, json={"matches": []})

    with FootballDataClient("test", transport=httpx.MockTransport(handler)) as client:
        assert client.get("matches", attempts=3) == {"matches": []}
    assert len(requests) == 2
    assert 12 in sleeps
    requests.clear()

    def always_fail(request):
        requests.append(request)
        return httpx.Response(503)

    with (
        FootballDataClient("test", transport=httpx.MockTransport(always_fail)) as client,
        pytest.raises(ProviderError),
    ):
        client.get("matches", attempts=3)
    assert len(requests) == 3


def test_authentication_is_not_retried(monkeypatch):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(403)

    with (
        FootballDataClient("test", transport=httpx.MockTransport(handler)) as client,
        pytest.raises(ProviderError),
    ):
        client.get("matches", attempts=3)
    assert len(requests) == 1


def enter_gate(directory, queue):
    with RateGate("shared-secret", 0.1, directory):
        queue.put(time.time())


def test_quota_serializes_processes(tmp_path):
    context = multiprocessing.get_context("spawn")
    queue = context.Queue()
    gate = RateGate("shared-secret", 0.15, tmp_path)
    with gate:
        started = time.time()
        process = context.Process(target=enter_gate, args=(tmp_path, queue))
        process.start()
        gate.defer(0.15)
    try:
        acquired = queue.get(timeout=10)
    finally:
        process.join(timeout=2)
        if process.is_alive():
            process.terminate()
            process.join(timeout=2)
    assert process.exitcode == 0
    assert acquired - started >= 0.14
    assert "shared-secret" not in str(gate.path)
    assert "shared-secret" not in gate.path.read_text()


def test_long_server_cooldown_is_preserved(tmp_path):
    gate = RateGate("test", 1, tmp_path)
    with gate:
        gate.defer(120)
    with pytest.raises(ValueError, match="liberação"), gate:
        pass
