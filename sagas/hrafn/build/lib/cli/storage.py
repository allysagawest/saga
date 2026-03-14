from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from .config import ensure_runtime_dirs


EVENTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    provider TEXT,
    title TEXT,
    start_time TEXT,
    end_time TEXT,
    location TEXT,
    updated_at TEXT,
    deleted INTEGER,
    raw_json TEXT
)
"""

SYNC_STATE_SCHEMA = """
CREATE TABLE IF NOT EXISTS sync_state (
    provider TEXT PRIMARY KEY,
    sync_token TEXT,
    last_sync TEXT
)
"""


def get_connection() -> sqlite3.Connection:
    paths = ensure_runtime_dirs()
    connection = sqlite3.connect(paths.database_file)
    connection.row_factory = sqlite3.Row
    connection.execute(EVENTS_SCHEMA)
    connection.execute(SYNC_STATE_SCHEMA)
    connection.commit()
    return connection


@contextmanager
def managed_connection() -> Iterator[sqlite3.Connection]:
    connection = get_connection()
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()
