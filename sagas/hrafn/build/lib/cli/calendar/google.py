from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow

from cli.config import ensure_runtime_dirs


SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
GOOGLE_OAUTH_SETUP_URL = "https://console.cloud.google.com/apis/credentials"


class GoogleCalendarError(RuntimeError):
    """Raised when Google Calendar credentials or API access fails."""


class GoogleCredentialsSetupError(GoogleCalendarError):
    """Raised when local Google OAuth client setup is incomplete or invalid."""


def _load_google_payload(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise GoogleCredentialsSetupError(
            f"Google credentials not found at {path}. Place your Google OAuth client JSON there, then run 'hrafn calendar connect google'."
        )

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GoogleCredentialsSetupError(
            f"Google credentials file at {path} is not valid JSON."
        ) from exc


def _extract_client_config(payload: dict[str, Any]) -> dict[str, Any]:
    if "installed" in payload or "web" in payload:
        return payload
    if "client_config" in payload and isinstance(payload["client_config"], dict):
        return payload["client_config"]
    raise GoogleCredentialsSetupError(
        "Google OAuth client configuration is missing. Save your Google client JSON to ~/.config/hrafn/google.json and run 'hrafn calendar connect google'."
    )


def _extract_authorized_user(payload: dict[str, Any]) -> dict[str, Any] | None:
    if {"token", "refresh_token", "client_id", "client_secret"}.issubset(payload):
        return payload
    authorized = payload.get("authorized_user")
    if isinstance(authorized, dict):
        return authorized
    return None


def _save_google_payload(
    path: Path,
    *,
    client_config: dict[str, Any],
    authorized_user: dict[str, Any],
) -> None:
    path.write_text(
        json.dumps(
            {
                "client_config": client_config,
                "authorized_user": authorized_user,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def connect_google_account() -> Path:
    paths = ensure_runtime_dirs()
    payload = _load_google_payload(paths.google_credentials_file)
    client_config = _extract_client_config(payload)

    try:
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        credentials = flow.run_local_server(port=0)
    except OSError as exc:
        raise GoogleCalendarError(f"Failed to launch local OAuth callback server: {exc}") from exc
    except Exception as exc:  # pragma: no cover - third-party library behavior
        raise GoogleCalendarError(f"Google OAuth flow failed: {exc}") from exc

    _save_google_payload(
        paths.google_credentials_file,
        client_config=client_config,
        authorized_user=json.loads(credentials.to_json()),
    )
    return paths.google_credentials_file


def validate_google_client_config(path: Path) -> dict[str, Any]:
    payload = _load_google_payload(path)
    _extract_client_config(payload)
    return payload


def install_google_client_config(source: Path, destination: Path) -> Path:
    try:
        source = source.expanduser().resolve(strict=True)
    except FileNotFoundError as exc:
        raise GoogleCredentialsSetupError(f"Google credentials file not found at {source}.") from exc

    if not source.is_file():
        raise GoogleCredentialsSetupError(f"Google credentials path is not a file: {source}")

    validate_google_client_config(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return destination


def load_credentials() -> Credentials:
    paths = ensure_runtime_dirs()
    payload = _load_google_payload(paths.google_credentials_file)
    authorized_user = _extract_authorized_user(payload)
    client_config = _extract_client_config(payload)

    if authorized_user is None:
        raise GoogleCalendarError(
            "Google account is not connected. Run 'hrafn calendar connect google' first."
        )

    credentials = Credentials.from_authorized_user_info(authorized_user, SCOPES)

    if credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(Request())
        except RefreshError as exc:
            raise GoogleCalendarError(
                "Google token refresh failed. Reconnect with 'hrafn calendar connect google'."
            ) from exc
        _save_google_payload(
            paths.google_credentials_file,
            client_config=client_config,
            authorized_user=json.loads(credentials.to_json()),
        )
    elif not credentials.valid:
        raise GoogleCalendarError(
            "Google credentials are invalid. Reconnect with 'hrafn calendar connect google'."
        )

    return credentials


def build_calendar_service():
    credentials = load_credentials()
    try:
        return build("calendar", "v3", credentials=credentials, cache_discovery=False)
    except HttpError as exc:
        raise GoogleCalendarError(f"Google Calendar API request failed: {exc}") from exc
    except Exception as exc:  # pragma: no cover - third-party library behavior
        raise GoogleCalendarError(f"Failed to initialize Google Calendar client: {exc}") from exc
