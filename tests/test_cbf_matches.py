"""Catálogo de URLs de jogos, proveniência e referências contraditórias."""

import json
import sqlite3

import pytest
from typer.testing import CliRunner

from sports_stats_analyzer.cbf_matches import catalog_match_urls
from sports_stats_analyzer.cli import app
from sports_stats_analyzer.providers.cbf_teams import _schema


def _card(match_id, home_score):
    return {
        "match_id": match_id,
        "url": "https://www.cbf.com.br/futebol-brasileiro/jogos/"
        f"campeonato-brasileiro/serie-a/2026/a-x-b/{match_id}",
        "home_team_id": 1,
        "away_team_id": 2,
        "home_score": home_score,
        "away_score": 0,
    }


def _database(path):
    with sqlite3.connect(path) as connection:
        _schema(connection)
        for team_id in (1, 2, 3):
            connection.execute(
                "INSERT INTO cbf_teams VALUES ('serie-a', 2026, ?, 'Time', 'SP', '', '', '')",
                (team_id,),
            )
        for team_id, cards in (
            (1, [_card(100, 1), _card(101, 2), {**_card(102, 1), "url": "https://other.test"}]),
            (2, [_card(100, 1), _card(101, 3)]),
        ):
            connection.execute(
                """INSERT INTO cbf_team_pages
                (url, competition, season, team_id, tab, sha256, path, fetched_at, data_json)
                VALUES (?, 'serie-a', 2026, ?, 'historico-de-partidas', '', '', '', ?)""",
                (f"https://example.test/{team_id}", team_id, json.dumps({"matches": cards})),
            )


def test_catalog_deduplicates_and_excludes_conflicts(tmp_path):
    database = tmp_path / "sports.db"
    _database(database)
    result = catalog_match_urls(database, 2026)
    assert result["coverage"] == [
        {
            "competition": "serie-a",
            "indexed_teams": 3,
            "history_pages": 2,
            "cards": 4,
            "unique_matches": 1,
            "paired_matches": 1,
            "single_ref_matches": 0,
        }
    ]
    assert result["issue_counts"] == {"conflicting_match_card": 1, "invalid_match_url": 1}
    assert result["urls"][0]["match_id"] == 100
    assert result["urls"][0]["source_page_ids"] == [1, 2]


def test_cli_exports_valid_urls_without_overwriting(tmp_path, monkeypatch):
    database = tmp_path / "sports.db"
    _database(database)
    monkeypatch.setenv("SPORTS_DATABASE_PATH", str(database))
    output = tmp_path / "urls.txt"
    command = ["cbf-match-urls", "--season", "2026", "--urls-file", str(output)]
    result = CliRunner().invoke(app, command)
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["url_count"] == 1
    assert output.read_text().splitlines()[1].endswith("/100")
    assert CliRunner().invoke(app, command).exit_code == 2
    assert CliRunner().invoke(app, [*command, "--replace"]).exit_code == 0
    assert CliRunner().invoke(app, ["cbf-match-urls", "--help"]).exit_code == 0


def test_catalog_requires_collected_teams(tmp_path):
    with pytest.raises(ValueError, match="inexistente"):
        catalog_match_urls(tmp_path / "missing.db", 2026)
