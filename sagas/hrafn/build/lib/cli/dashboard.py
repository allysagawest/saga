from __future__ import annotations

import asyncio
from datetime import timedelta

from textual.app import App, ComposeResult
from textual.containers import Grid
from textual.widgets import Static

from cli.bus import BusEvent, HrafnBus
from cli.config import HrafnTheme
from cli.models import EventRecord, FocusWindowRecord, NextMeetingRecord, SignalRecord, TaskRecord
from cli.runtime import HrafnRuntime, upcoming_events
from cli.utils.time import now_local, parse_iso_datetime


def build_dashboard_css(theme: HrafnTheme) -> str:
    colors = _dashboard_colors(theme)
    return f"""
Screen {{
  background: {colors["background"]};
  color: {colors["foreground"]};
}}

#root {{
  layout: grid;
  grid-size: 12 4;
  grid-columns: 1fr 1fr 1fr 1fr 1fr 1fr 1fr 1fr 1fr 1fr 1fr 1fr;
  grid-rows: 3 11 8 8;
  grid-gutter: 1 1;
  padding: 1;
}}

#header {{
  column-span: 12;
  border: round {colors["accent"]};
  background: {colors["panel_alt"]};
  padding: 0 2;
}}

#upcoming {{
  column-span: 8;
}}

#meeting {{
  column-span: 4;
}}

#focus {{
  column-span: 4;
}}

#signals {{
  column-span: 4;
}}

#status {{
  column-span: 4;
}}

#tasks {{
  column-span: 7;
}}

#commands {{
  column-span: 5;
}}

.panel {{
  border: round {colors["primary"]};
  background: {colors["panel"]};
  padding: 1 2;
}}

.title {{
  color: {colors["accent"]};
  text-style: bold;
}}

.muted {{
  color: {colors["muted"]};
}}
"""


