import json
import sqlite3

import httpx
import pytest
from typer.testing import CliRunner

from sports_stats_analyzer.cli import app
from sports_stats_analyzer.providers.football_data import FootballDataClient, ProviderError
from sports_stats_analyzer.storage import save_snapshot


def test_request_contract_and_nullable_score():
    def handler(request):
        assert (
            str(request.url)
            == "https://api.football-data.org/v4/competitions/BSA/matches?season=2025"
        )
        assert request.headers["X-Auth-Token"] == "test-token"
        return httpx.Response(200, json={"matches": [{"score": {"fullTime": {"home": None}}}]})

    with FootballDataClient("test-token", transport=httpx.MockTransport(handler)) as client:
        assert (
            client.get("competitions/BSA/matches", {"season": 2025})["matches"][0]["score"][
                "fullTime"
            ]["home"]
            is None
        )


@pytest.mark.parametrize("status", [401, 403, 404, 429, 500, 302])
def test_http_failures_do_not_expose_response(status):
    transport = httpx.MockTransport(lambda _: httpx.Response(status, text="sensitive"))
    with FootballDataClient("test-token", transport=transport) as client:
        with pytest.raises(ProviderError) as error:
            client.get("competitions")
        assert "sensitive" not in str(error.value)
        assert "test-token" not in str(error.value)


@pytest.mark.parametrize("body", ["not-json", "[]"])
def test_invalid_payload(body):
    with (
        FootballDataClient(
            "test-token",
            transport=httpx.MockTransport(lambda _: httpx.Response(200, text=body)),
        ) as client,
        pytest.raises(ProviderError),
    ):
        client.get("competitions")


def test_external_endpoint_rejected():
    with FootballDataClient("test-token") as client, pytest.raises(ValueError):
        client.get("https://example.com")


def test_snapshots_preserve_history(tmp_path):
    database = tmp_path / "sports.db"
    first = save_snapshot(database, "competitions", {}, {"competitions": []})
    second = save_snapshot(database, "competitions", {}, {"competitions": [{"id": 1}]})
    assert first != second
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT fetched_at, payload_json FROM snapshots ORDER BY id"
        ).fetchall()
    assert len(rows) == 2
    assert rows[0][0].endswith("+00:00")
    assert json.loads(rows[0][1]) == {"competitions": []}


def test_cli_validation():
    result = CliRunner().invoke(app, ["collect", "matches"])
    assert result.exit_code == 2
    assert "competition" in result.output


def test_cli_collection(tmp_path, monkeypatch):
    database = tmp_path / "sports.db"
    monkeypatch.setenv("SPORTS_DATABASE_PATH", str(database))
    monkeypatch.setenv("FOOTBALL_DATA_API_TOKEN", "test-token")
    monkeypatch.setattr(FootballDataClient, "get", lambda *args: {"matches": []})
    result = CliRunner().invoke(
        app, ["collect", "matches", "--competition", "BSA", "--season", "2025"]
    )
    assert result.exit_code == 0, result.output
    assert database.exists()


def test_rate_limit_spacing(monkeypatch):
    sleeps = []
    monkeypatch.setattr("sports_stats_analyzer.providers.football_data.time.sleep", sleeps.append)
    monkeypatch.setattr("sports_stats_analyzer.providers.football_data.time.monotonic", lambda: 100)
    with FootballDataClient(
        "test-token",
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={})),
    ) as client:
        client.get("competitions")
        client.get("competitions")
    assert sleeps == [6]
