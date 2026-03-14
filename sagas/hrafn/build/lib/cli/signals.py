from __future__ import annotations

from cli.models import EventRecord, SignalRecord
from cli.utils.time import now_local, parse_iso_datetime


def compute_signals(events: list[EventRecord]) -> list[SignalRecord]:
    now = now_local()
    active_signals: list[SignalRecord] = []

    if any(
        0 <= (parse_iso_datetime(event.start).astimezone() - now).total_seconds() <= 600
        for event in events
    ):
        active_signals.append(SignalRecord(name="meeting_starting_soon"))

    if any(
        parse_iso_datetime(event.start).astimezone() <= now
        < parse_iso_datetime(event.end).astimezone()
        for event in events
    ):
        active_signals.append(SignalRecord(name="meeting_live"))

    if _has_focus_window(events, now):
        active_signals.append(SignalRecord(name="focus_window_available"))

    return active_signals


def _has_focus_window(events: list[EventRecord], now) -> bool:
    ordered = sorted(events, key=lambda event: event.start)
    future_events = [
        event for event in ordered if parse_iso_datetime(event.end).astimezone() > now
    ]

    if not future_events:
        return True

    first_start = parse_iso_datetime(future_events[0].start).astimezone()
    if (first_start - now).total_seconds() > 3600:
        return True

    for current, next_event in zip(future_events, future_events[1:]):
        current_end = parse_iso_datetime(current.end).astimezone()
        next_start = parse_iso_datetime(next_event.start).astimezone()
        if (next_start - current_end).total_seconds() > 3600:
            return True

    return False
