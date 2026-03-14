from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from googleapiclient.errors import HttpError

from cli.calendar.google import GoogleCalendarError, build_calendar_service
from cli.calendar.store import (
    GOOGLE_PROVIDER,
    get_sync_state,
    google_event_to_record,
    mark_event_deleted,
    mark_missing_events_deleted,
    save_sync_state,
    upsert_event,
)
from cli.storage import managed_connection
from cli.utils.time import google_event_bounds, now_utc, to_utc_iso


@dataclass(slots=True)
class SyncResult:
    created_or_updated: int
    deleted: int
    sync_token: str | None
    full_sync: bool


class CalendarSyncEngine:
    def sync_google_calendar(self) -> SyncResult:
        service = build_calendar_service()
        with managed_connection() as connection:
            state = get_sync_state(connection, GOOGLE_PROVIDER)

            try:
                if state.sync_token:
                    return self._run_incremental_sync(connection, service, state.sync_token)
                return self._run_full_sync(connection, service)
            except HttpError as exc:
                if getattr(exc.resp, "status", None) == 410:
                    save_sync_state(connection, GOOGLE_PROVIDER, None)
                    return self._run_full_sync(connection, service)
                raise GoogleCalendarError(f"Google Calendar sync failed: {exc}") from exc
            except Exception as exc:  # pragma: no cover - network/client library behavior
                raise GoogleCalendarError(f"Google Calendar sync failed: {exc}") from exc

    def _run_full_sync(self, connection, service) -> SyncResult:
        time_min = to_utc_iso(now_utc())
        page_token: str | None = None
        created_or_updated = 0
        deleted = 0
        retained_ids: set[str] = set()
        sync_token: str | None = None

        while True:
            response = (
                service.events()
                .list(
                    calendarId="primary",
                    singleEvents=True,
                    orderBy="startTime",
                    timeMin=time_min,
                    showDeleted=True,
                    pageToken=page_token,
                )
                .execute()
            )

            page_created, page_deleted, page_ids = self._process_event_page(
                connection,
                response.get("items", []),
            )
            created_or_updated += page_created
            deleted += page_deleted
            retained_ids.update(page_ids)

            page_token = response.get("nextPageToken")
            if not page_token:
                sync_token = response.get("nextSyncToken")
                break

        deleted += mark_missing_events_deleted(
            connection,
            GOOGLE_PROVIDER,
            retained_ids,
            time_min,
        )
        save_sync_state(connection, GOOGLE_PROVIDER, sync_token)
        return SyncResult(
            created_or_updated=created_or_updated,
            deleted=deleted,
            sync_token=sync_token,
            full_sync=True,
        )

    def _run_incremental_sync(self, connection, service, sync_token: str) -> SyncResult:
        page_token: str | None = None
        created_or_updated = 0
        deleted = 0
        next_sync_token = sync_token

        while True:
            response = (
                service.events()
                .list(
                    calendarId="primary",
                    syncToken=sync_token,
                    showDeleted=True,
                    pageToken=page_token,
                )
                .execute()
            )

            page_created, page_deleted, _ = self._process_event_page(
                connection,
                response.get("items", []),
            )
            created_or_updated += page_created
            deleted += page_deleted

            page_token = response.get("nextPageToken")
            if not page_token:
                next_sync_token = response.get("nextSyncToken", sync_token)
                break

        save_sync_state(connection, GOOGLE_PROVIDER, next_sync_token)
        return SyncResult(
            created_or_updated=created_or_updated,
            deleted=deleted,
            sync_token=next_sync_token,
            full_sync=False,
        )

    def _process_event_page(self, connection, items: list[dict[str, Any]]) -> tuple[int, int, set[str]]:
        created_or_updated = 0
        deleted = 0
        retained_ids: set[str] = set()

        for raw_event in items:
            event_id = str(raw_event.get("id") or "")
            if not event_id:
                continue

            status = str(raw_event.get("status") or "")
            if status == "cancelled":
                mark_event_deleted(connection, GOOGLE_PROVIDER, event_id)
                deleted += 1
                continue

            start_time, end_time = google_event_bounds(raw_event)
            retained_ids.add(event_id)
            event = google_event_to_record(raw_event, start_time, end_time)
            if upsert_event(connection, event):
                created_or_updated += 1

        return created_or_updated, deleted, retained_ids
