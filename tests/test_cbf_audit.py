"""Auditoria de páginas já coletadas, sem rede nem fusão automática de clubes."""

import hashlib
import json
import sqlite3

import pytest
from typer.testing import CliRunner

from sports_stats_analyzer.cbf_audit import audit_team_pages
from sports_stats_analyzer.cli import app
from sports_stats_analyzer.providers.cbf_teams import _schema


def _page(database, connection, competition, team_id, tab, payload):
    body = f"<html>{competition}:{team_id}:{tab}</html>".encode()
    digest = hashlib.sha256(body).hexdigest()
    relative = f"html/{digest}.html"
    target = database.parent / "cbf" / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)
    connection.execute(
        """INSERT INTO cbf_team_pages
        (url, competition, season, team_id, tab, sha256, path, fetched_at, data_json)
        VALUES (?, ?, 2026, ?, ?, ?, ?, '2026-09-19T00:00:00+00:00', ?)""",
        (
            f"https://example.test/{competition}/{team_id}/{tab}",
            competition,
            team_id,
            tab,
            digest,
            relative,
            json.dumps(payload),
        ),
    )
    return target


def test_audit_reports_coverage_semantics_integrity_and_identity_candidates(tmp_path):
    database = tmp_path / "sports.db"
    with sqlite3.connect(database) as connection:
        _schema(connection)
        for identifier, name in ((1, "Ituano"), (2, "ITUANO FC")):
            connection.execute(
                "INSERT INTO cbf_teams VALUES ('serie-c', 2026, ?, ?, 'SP', '', '', '')",
                (identifier, name),
            )
        _page(
            database,
            connection,
            "serie-c",
            None,
            "index",
            {
                "teams": [
                    {"team_id": 1, "name": "Ituano", "state": "SP"},
                    {"team_id": 2, "name": "ITUANO FC", "state": "SP"},
                ]
            },
        )
        _page(
            database,
            connection,
            "serie-c",
            1,
            "atletas",
            {"listed_athletes": [{"name": "Atleta A"}]},
        )
        corrupted = _page(
            database,
            connection,
            "serie-c",
            1,
            "historico-de-partidas",
            {"matches": [{"match_id": 101, "url": "https://example.test/jogo"}]},
        )
        _page(
            database,
            connection,
            "serie-c",
            1,
            "estatisticas",
            {"statistics": {"played": 1, "wins": 1, "draws": 0, "losses": 0}},
        )
        _page(database, connection, "serie-c", 2, "atletas", {"listed_athletes": []})
        _page(
            database,
            connection,
            "serie-c",
            2,
            "estatisticas",
            {"statistics": {"played": 3, "wins": 1, "draws": 0, "losses": 1}},
        )
    corrupted.write_bytes(b"corrompido")

    report = audit_team_pages(database, 2026)
    assert report["teams"] == 2
    assert report["coverage"][0]["tabs"]["historico-de-partidas"] == {
        "observed": 1,
        "nonempty": 1,
        "expected": 2,
    }
    assert report["issue_counts"] == {
        "empty_content": 1,
        "hash_mismatch": 1,
        "missing_tab": 1,
        "results_total_mismatch": 1,
    }
    assert [member["team_id"] for member in report["identity_candidates"][0]["members"]] == [1, 2]
    assert report["identity_candidates"][0]["name_key"] == "ituano"


def test_audit_requires_collected_teams(tmp_path, monkeypatch):
    database = tmp_path / "sports.db"
    with pytest.raises(ValueError, match="inexistente"):
        audit_team_pages(database, 2026)
    monkeypatch.setenv("SPORTS_DATABASE_PATH", str(database))
    assert CliRunner().invoke(app, ["cbf-team-audit", "--season", "2026"]).exit_code == 1
    assert CliRunner().invoke(app, ["cbf-team-audit", "--help"]).exit_code == 0
