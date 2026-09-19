"""Leitura posicional conservadora e minutos nominais de súmulas CBF."""

import sqlite3

import pytest
from typer.testing import CliRunner

from sports_stats_analyzer.cbf_sumulas import (
    SumulaParseError,
    Word,
    _appearances,
    _event_minute,
    _roster,
    _substitutions,
    extract_stored_sumula,
)
from sports_stats_analyzer.cli import app
from sports_stats_analyzer.providers.cbf import _database


def _roster_words():
    words = [Word(255, 400, "Relação")]
    for row in range(12):
        y = 443 + row * 14
        role = "T" if row < 11 else "R"
        for shirt_x, role_x, id_x, prefix in ((47, 219, 256, 100000), (305, 477, 514, 200000)):
            words.extend(
                [
                    Word(shirt_x, y, str(row + 1)),
                    Word(role_x, y, role),
                    Word(id_x, y, str(prefix + row + 1)),
                ]
            )
    return words


def test_roster_substitutions_and_nominal_minutes():
    roster = _roster(_roster_words())
    assert len(roster) == 24
    words = [
        Word(270, 225, "Substituições"),
        Word(62, 253, "-"),
        Word(93, 253, "INT"),
        Word(116, 253, "Bahia/BA"),
        Word(244, 253, "12"),
        Word(400, 253, "1"),
    ]
    events = _substitutions(words, {"home": "Bahia / BA", "away": "Remo / PA"}, 4)
    appearances = _appearances(roster, events, 101)
    by_id = {item["cbf_person_id"]: item for item in appearances}
    assert by_id[100001]["nominal_minutes"] == 49
    assert by_id[100012]["nominal_minutes"] == 52
    assert by_id[200001]["nominal_minutes"] == 101
    assert events[0]["in_cbf_person_id"] == 100012
    assert _event_minute("2T", "+5:00", 4) == 99
    with pytest.raises(SumulaParseError, match="contradiz"):
        _appearances(roster, [events[0], events[0].copy()], 101)


def test_rejects_missing_document_and_hash_mismatch(tmp_path):
    database = tmp_path / "sports.db"
    with sqlite3.connect(database) as connection:
        _database(connection)
        connection.execute(
            """INSERT INTO cbf_sumulas
            (document_url, season, sha256, path, fetched_at)
            VALUES ('https://conteudo.cbf.com.br/sumulas/2026/1se.pdf', 2026, 'wrong',
                    'sumulas/2026/file.pdf', '')"""
        )
    with pytest.raises(SumulaParseError, match="ausente"):
        extract_stored_sumula(database, 1)
    target = tmp_path / "cbf/sumulas/2026/file.pdf"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"%PDF-invalid")
    with pytest.raises(SumulaParseError, match="Hash"):
        extract_stored_sumula(database, 1)
    assert CliRunner().invoke(app, ["cbf-sumula-extract", "--help"]).exit_code == 0
