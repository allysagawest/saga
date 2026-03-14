from __future__ import annotations

from datetime import UTC, datetime, time, timedelta


def now_local() -> datetime:
    return datetime.now().astimezone()


def now_utc() -> datetime:
    return datetime.now(UTC)


def local_midnight(reference: datetime | None = None) -> datetime:
    current = reference.astimezone() if reference else now_local()
    next_day = current.date() + timedelta(days=1)
    return datetime.combine(next_day, time.min, tzinfo=current.tzinfo)


def parse_iso_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        local_tz = now_local().tzinfo
        return parsed.replace(tzinfo=local_tz)
    return parsed


def to_utc_iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def format_agenda_time(value: str) -> str:
    return parse_iso_datetime(value).astimezone().strftime("%H:%M")


def is_due_today(due_value: str | None, reference: datetime | None = None) -> bool:
    if not due_value:
        return False

    due_dt = parse_iso_datetime(due_value).astimezone()
    current = reference.astimezone() if reference else now_local()
    return current <= due_dt < local_midnight(current)