class HeaderPanel(Static):
    def __init__(self, bus: HrafnBus, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.bus = bus

    def on_mount(self) -> None:
        self.set_interval(1, self.update_panel)
        self.update_panel()

    def update_panel(self) -> None:
        now = now_local()
        status = self.bus.state.system_status
        countdown = _format_next_sync_countdown(status.next_sync_at)
        if status.next_sync_time and countdown:
            sync_text = f"next sync {countdown}  ->  {status.next_sync_time}"
        elif status.next_sync_time:
            sync_text = f"next sync scheduled  ->  {status.next_sync_time}"
        else:
            sync_text = "next sync unavailable"
        self.update(
            f"[title]HRAFN[/title]  [muted]Operational calendar view[/muted]\n"
            f"{now.strftime('%A %b %d')}  {now.strftime('%H:%M:%S')}  [muted]|[/muted]  {sync_text}"
        )


class UpcomingPanel(Static):
    def update_panel(self, events: list[EventRecord]) -> None:
        lines = ["[title]UPCOMING[/title]"]
        items = upcoming_events(events, limit=3)
        if not items:
            lines.append("No upcoming events in the next 30 days.")
            self.update("\n".join(lines))
            return

        now = now_local()
        for index, event in enumerate(items, start=1):
            start = parse_iso_datetime(event.start).astimezone()
            end = parse_iso_datetime(event.end).astimezone()
            day_label = start.strftime("%a %H:%M") if start.date() == now.date() else start.strftime("%a %b %d  %H:%M")
            lines.extend(
                [
                    f"{index}. {event.title}",
                    f"   {day_label} -> {end.strftime('%H:%M')}  [{event.calendar}]",
                    f"   {_format_relative(start - now) if start > now else 'LIVE'}"
                    + (f"  |  {event.location}" if event.location else ""),
                    "",
                ]
            )
        self.update("\n".join(lines[:-1]))


class NextMeetingPanel(Static):
    def update_panel(self, meeting: NextMeetingRecord | None) -> None:
        if meeting is None:
            self.update("[title]NEXT[/title]\nNo upcoming meeting.")
            return

        start = parse_iso_datetime(meeting.start).astimezone()
        end = parse_iso_datetime(meeting.end).astimezone()
        delta = start - now_local()
        self.update(
            "[title]NEXT[/title]\n"
            f"{meeting.title}\n"
            f"{start.strftime('%a %H:%M')} -> {end.strftime('%H:%M')}\n"
            f"{meeting.calendar}\n"
            f"{_format_countdown(delta)}"
        )


class FocusPanel(Static):
    def update_panel(self, windows: list[FocusWindowRecord]) -> None:
        lines = ["[title]FOCUS WINDOWS[/title]"]
        if not windows:
            lines.append("No focus windows over 1h.")
            self.update("\n".join(lines))
            return
        for window in windows[:4]:
            start = parse_iso_datetime(window.start).astimezone()
            end = parse_iso_datetime(window.end).astimezone()
            lines.append(f"{start.strftime('%H:%M')} -> {end.strftime('%H:%M')}   {_format_minutes(window.duration_minutes)}")
        self.update("\n".join(lines))


class TaskMatrixPanel(Static):
    def update_panel(self, tasks: list[TaskRecord], selected_index: int) -> None:
        lines = ["[title]TASK MATRIX[/title]"]
        if not tasks:
            lines.append("No pending tasks.")
            self.update("\n".join(lines))
            return
        for index, task in enumerate(tasks[:6]):
            cursor = ">" if index == selected_index else " "
            due = ""
            if task.due:
                due_dt = parse_iso_datetime(task.due).astimezone()
                due = f"  [{due_dt.strftime('%H:%M')}]"
            lines.append(f"{cursor} ☐ {task.description}{due}")
        self.update("\n".join(lines))


class SignalsPanel(Static):
    def update_panel(self, signals: list[SignalRecord]) -> None:
        lines = ["[title]SIGNALS[/title]"]
        if not signals:
            lines.append("No active signals.")
            self.update("\n".join(lines))
            return
        for signal in signals:
            lines.append(f"⚡ {signal.name}")
        self.update("\n".join(lines))


class StatusPanel(Static):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._payload: dict[str, str | None] = {}

    def update_panel(self, payload: dict[str, str | None]) -> None:
        self._payload = payload
        lines = [
            "[title]STATUS[/title]",
            f"calendar sync    {payload.get('calendar_sync', 'idle')}",
            f"task sync        {payload.get('task_sync', 'idle')}",
            f"signals          {payload.get('signals', 'idle')}",
        ]
        next_sync_time = payload.get("next_sync_time")
        next_sync_at = payload.get("next_sync_at")
        if next_sync_time or next_sync_at:
            countdown = _format_next_sync_countdown(next_sync_at)
            lines.append(f"next sync       {next_sync_time or 'scheduled'}")
            if countdown:
                lines.append(f"countdown       {countdown}")
        if payload.get("message"):
            lines.extend(["", str(payload["message"])])
        self.update("\n".join(lines))


class CommandsPanel(Static):
    def on_mount(self) -> None:
        self.update(
            "[title]COMMANDS[/title]\n"
            "j/k navigate\n"
            "x complete task\n"
            "J join meeting\n"
            "s sync calendars\n"
            "r refresh\n"
            "q quit"
        )


class HrafnDashboard(App[None]):
    CSS = ""
    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def __init__(self, bus: HrafnBus, runtime: HrafnRuntime) -> None:
        self.bus = bus
        self.runtime = runtime
        self.CSS = build_dashboard_css(bus.state.theme)
        super().__init__()
        self._queue: asyncio.Queue[BusEvent] | None = None
        self._listener: asyncio.Task[None] | None = None

    def compose(self) -> ComposeResult:
        yield Grid(
            HeaderPanel(self.bus, id="header"),
            UpcomingPanel(classes="panel", id="upcoming"),
            NextMeetingPanel(classes="panel", id="meeting"),
            FocusPanel(classes="panel", id="focus"),
            SignalsPanel(classes="panel", id="signals"),
            StatusPanel(classes="panel", id="status"),
            TaskMatrixPanel(classes="panel", id="tasks"),
            CommandsPanel(classes="panel", id="commands"),
            id="root",
        )

    async def on_mount(self) -> None:
        await self.runtime.start()
        self._queue = await self.bus.subscribe()
        self._listener = asyncio.create_task(self._listen_to_bus())
        self._render_all()

    async def on_unmount(self) -> None:
        if self._listener is not None:
            self._listener.cancel()
            await asyncio.gather(self._listener, return_exceptions=True)
        if self._queue is not None:
            await self.bus.unsubscribe(self._queue)
        await self.runtime.stop()

    async def _listen_to_bus(self) -> None:
        assert self._queue is not None
        while True:
            event = await self._queue.get()
            self.call_next(self._apply_event, event)

    def _apply_event(self, event: BusEvent) -> None:
        if event.name in {"calendar_updated"}:
            self.query_one(UpcomingPanel).update_panel(self.bus.state.events)
        if event.name in {"calendar_updated", "next_meeting_changed", "clock_tick"}:
            self.query_one(NextMeetingPanel).update_panel(self.bus.state.next_meeting)
        if event.name in {"focus_windows_updated", "calendar_updated"}:
            self.query_one(FocusPanel).update_panel(self.bus.state.focus_windows)
        if event.name in {"tasks_updated", "task_selection_changed"}:
            self.query_one(TaskMatrixPanel).update_panel(self.bus.state.tasks, self.bus.state.selected_task_index)
        if event.name in {"signals_updated"}:
            self.query_one(SignalsPanel).update_panel(self.bus.state.signals)
        if event.name in {"system_status_updated", "calendar_sync_complete", "task_completed", "join_next_meeting", "clock_tick"}:
            self.query_one(StatusPanel).update_panel(self.bus.state.system_status.to_dict())

    def _render_all(self) -> None:
        self.query_one(UpcomingPanel).update_panel(self.bus.state.events)
        self.query_one(NextMeetingPanel).update_panel(self.bus.state.next_meeting)
        self.query_one(FocusPanel).update_panel(self.bus.state.focus_windows)
        self.query_one(TaskMatrixPanel).update_panel(self.bus.state.tasks, self.bus.state.selected_task_index)
        self.query_one(SignalsPanel).update_panel(self.bus.state.signals)
        self.query_one(StatusPanel).update_panel(self.bus.state.system_status.to_dict())

    async def on_key(self, event) -> None:
        key = event.key
        if key == "j":
            await self.bus.move_task_selection(1)
        elif key == "k":
            await self.bus.move_task_selection(-1)
        elif key == "x":
            tasks = self.bus.state.tasks
            if tasks:
                task = tasks[self.bus.state.selected_task_index]
                await self.bus.publish("complete_task", {"task_id": task.id})
        elif key == "J":
            await self.bus.publish("join_next_meeting")
        elif key == "s":
            await self.bus.publish("calendar_sync_requested")
        elif key == "r":
            await self.bus.publish("refresh_requested")


def _dashboard_colors(theme: HrafnTheme) -> dict[str, str]:
    return {
        "primary": theme.colors.get("primary", theme.colors.get("agenda_time", "#37d7ff")),
        "accent": theme.colors.get("accent", theme.colors.get("meeting_starting_soon", "#ff4fd8")),
        "background": theme.colors.get("background", "#090b12"),
        "foreground": theme.colors.get("foreground", theme.colors.get("agenda_title", "#d7f7ff")),
        "panel": theme.colors.get("panel", "#111827"),
        "panel_alt": theme.colors.get("surface", theme.colors.get("panel", "#111827")),
        "muted": theme.colors.get("sync_status", "#6e89a6"),
    }


def _format_countdown(delta: timedelta) -> str:
    total_seconds = int(delta.total_seconds())
    if total_seconds <= 0:
        return "LIVE"
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _format_next_sync_countdown(next_sync_at: str | None) -> str | None:
    if not next_sync_at:
        return None
    target = parse_iso_datetime(next_sync_at).astimezone()
    return _format_countdown(target - now_local())


def _format_minutes(minutes: int) -> str:
    hours, remainder = divmod(minutes, 60)
    if hours:
        return f"{hours}h{remainder:02d}m"
    return f"{remainder}m"


def _format_relative(delta: timedelta) -> str:
    total_seconds = int(delta.total_seconds())
    if total_seconds <= 0:
        return "LIVE"
    minutes = total_seconds // 60
    if minutes < 60:
        return f"in {minutes}m"
    hours, remainder = divmod(minutes, 60)
    if hours < 24:
        return f"in {hours}h {remainder:02d}m"
    days, rem_hours = divmod(hours, 24)
    return f"in {days}d {rem_hours}h"
