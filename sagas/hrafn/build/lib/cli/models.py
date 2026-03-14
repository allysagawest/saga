from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class EventRecord:
    title: str
    start: str
    end: str
    calendar: str
    location: str | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class TaskRecord:
    id: str
    uuid: str | None
    description: str
    due: str | None
    project: str | None
    priority: str | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class SignalRecord:
    name: str

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name}


@dataclass(slots=True)
class NextMeetingRecord:
    title: str
    calendar: str
    start: str
    end: str
    location: str | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class FocusWindowRecord:
    start: str
    end: str
    duration_minutes: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class SystemStatusRecord:
    calendar_sync: str
    task_sync: str
    signals: str
    message: str | None = None
    next_sync_time: str | None = None
    next_sync_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
