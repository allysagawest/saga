from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
from collections.abc import Sequence

from cli.models import TaskRecord
from cli.utils.time import is_due_today


class TaskReaderError(RuntimeError):
    """Raised when Taskwarrior data cannot be read."""


def taskwarrior_is_initialized() -> bool:
    return Path.home().joinpath(".taskrc").exists() and Path.home().joinpath(".task").is_dir()


def _normalize_task(raw_task: dict[str, object]) -> TaskRecord:
    return TaskRecord(
        id=str(raw_task.get("id") or raw_task.get("uuid") or ""),
        uuid=str(raw_task["uuid"]) if raw_task.get("uuid") else None,
        description=str(raw_task.get("description") or "(untitled task)"),
        due=str(raw_task["due"]) if raw_task.get("due") else None,
        project=str(raw_task["project"]) if raw_task.get("project") else None,
        priority=str(raw_task["priority"]) if raw_task.get("priority") else None,
    )


def ensure_taskwarrior() -> None:
    if shutil.which("task") is None:
        raise TaskReaderError(
            "Taskwarrior is not installed or not on PATH. Install Hrafn again or install Taskwarrior to use 'hrafn tasks'."
        )
    if not taskwarrior_is_initialized():
        raise TaskReaderError(
            "Taskwarrior is installed but not initialized. Run 'hrafn tasks init' to create ~/.taskrc and ~/.task."
        )


def _run_task_command(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
    ensure_taskwarrior()

    try:
        return subprocess.run(
            ["task", *args],
            capture_output=True,
            check=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() or "Taskwarrior returned a non-zero exit status."
        if "Cannot proceed without rc file." in stderr:
            raise TaskReaderError(
                "Taskwarrior is installed but not initialized. Run 'hrafn tasks init' to create ~/.taskrc and ~/.task."
            ) from exc
        raise TaskReaderError(f"Failed to read Taskwarrior data: {stderr}") from exc


def read_tasks(include_completed: bool = False) -> list[TaskRecord]:
    export_args = ["status:pending", "export"]
    if include_completed:
        export_args = ["export"]

    result = _run_task_command(export_args)

    try:
        payload = json.loads(result.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise TaskReaderError("Taskwarrior returned invalid JSON from 'task export'.") from exc

    return [_normalize_task(raw_task) for raw_task in payload]


def read_tasks_due_today() -> list[TaskRecord]:
    tasks = read_tasks(include_completed=False)
    return [task for task in tasks if is_due_today(task.due)]


def add_task(
    description: str,
    *,
    due: str | None = None,
    project: str | None = None,
    priority: str | None = None,
) -> str:
    args = ["add", description]
    if due:
        args.append(f"due:{due}")
    if project:
        args.append(f"project:{project}")
    if priority:
        args.append(f"priority:{priority}")

    result = _run_task_command(args)
    return result.stdout.strip() or "Task added."


def complete_task(task_id: str) -> str:
    result = _run_task_command([task_id, "done"])
    return result.stdout.strip() or f"Task {task_id} completed."


def remove_task(task_id: str) -> str:
    result = _run_task_command([task_id, "delete", "rc.confirmation=no"])
    return result.stdout.strip() or f"Task {task_id} deleted."


def initialize_taskwarrior() -> str:
    rc_path = Path.home() / ".taskrc"
    data_path = Path.home() / ".task"

    data_path.mkdir(parents=True, exist_ok=True)
    if not rc_path.exists():
        rc_path.write_text(
            "data.location=~/.task\n"
            "confirmation=1\n"
            "verbose=new-id,edit,special,unwait\n",
            encoding="utf-8",
        )
        return f"Initialized Taskwarrior at {rc_path} with data directory {data_path}."

    return f"Taskwarrior already initialized at {rc_path}."
