"""Migração e leitura de revisões por instante de observação."""

import sqlite3
from datetime import datetime
from pathlib import Path

from sports_stats_analyzer.domain import utc


def connect(database: Path) -> sqlite3.Connection:
    if not database.is_file():
        raise ValueError("Banco não encontrado. Execute collect primeiro.")
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def migrate(connection: sqlite3.Connection) -> None:
    """Migração 1 aditiva; não altera a tabela de snapshots da fase 1."""
    connection.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY)")
    if connection.execute("SELECT 1 FROM schema_migrations WHERE version=1").fetchone():
        return
    for table, columns in {
        "competitions": "name TEXT NOT NULL, code TEXT",
        "seasons": "competition_id INTEGER NOT NULL, start_date TEXT NOT NULL, end_date TEXT NOT NULL",
        "teams": "name TEXT",
        "matches": """competition_id INTEGER NOT NULL, competition_code TEXT,
            season_id INTEGER NOT NULL, season_year INTEGER NOT NULL,
            kickoff_at TEXT NOT NULL, provider_updated_at TEXT, status TEXT NOT NULL,
            home_id INTEGER, away_id INTEGER, home_name TEXT, away_name TEXT,
            duration TEXT, home_goals INTEGER, away_goals INTEGER""",
    }.items():
        connection.execute(f"""CREATE TABLE {table} (
            provider TEXT NOT NULL, external_id INTEGER NOT NULL,
            snapshot_id INTEGER NOT NULL REFERENCES snapshots(id), {columns},
            PRIMARY KEY(provider, external_id, snapshot_id))""")
    connection.execute("""CREATE TABLE normalization_runs (
        snapshot_id INTEGER PRIMARY KEY REFERENCES snapshots(id),
        accepted INTEGER NOT NULL, rejected INTEGER NOT NULL, skipped INTEGER NOT NULL)""")
    connection.execute("""CREATE TABLE normalization_issues (
        snapshot_id INTEGER NOT NULL REFERENCES snapshots(id),
        record_index INTEGER NOT NULL, reason TEXT NOT NULL,
        PRIMARY KEY(snapshot_id, record_index))""")
    connection.execute("INSERT INTO schema_migrations VALUES (1)")


def match_versions(database: Path, observed_at: datetime | None = None) -> list[dict]:
    """Retorna a última revisão conhecida ANTES de aplicar filtros de status/data."""
    with connect(database) as connection:
        if not connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='matches'"
        ).fetchone():
            raise ValueError("Execute normalize antes de consultar indicadores.")
        clause = "" if observed_at is None else "WHERE s.fetched_at <= ?"
        params = () if observed_at is None else (utc(observed_at).isoformat(),)
        rows = connection.execute(
            f"""
            SELECT * FROM (
                SELECT m.*, s.fetched_at, ROW_NUMBER() OVER (
                    PARTITION BY m.provider, m.external_id
                    ORDER BY s.fetched_at DESC, m.snapshot_id DESC
                ) AS revision_rank
                FROM matches m JOIN snapshots s ON s.id=m.snapshot_id {clause}
            ) WHERE revision_rank=1
        """,
            params,
        ).fetchall()
    return [dict(row) for row in rows]
