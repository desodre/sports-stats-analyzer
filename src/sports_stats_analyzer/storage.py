"""Snapshots imutáveis para auditoria e reprocessamento futuro."""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def save_snapshot(
    database: Path,
    endpoint: str,
    params: dict[str, Any],
    payload: dict[str, Any],
) -> int:
    database.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY,
                provider TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                params_json TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
        """)
        cursor = connection.execute(
            "INSERT INTO snapshots "
            "(provider, endpoint, params_json, fetched_at, payload_json) VALUES (?, ?, ?, ?, ?)",
            (
                "football-data.org",
                endpoint,
                json.dumps(params, sort_keys=True),
                datetime.now(UTC).isoformat(),
                json.dumps(payload, ensure_ascii=False),
            ),
        )
        assert cursor.lastrowid is not None
        return cursor.lastrowid
