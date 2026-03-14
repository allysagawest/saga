from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from cli.config import HrafnTheme
from cli.models import (
    EventRecord,
    FocusWindowRecord,
    NextMeetingRecord,
    SignalRecord,
    SystemStatusRecord,
    TaskRecord,
)


@dataclass(slots=True)
class BusEvent:
    name: str
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass(slots=True)
class HrafnState:
    theme: HrafnTheme
    events: list[EventRecord] = field(default_factory=list)
    tasks: list[TaskRecord] = field(default_factory=list)
    signals: list[SignalRecord] = field(default_factory=list)
    next_meeting: NextMeetingRecord | None = None
    focus_windows: list[FocusWindowRecord] = field(default_factory=list)
    system_status: SystemStatusRecord = field(
        default_factory=lambda: SystemStatusRecord(
            calendar_sync="idle",
            task_sync="idle",
            signals="idle",
            message=None,
        )
    )
    selected_task_index: int = 0


class HrafnBus:
    def __init__(self, initial_state: HrafnState) -> None:
        self._state = initial_state
        self._subscribers: set[asyncio.Queue[BusEvent]] = set()
        self._lock = asyncio.Lock()

    @property
    def state(self) -> HrafnState:
        return self._state

    async def subscribe(self) -> asyncio.Queue[BusEvent]:
        queue: asyncio.Queue[BusEvent] = asyncio.Queue()
        async with self._lock:
            self._subscribers.add(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue[BusEvent]) -> None:
        async with self._lock:
            self._subscribers.discard(queue)

    async def publish(self, name: str, payload: dict[str, Any] | None = None) -> None:
        event = BusEvent(name=name, payload=payload or {})
        async with self._lock:
            subscribers = list(self._subscribers)
        for queue in subscribers:
            await queue.put(event)

    async def update_events(self, events: list[EventRecord]) -> None:
        self._state.events = events
        await self.publish("calendar_updated", {"events": [event.to_dict() for event in events]})

    async def update_tasks(self, tasks: list[TaskRecord]) -> None:
        self._state.tasks = tasks
        if self._state.selected_task_index >= len(tasks):
            self._state.selected_task_index = max(0, len(tasks) - 1)
        await self.publish("tasks_updated", {"tasks": [task.to_dict() for task in tasks]})

    async def update_signals(self, signals: list[SignalRecord]) -> None:
        self._state.signals = signals
        await self.publish("signals_updated", {"signals": [signal.to_dict() for signal in signals]})

    async def update_next_meeting(self, meeting: NextMeetingRecord | None) -> None:
        self._state.next_meeting = meeting
        await self.publish(
            "next_meeting_changed",
            {"next_meeting": meeting.to_dict() if meeting else None},
        )

    async def update_focus_windows(self, windows: list[FocusWindowRecord]) -> None:
        self._state.focus_windows = windows
        await self.publish(
            "focus_windows_updated",
            {"focus_windows": [window.to_dict() for window in windows]},
        )

    async def update_system_status(self, status: SystemStatusRecord) -> None:
        self._state.system_status = status
        await self.publish("system_status_updated", {"system_status": status.to_dict()})

    async def move_task_selection(self, delta: int) -> None:
        tasks = self._state.tasks
        if not tasks:
            self._state.selected_task_index = 0
        else:
            self._state.selected_task_index = max(
                0,
                min(self._state.selected_task_index + delta, len(tasks) - 1),
            )
        await self.publish(
            "task_selection_changed",
            {"selected_task_index": self._state.selected_task_index},
        )
