from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any

APP_DIR = Path(__file__).resolve().parent
configured_path = Path(os.getenv("DATABASE_PATH", "data/testpilot.db")).expanduser()
DB_PATH = configured_path if configured_path.is_absolute() else APP_DIR / configured_path


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db() -> None:
    with closing(get_conn()) as conn:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_name TEXT NOT NULL,
                    source_text TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    requirements_json TEXT NOT NULL,
                    cases_json TEXT NOT NULL,
                    summary_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )


def save_analysis(
    project_name: str,
    source_text: str,
    mode: str,
    requirements: list[dict[str, Any]],
    cases: list[dict[str, Any]],
    summary: dict[str, Any],
) -> int:
    with closing(get_conn()) as conn:
        with conn:
            cur = conn.execute(
                """
                INSERT INTO analyses
                    (project_name, source_text, mode, requirements_json, cases_json, summary_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_name,
                    source_text,
                    mode,
                    json.dumps(requirements, ensure_ascii=False),
                    json.dumps(cases, ensure_ascii=False),
                    json.dumps(summary, ensure_ascii=False),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            return int(cur.lastrowid)


def _decode(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(row)
    data["requirements"] = json.loads(data.pop("requirements_json"))
    data["cases"] = json.loads(data.pop("cases_json"))
    data["summary"] = json.loads(data.pop("summary_json"))
    return data


def get_analysis(analysis_id: int) -> dict[str, Any] | None:
    with closing(get_conn()) as conn:
        row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
        return _decode(row)


def list_analyses(limit: int = 8) -> list[dict[str, Any]]:
    with closing(get_conn()) as conn:
        rows = conn.execute(
            "SELECT * FROM analyses ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_decode(row) for row in rows if row is not None]
