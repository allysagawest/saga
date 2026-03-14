from __future__ import annotations

import unittest
from unittest.mock import patch

from cli.service import _parse_systemd_duration, _read_timer_schedule


class SyncServiceTests(unittest.TestCase):
    def test_parse_systemd_duration_handles_compound_values(self) -> None:
        self.assertEqual(_parse_systemd_duration("1 day 2h 3min 4s"), 93784)
        self.assertEqual(_parse_systemd_duration("5min 30s"), 330)
        self.assertEqual(_parse_systemd_duration("-"), None)

    @patch("cli.service.subprocess.run")
    def test_read_timer_schedule_parses_systemctl_status_output(self, run_mock) -> None:
        run_mock.return_value.returncode = 0
        run_mock.return_value.stdout = (
            "● hrafn-sync.timer - Run Hrafn calendar sync on a schedule\n"
            "     Loaded: loaded (/home/ally_west/.config/systemd/user/hrafn-sync.timer; enabled; preset: disabled)\n"
            "     Active: active (waiting) since Fri 2026-03-13 21:39:12 EDT; 2min 58s ago\n"
            "    Trigger: Fri 2026-03-13 21:44:12 EDT; 4min 32s left\n"
        )

        next_sync_time, next_sync_in_seconds = _read_timer_schedule()

        self.assertEqual(next_sync_time, "Fri 2026-03-13 21:44:12 EDT")
        self.assertEqual(next_sync_in_seconds, 272)


if __name__ == "__main__":
    unittest.main()
