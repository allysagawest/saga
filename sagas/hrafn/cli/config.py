from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from typing import Any


@dataclass(frozen=True)
class HrafnPaths:
    config_dir: Path
    config_file: Path
    calendar_stack_file: Path
    calendar_mirror_state_file: Path
    theme_file: Path


@dataclass(frozen=True)
class HrafnTheme:
    colors: dict[str, str]
    fonts: dict[str, str | int]


@dataclass(frozen=True)
class HrafnSyncServiceConfig:
    enabled: bool = True
    interval_minutes: int = 5


DEFAULT_THEME = HrafnTheme(
    colors={
        "agenda_time": "#6ba8f0",
        "agenda_title": "#e6edf3",
        "task": "#6fbf8f",
        "empty": "#a8b3bf",
        "meeting_starting_soon": "#4a90e2",
        "meeting_live": "#6fbf8f",
        "tasks_due_today": "#d66a6a",
        "focus_window_available": "#7f8c9a",
        "sync_status": "#6ba8f0",
        "error": "#d66a6a",
        "warning": "#d6a76a",
    },
    fonts={
        "ui": "JetBrainsMono Nerd Font",
        "display": "JetBrainsMono Nerd Font",
        "size": 12,
    },
)


def get_paths() -> HrafnPaths:
    home = Path.home()
    config_dir = home / ".config" / "hrafn"
    return HrafnPaths(
        config_dir=config_dir,
        config_file=config_dir / "config.toml",
        calendar_stack_file=config_dir / "calendar-stack.json",
        calendar_mirror_state_file=config_dir / "calendar-mirror-state.json",
        theme_file=config_dir / "theme.json",
    )


def ensure_runtime_dirs() -> HrafnPaths:
    paths = get_paths()
    paths.config_dir.mkdir(parents=True, exist_ok=True)
    if not paths.config_file.exists():
        paths.config_file.write_text(default_config_text(), encoding="utf-8")
    return paths


def load_theme() -> HrafnTheme:
    paths = ensure_runtime_dirs()
    if not paths.theme_file.exists():
        return DEFAULT_THEME

    try:
        payload = json.loads(paths.theme_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return DEFAULT_THEME

    colors = DEFAULT_THEME.colors | _as_dict(payload.get("colors"))
    fonts = DEFAULT_THEME.fonts | _as_dict(payload.get("fonts"))
    return HrafnTheme(colors=colors, fonts=fonts)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def load_hrafn_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}

    return cast(dict[str, Any], payload if isinstance(payload, dict) else {})


def default_config_text() -> str:
    return (
        "# Hrafn configuration\n"
        "# User settings and managed sync-service settings live here.\n\n"
        "# >>> Hrafn managed sync service >>>\n"
        "[sync_service]\n"
        "enabled = true\n"
        "interval_minutes = 5\n"
        "# <<< Hrafn managed sync service <<<\n"
    )


def load_sync_service_config() -> HrafnSyncServiceConfig:
    paths = ensure_runtime_dirs()
    defaults = HrafnSyncServiceConfig()

    try:
        payload = tomllib.loads(paths.config_file.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return defaults

    section = payload.get("sync_service")
    if not isinstance(section, dict):
        return defaults

    interval = section.get("interval_minutes", defaults.interval_minutes)
    if not isinstance(interval, int):
        interval = defaults.interval_minutes
    interval = max(1, interval)

    enabled = section.get("enabled", defaults.enabled)
    if not isinstance(enabled, bool):
        enabled = defaults.enabled

    return HrafnSyncServiceConfig(enabled=enabled, interval_minutes=interval)


def save_sync_service_config(config: HrafnSyncServiceConfig) -> None:
    paths = ensure_runtime_dirs()
    existing = paths.config_file.read_text(encoding="utf-8") if paths.config_file.exists() else ""
    managed_block = (
        "# >>> Hrafn managed sync service >>>\n"
        "[sync_service]\n"
        f"enabled = {'true' if config.enabled else 'false'}\n"
        f"interval_minutes = {max(1, config.interval_minutes)}\n"
        "# <<< Hrafn managed sync service <<<"
    )
    start_marker = "# >>> Hrafn managed sync service >>>"
    end_marker = "# <<< Hrafn managed sync service <<<"

    if start_marker in existing and end_marker in existing:
        prefix, remainder = existing.split(start_marker, 1)
        _, suffix = remainder.split(end_marker, 1)
        updated = prefix.rstrip() + "\n\n" + managed_block + suffix
    else:
        updated = existing.rstrip()
        if updated:
            updated += "\n\n"
        updated += managed_block + "\n"

    paths.config_file.write_text(updated, encoding="utf-8")
