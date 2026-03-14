from __future__ import annotations

import asyncio
from datetime import timedelta

from cli.bus import HrafnBus
from cli.calendar.stack import CalendarStackError, read_agenda, run_vdirsyncer_sync
from cli.models import (
    EventRecord,
    FocusWindowRecord,
    NextMeetingRecord,
    SystemStatusRecord,
)
from cli.service import HrafnServiceError, service_status
from cli.signals import compute_signals
from cli.tasks.reader import TaskReaderError, complete_task, read_tasks
from cli.utils.time import now_local, parse_iso_datetime


class HrafnRuntime:
    def __init__(self, bus: HrafnBus) -> None:
        self.bus = bus
        self._queue: asyncio.Queue | None = None
        self._tasks: list[asyncio.Task[None]] = []
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._queue = await self.bus.subscribe()
        self._tasks = [
            asyncio.create_task(self._handle_events(), name="hrafn-bus-handler"),
            asyncio.create_task(self._clock_tick(), name="hrafn-clock-tick"),
            asyncio.create_task(self._calendar_poll(), name="hrafn-calendar-poll"),
            asyncio.create_task(self._task_poll(), name="hrafn-task-poll"),
        ]
        await self.refresh_all()

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        if self._queue is not None:
            await self.bus.unsubscribe(self._queue)
            self._queue = None

    async def refresh_all(self) -> None:
        await self._refresh_calendar_state()
        await self._refresh_task_state()

    async def _handle_events(self) -> None:
        assert self._queue is not None
        while self._running:
            event = await self._queue.get()
            if event.name == "calendar_sync_requested":
                await self._run_calendar_sync()
            elif event.name == "refresh_requested":
                await self.refresh_all()
            elif event.name == "complete_task":
                task_id = str(event.payload.get("task_id") or "")
                if task_id:
                    await self._complete_task(task_id)
            elif event.name == "join_next_meeting":
                await self._mark_system_message("join_next_meeting published")

    async def _clock_tick(self) -> None:
        while self._running:
            await self.bus.publish("clock_tick", {"now": now_local().isoformat()})
            await asyncio.sleep(1)

    async def _calendar_poll(self) -> None:
        while self._running:
            await asyncio.sleep(30)
            await self._refresh_calendar_state()

    async def _task_poll(self) -> None:
        while self._running:
            await asyncio.sleep(15)
            await self._refresh_task_state()

    async def _refresh_calendar_state(self) -> None:
        timer_sync = _current_timer_status()
        try:
            events = read_agenda(days=30)
            status = self.bus.state.system_status
            await self.bus.update_events(events)
            await self.bus.update_next_meeting(_compute_next_meeting(events))
            await self.bus.update_focus_windows(_compute_focus_windows(events))
            await self.bus.update_signals(compute_signals(events))
            await self.bus.update_system_status(
                SystemStatusRecord(
                    calendar_sync="ok",
                    task_sync=status.task_sync,
                    signals="active",
                    message=status.message,
                    next_sync_time=timer_sync.next_sync_time,
                    next_sync_at=timer_sync.next_sync_at,
                )
            )
        except CalendarStackError as exc:
            status = self.bus.state.system_status
            await self.bus.update_system_status(
                SystemStatusRecord(
                    calendar_sync="error",
                    task_sync=status.task_sync,
                    signals="stale",
                    message=str(exc),
                    next_sync_time=timer_sync.next_sync_time,
                    next_sync_at=timer_sync.next_sync_at,
                )
            )

    async def _refresh_task_state(self) -> None:
        try:
            tasks = read_tasks(include_completed=False)
            status = self.bus.state.system_status
            await self.bus.update_tasks(tasks)
            await self.bus.update_system_status(
                SystemStatusRecord(
                    calendar_sync=status.calendar_sync,
                    task_sync="ok",
                    signals=status.signals,
                    message=status.message,
                    next_sync_time=status.next_sync_time,
                    next_sync_at=status.next_sync_at,
                )
            )
        except TaskReaderError as exc:
            status = self.bus.state.system_status
            await self.bus.update_tasks([])
            await self.bus.update_system_status(
                SystemStatusRecord(
                    calendar_sync=status.calendar_sync,
                    task_sync="error",
                    signals=status.signals,
                    message=str(exc),
                    next_sync_time=status.next_sync_time,
                    next_sync_at=status.next_sync_at,
                )
            )

    async def _run_calendar_sync(self) -> None:
        status = self.bus.state.system_status
        await self.bus.update_system_status(
            SystemStatusRecord(
                calendar_sync="syncing",
                task_sync=status.task_sync,
                signals=status.signals,
                message="calendar sync requested",
                next_sync_time=status.next_sync_time,
                next_sync_at=status.next_sync_at,
            )
        )
        try:
            output = run_vdirsyncer_sync()
            await self.bus.publish("calendar_sync_complete", {"output": output})
            await self._refresh_calendar_state()
        except CalendarStackError as exc:
            await self._mark_system_message(str(exc), calendar_sync="error")

    async def _complete_task(self, task_id: str) -> None:
        try:
            output = complete_task(task_id)
            await self.bus.publish("task_completed", {"task_id": task_id, "output": output})
            await self._refresh_task_state()
        except TaskReaderError as exc:
            await self._mark_system_message(str(exc), task_sync="error")

    async def _mark_system_message(
        self,
        message: str,
        *,
        calendar_sync: str | None = None,
        task_sync: str | None = None,
        signals: str | None = None,
    ) -> None:
        status = self.bus.state.system_status
        await self.bus.update_system_status(
            SystemStatusRecord(
                calendar_sync=calendar_sync or status.calendar_sync,
                task_sync=task_sync or status.task_sync,
                signals=signals or status.signals,
                message=message,
                next_sync_time=status.next_sync_time,
                next_sync_at=status.next_sync_at,
            )
        )


