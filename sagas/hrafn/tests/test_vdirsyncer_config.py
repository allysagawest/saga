from __future__ import annotations

import unittest

from cli.calendar.stack import CalendarConnection, _normalize_role, _render_vdirsyncer_config


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

    def test_legacy_roles_normalize_to_supported_values(self) -> None:
        self.assertEqual(_normalize_role("source"), "secondary")
        self.assertEqual(_normalize_role("busy_target"), "secondary")
        self.assertEqual(_normalize_role("master"), "main")


if __name__ == "__main__":
    unittest.main()
