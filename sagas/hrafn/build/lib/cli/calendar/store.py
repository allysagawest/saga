from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable

from cli.models import EventRecord, SyncState
from cli.utils.time import now_utc


GOOGLE_PROVIDER = "google"


def get_sync_state(connection: sqlite3.Connection, provider: str) -> SyncState:
    row = connection.execute(
        "SELECT provider, sync_token, last_sync FROM sync_state WHERE provider = ?",
        (provider,),
    ).fetchone()
    if row is None:
        return SyncState(provider=provider, sync_token=None, last_sync=None)
    return SyncState(
        provider=row["provider"],
        sync_token=row["sync_token"],
        last_sync=row["last_sync"],
    )


def save_sync_state(
    connection: sqlite3.Connection,
    provider: str,
    sync_token: str | None,
) -> None:
    connection.execute(
        """
        INSERT INTO sync_state (provider, sync_token, last_sync)
        VALUES (?, ?, ?)
        ON CONFLICT(provider) DO UPDATE SET
            sync_token = excluded.sync_token,
            last_sync = excluded.last_sync
        """,
        (provider, sync_token, now_utc().isoformat().replace("+00:00", "Z")),
    )


def get_future_event_ids(connection: sqlite3.Connection, provider: str, now_iso: str) -> set[str]:
    rows = connection.execute(
        """
        SELECT id
        FROM events
        WHERE provider = ?
          AND deleted = 0
          AND end_time >= ?
        """,
        (provider, now_iso),
    ).fetchall()
    return {row["id"] for row in rows}


def mark_missing_events_deleted(
    connection: sqlite3.Connection,
    provider: str,
    retained_ids: Iterable[str],
    now_iso: str,
) -> int:
    retained = set(retained_ids)
    existing = get_future_event_ids(connection, provider, now_iso)
    missing = existing - retained
    for event_id in missing:
        connection.execute(
            "UPDATE events SET deleted = 1 WHERE id = ? AND provider = ?",
            (event_id, provider),
        )
    return len(missing)


def mark_event_deleted(connection: sqlite3.Connection, provider: str, event_id: str) -> None:
    connection.execute(
        "UPDATE events SET deleted = 1 WHERE id = ? AND provider = ?",
        (event_id, provider),
    )


def upsert_event(connection: sqlite3.Connection, event: EventRecord) -> bool:
    existing = connection.execute(
        "SELECT updated_at FROM events WHERE id = ?",
        (event.id,),
    ).fetchone()

    if existing is not None and existing["updated_at"] == event.updated_at:
        return False

    connection.execute(
        """
        INSERT INTO events (
            id, provider, title, start_time, end_time, location,
            updated_at, deleted, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            provider = excluded.provider,
            title = excluded.title,
            start_time = excluded.start_time,
            end_time = excluded.end_time,
            location = excluded.location,
            updated_at = excluded.updated_at,
            deleted = excluded.deleted,
            raw_json = excluded.raw_json
        """,
        (
            event.id,
            event.provider,
            event.title,
            event.start_time,
            event.end_time,
            event.location,
            event.updated_at,
            event.deleted,
            event.raw_json,
        ),
    )
    return True


def google_event_to_record(raw_event: dict[str, object], start_time: str, end_time: str) -> EventRecord:
    return EventRecord(
        id=str(raw_event["id"]),
        provider=GOOGLE_PROVIDER,
        title=str(raw_event.get("summary") or "(untitled event)"),
        start_time=start_time,
        end_time=end_time,
        location=str(raw_event.get("location")) if raw_event.get("location") else None,
        updated_at=str(raw_event.get("updated") or ""),
        deleted=0,
        raw_json=json.dumps(raw_event, sort_keys=True),
    )
