from __future__ import annotations

import unittest

from cli.calendar.stack import (
    CalendarConnection,
    _build_vdirsyncer_google_oauth_error,
    _render_khal_config,
    _normalize_role,
    _render_vdirsyncer_config,
    finalize_caldav_connection,
    finalize_google_connection,
)


class VdirsyncerConfigTests(unittest.TestCase):
    def test_secondary_connection_discovers_from_remote_when_unpinned(self) -> None:
        config = _render_vdirsyncer_config(
            [
                CalendarConnection(
                    kind="google",
                    name="Bryce",
                    slug="bryce",
                    path="/tmp/bryce",
                    role="secondary",
                    client_id="client-id",
                    client_secret="client-secret",
                    token_file="/tmp/token.json",
                )
            ]
        )

        self.assertIn('collections = ["from a"]', config)
        self.assertNotIn("read_only = true", config)
        self.assertNotIn('partial_sync = "ignore"', config)

    def test_selected_collections_render_exactly_in_vdirsyncer_config(self) -> None:
        config = _render_vdirsyncer_config(
            [
                CalendarConnection(
                    kind="google",
                    name="Personal",
                    slug="google_personal",
                    path="/tmp/google_personal",
                    role="secondary",
                    selected_collections=[
                        "alex.carson.440@gmail.com",
                        "family10799977565623715725@group.calendar.google.com",
                    ],
                    client_id="client-id",
                    client_secret="client-secret",
                    token_file="/tmp/token.json",
                )
            ]
        )

        self.assertIn(
            'collections = ["alex.carson.440@gmail.com", "family10799977565623715725@group.calendar.google.com"]',
            config,
        )

    def test_selected_collections_render_as_multiple_khal_calendars(self) -> None:
        config = _render_khal_config(
            [
                CalendarConnection(
                    kind="google",
                    name="Personal",
                    slug="google_personal",
                    path="/tmp/google_personal",
                    role="secondary",
                    selected_collections=[
                        "alex.carson.440@gmail.com",
                        "family10799977565623715725@group.calendar.google.com",
                    ],
                    client_id="client-id",
                    client_secret="client-secret",
                    token_file="/tmp/token.json",
                )
            ]
        )

        self.assertIn("[[google_personal]]", config)
        self.assertIn("path = /tmp/google_personal/alex.carson.440@gmail.com", config)
        self.assertIn("[[google_personal__2]]", config)
        self.assertIn(
            "path = /tmp/google_personal/family10799977565623715725@group.calendar.google.com",
            config,
        )

    def test_legacy_roles_normalize_to_supported_values(self) -> None:
        self.assertEqual(_normalize_role("source"), "secondary")
        self.assertEqual(_normalize_role("busy_target"), "secondary")
        self.assertEqual(_normalize_role("master"), "main")

    def test_google_oauth_error_includes_install_guidance(self) -> None:
        from unittest.mock import patch

        with patch("cli.calendar.stack._detect_linux_distro", return_value="fedora"):
            message = _build_vdirsyncer_google_oauth_error("critical: aiohttp-oauthlib not installed")

        self.assertIn("aiohttp OAuth dependency", message)
        self.assertIn("sudo dnf install python3-aiohttp-oauthlib", message)

    def test_finalize_google_connection_discovers_without_syncing(self) -> None:
        from unittest.mock import patch

        connection = CalendarConnection(
            kind="google",
            name="Bryce",
            slug="bryce",
            path="/tmp/bryce",
            role="secondary",
            client_id="client-id",
            client_secret="client-secret",
            token_file="/tmp/token.json",
        )

        with (
            patch("cli.calendar.stack.ensure_binary"),
            patch("cli.calendar.stack.ensure_vdirsyncer_ready"),
            patch("cli.calendar.stack._run_command") as run_command,
        ):
            message = finalize_google_connection(connection)

        self.assertEqual(message, "Google calendars discovered.")
        run_command.assert_called_once_with(["vdirsyncer", "discover", "bryce"], capture_output=False)

    def test_finalize_caldav_connection_discovers_without_syncing(self) -> None:
        from unittest.mock import patch

        connection = CalendarConnection(
            kind="caldav",
            name="Work",
            slug="work",
            path="/tmp/work",
            role="secondary",
            url="https://example.com/caldav",
            username="ally",
            password="secret",
        )

        with (
            patch("cli.calendar.stack.ensure_binary"),
            patch("cli.calendar.stack.ensure_vdirsyncer_ready"),
            patch("cli.calendar.stack._run_command") as run_command,
        ):
            message = finalize_caldav_connection(connection)

        self.assertEqual(message, "CalDAV calendars discovered.")
        run_command.assert_called_once_with(["vdirsyncer", "discover", "work"], capture_output=False)


if __name__ == "__main__":
    unittest.main()