class _TimerStatus:
    def __init__(self, next_sync_time: str | None, next_sync_at: str | None) -> None:
        self.next_sync_time = next_sync_time
        self.next_sync_at = next_sync_at


def _current_timer_status() -> _TimerStatus:
    try:
        status = service_status()
    except HrafnServiceError:
        return _TimerStatus(next_sync_time=None, next_sync_at=None)

    next_sync_at = None
    if status.next_sync_in_seconds is not None:
        next_sync_at = (now_local() + timedelta(seconds=status.next_sync_in_seconds)).isoformat()
    return _TimerStatus(next_sync_time=status.next_sync_time, next_sync_at=next_sync_at)


def _compute_next_meeting(events: list[EventRecord]) -> NextMeetingRecord | None:
    for event in upcoming_events(events, limit=1):
        return NextMeetingRecord(
            title=event.title,
            calendar=event.calendar,
            start=event.start,
            end=event.end,
            location=event.location,
        )
    return None


def upcoming_events(events: list[EventRecord], *, limit: int | None = None) -> list[EventRecord]:
    now = now_local()
    ordered = sorted(events, key=lambda item: item.start)
    upcoming = [
        event
        for event in ordered
        if parse_iso_datetime(event.end).astimezone() >= now
    ]
    if limit is None:
        return upcoming
    return upcoming[:limit]


def _compute_focus_windows(events: list[EventRecord]) -> list[FocusWindowRecord]:
    now = now_local()
    today_events = [
        event
        for event in sorted(events, key=lambda item: item.start)
        if parse_iso_datetime(event.start).astimezone().date() == now.date()
    ]
    windows: list[FocusWindowRecord] = []
    for current, next_event in zip(today_events, today_events[1:]):
        current_end = parse_iso_datetime(current.end).astimezone()
        next_start = parse_iso_datetime(next_event.start).astimezone()
        gap_minutes = int((next_start - current_end).total_seconds() // 60)
        if gap_minutes > 60:
            windows.append(
                FocusWindowRecord(
                    start=current.end,
                    end=next_event.start,
                    duration_minutes=gap_minutes,
                )
            )
    return windows
