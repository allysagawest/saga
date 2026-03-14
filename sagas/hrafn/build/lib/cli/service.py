from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
import re

from cli.config import HrafnSyncServiceConfig, load_sync_service_config, save_sync_service_config


class HrafnServiceError(RuntimeError):
    """Raised when the background sync service cannot be managed."""


@dataclass(frozen=True)
class HrafnServiceStatus:
    enabled: bool
    interval_minutes: int
    timer_installed: bool
    timer_enabled: bool
    timer_active: bool
    next_sync_time: str | None
    next_sync_in_seconds: int | None


def user_systemd_dir() -> Path:
    return Path.home() / ".config" / "systemd" / "user"


def service_unit_path() -> Path:
    return user_systemd_dir() / "hrafn-sync.service"


def timer_unit_path() -> Path:
    return user_systemd_dir() / "hrafn-sync.timer"


def render_service_unit() -> str:
    exec_start = str(Path.home() / ".local" / "bin" / "hrafn")
    return "\n".join(
        [
            "[Unit]",
            "Description=Hrafn calendar background sync",
            "After=network-online.target",
            "Wants=network-online.target",
            "",
            "[Service]",
            "Type=oneshot",
            f"ExecStart={exec_start} sync",
            "",
        ]
    )


def render_timer_unit(interval_minutes: int) -> str:
    interval = max(1, interval_minutes)
    return "\n".join(
        [
            "[Unit]",
            "Description=Run Hrafn calendar sync on a schedule",
            "",
            "[Timer]",
            "OnBootSec=2min",
            f"OnUnitActiveSec={interval}min",
            "AccuracySec=1min",
            "Persistent=true",
            "Unit=hrafn-sync.service",
            "",
            "[Install]",
            "WantedBy=timers.target",
            "",
        ]
    )


def install_sync_service(config: HrafnSyncServiceConfig | None = None) -> None:
    resolved = config or load_sync_service_config()
    systemd_dir = user_systemd_dir()
    systemd_dir.mkdir(parents=True, exist_ok=True)
    service_unit_path().write_text(render_service_unit(), encoding="utf-8")
    timer_unit_path().write_text(render_timer_unit(resolved.interval_minutes), encoding="utf-8")
    save_sync_service_config(resolved)
    _run_systemctl("--user", "daemon-reload")
    if resolved.enabled:
        _run_systemctl("--user", "enable", "--now", "hrafn-sync.timer")
    else:
        _run_systemctl("--user", "disable", "--now", "hrafn-sync.timer", check=False)


def uninstall_sync_service() -> None:
    _run_systemctl("--user", "disable", "--now", "hrafn-sync.timer", check=False)
    _run_systemctl("--user", "daemon-reload", check=False)
    if service_unit_path().exists():
        service_unit_path().unlink()
    if timer_unit_path().exists():
        timer_unit_path().unlink()
    _run_systemctl("--user", "daemon-reload", check=False)


def configure_sync_service(*, interval_minutes: int | None = None, enabled: bool | None = None) -> HrafnSyncServiceConfig:
    current = load_sync_service_config()
    updated = HrafnSyncServiceConfig(
        enabled=current.enabled if enabled is None else enabled,
        interval_minutes=current.interval_minutes if interval_minutes is None else max(1, interval_minutes),
    )
    save_sync_service_config(updated)
    install_sync_service(updated)
    return updated


def service_status() -> HrafnServiceStatus:
    config = load_sync_service_config()
    installed = timer_unit_path().exists() and service_unit_path().exists()
    timer_enabled = _is_systemctl_state("is-enabled", "hrafn-sync.timer")
    timer_active = _is_systemctl_state("is-active", "hrafn-sync.timer")
    next_sync_time, next_sync_in_seconds = _read_timer_schedule()
    return HrafnServiceStatus(
        enabled=config.enabled,
        interval_minutes=config.interval_minutes,
        timer_installed=installed,
        timer_enabled=timer_enabled,
        timer_active=timer_active,
        next_sync_time=next_sync_time,
        next_sync_in_seconds=next_sync_in_seconds,
    )


def _is_systemctl_state(command: str, unit: str) -> bool:
    try:
        result = subprocess.run(
            ["systemctl", "--user", command, unit],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return False
    return result.returncode == 0


def _run_systemctl(*args: str, check: bool = True) -> None:
    try:
        result = subprocess.run(
            ["systemctl", *args],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise HrafnServiceError("systemctl is required to manage the Hrafn background sync timer.") from exc

    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout).strip() or "systemctl command failed."
        raise HrafnServiceError(detail)


def _read_timer_schedule() -> tuple[str | None, int | None]:
    try:
        result = subprocess.run(
            [
                "systemctl",
                "--user",
                "status",
                "hrafn-sync.timer",
                "--no-pager",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None, None

    if result.returncode != 0:
        return None, None

    match = re.search(r"Trigger:\s+(.+?);\s+(.+?)\s+left", result.stdout)
    if not match:
        return None, None
    next_sync_time = match.group(1).strip()
    next_sync_in_seconds = _parse_systemd_duration(match.group(2).strip())
    return next_sync_time, next_sync_in_seconds


def _parse_systemd_duration(value: str) -> int | None:
    text = value.strip()
    if not text or text == "-":
        return None

    total_seconds = 0.0
    for amount, unit in re.findall(r"(\d+(?:\.\d+)?)\s*(day|days|h|min|ms|s)", text):
        number = float(amount)
        if unit in {"day", "days"}:
            total_seconds += number * 86400
        elif unit == "h":
            total_seconds += number * 3600
        elif unit == "min":
            total_seconds += number * 60
        elif unit == "s":
            total_seconds += number
        elif unit == "ms":
            total_seconds += number / 1000
    return int(total_seconds) if total_seconds > 0 else None
