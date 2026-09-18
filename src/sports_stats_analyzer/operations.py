"""Atualização explícita, estado operacional e cópia consistente do SQLite."""

import fcntl
import json
import logging
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

from sports_stats_analyzer.config import Settings
from sports_stats_analyzer.normalization import normalize
from sports_stats_analyzer.providers.football_data import FootballDataClient, ProviderError
from sports_stats_analyzer.storage import save_snapshot

logger = logging.getLogger(__name__)


def update(database: Path, competition: str = "BSA", season: int | None = None) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9]+", competition):
        raise ValueError("Código de competição inválido")
    season = season if season is not None else datetime.now(UTC).year
    if not 1900 <= season <= 2100:
        raise ValueError("Temporada inválida")
    settings = Settings()
    database.parent.mkdir(parents=True, exist_ok=True)
    with database.with_suffix(database.suffix + ".update.lock").open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Já existe atualização em andamento para este banco") from None
        with sqlite3.connect(database) as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS operation_runs (
                id TEXT PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT,
                competition TEXT NOT NULL, season INTEGER NOT NULL, status TEXT NOT NULL,
                error_kind TEXT, snapshot_id INTEGER)""")
            run_id = uuid4().hex
            connection.execute(
                "INSERT INTO operation_runs VALUES (?, ?, NULL, ?, ?, 'running', NULL, NULL)",
                (run_id, datetime.now(UTC).isoformat(), competition.upper(), season),
            )
        snapshot_id = None
        try:
            endpoint = f"competitions/{competition.upper()}/matches"
            with FootballDataClient(
                settings.football_data_api_token.get_secret_value(),
                settings.football_data_requests_per_minute,
            ) as client:
                payload = client.get(endpoint, {"season": season}, attempts=3)
            snapshot_id = save_snapshot(database, endpoint, {"season": season}, payload)
            normalization = normalize(database)
            status = "warning" if normalization["rejected"] else "success"
            error_kind = None
        except (ProviderError, ValueError, sqlite3.Error, OSError) as error:
            status, error_kind, normalization = "failed", type(error).__name__, None
        with sqlite3.connect(database) as connection:
            connection.execute(
                "UPDATE operation_runs SET finished_at=?, status=?, error_kind=?, snapshot_id=? WHERE id=?",
                (datetime.now(UTC).isoformat(), status, error_kind, snapshot_id, run_id),
            )
        logger.info(
            "update status=%s competition=%s season=%s", status, competition.upper(), season
        )
        return {
            "run_id": run_id,
            "status": status,
            "snapshot_id": snapshot_id,
            "error_kind": error_kind,
            "normalization": normalization,
        }


def read_table(database: Path, table: str) -> list[dict]:
    allowed = {"snapshots", "operation_runs", "paper_forecasts", "normalization_issues"}
    if table not in allowed:
        raise ValueError("Tabela não permitida")
    if not database.is_file():
        return []
    with sqlite3.connect(f"file:{quote(str(database.resolve()))}?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        if not connection.execute(
            "SELECT 1 FROM sqlite_master WHERE name=? AND type='table'", (table,)
        ).fetchone():
            return []
        return [dict(row) for row in connection.execute(f"SELECT * FROM {table}")]


def health(database: Path, competition: str = "BSA", season: int | None = None) -> dict:
    season = season if season is not None else datetime.now(UTC).year
    snapshots = [
        s
        for s in read_table(database, "snapshots")
        if s["endpoint"].upper() == f"competitions/{competition}/matches".upper()
        and json.loads(s["params_json"]).get("season") == season
    ]
    latest = max(snapshots, key=lambda s: s["fetched_at"], default=None)
    age = (
        (datetime.now(UTC) - datetime.fromisoformat(latest["fetched_at"])).total_seconds() / 3600
        if latest
        else None
    )
    runs = [
        r
        for r in read_table(database, "operation_runs")
        if r["competition"] == competition.upper() and r["season"] == season
    ]
    last_run = max(runs, key=lambda r: r["started_at"], default=None)
    return {
        "competition": competition,
        "season": season,
        "last_snapshot": latest["id"] if latest else None,
        "observed_at": latest["fetched_at"] if latest else None,
        "age_hours": age,
        "freshness": "missing" if age is None else "stale" if age > 24 else "fresh",
        "last_update": last_run,
        "quarantined_records": len(read_table(database, "normalization_issues")),
    }


def copy_database(source: Path, target: Path) -> dict:
    if not source.is_file():
        raise ValueError("Banco de origem inexistente")
    if target.exists() or source.resolve() == target.resolve():
        raise ValueError("Destino deve ser um arquivo novo; nenhum banco será sobrescrito")
    target.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(f"file:{quote(str(source.resolve()))}?mode=ro", uri=True) as origin:
        if origin.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Origem falhou na verificação de integridade")
        if not origin.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='snapshots'"
        ).fetchone():
            raise ValueError("Origem não contém snapshots do projeto")
        with target.open("xb"):
            pass
        with sqlite3.connect(target) as destination:
            origin.backup(destination)
            if destination.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Cópia falhou na verificação de integridade; não use esse arquivo")
    return {
        "source": str(source),
        "target": str(target),
        "integrity": "ok",
        "bytes": target.stat().st_size,
    }


def backup(database: Path) -> dict:
    target = (
        database.parent
        / "backups"
        / (datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8] + ".db")
    )
    return copy_database(database, target)
