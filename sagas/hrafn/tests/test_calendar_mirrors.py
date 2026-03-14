from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cli.calendar.stack import CalendarConnection, _render_mirror_ics


DETAIL_SOURCE = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:source-uid
DTSTART:20260314T130000Z
DTEND:20260314T140000Z
SUMMARY:Pipeline Review
DESCRIPTION:Discuss revenue and clients
LOCATION:HQ
ATTENDEE:mailto:test@example.com
ORGANIZER:mailto:owner@example.com
END:VEVENT
END:VCALENDAR
"""

BUSY_SOURCE = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:main-uid
DTSTART:20260314T150000Z
DTEND:20260314T160000Z
SUMMARY:Private Planning
DESCRIPTION:Sensitive notes
LOCATION:Office
END:VEVENT
END:VCALENDAR
"""


class CalendarMirrorTests(unittest.TestCase):
    def test_secondary_detail_mirror_preserves_details_and_labels_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_file = Path(tmp) / "source.ics"
            source_file.write_text(DETAIL_SOURCE, encoding="utf-8")

            rendered = _render_mirror_ics(
                source_file=source_file,
                target_kind="detail",
                source_connection=CalendarConnection(
                    kind="google",
                    name="Bryce",
                    slug="bryce",
                    path=tmp,
                    role="secondary",
                ),
            )

        self.assertIn("SUMMARY:[Bryce] Pipeline Review", rendered)
        self.assertIn("DESCRIPTION:Discuss revenue and clients", rendered)
        self.assertIn("LOCATION:HQ", rendered)
        self.assertNotIn("ATTENDEE:", rendered)
        self.assertNotIn("ORGANIZER:", rendered)
        self.assertIn("X-HRAFN-MIRROR-KIND:detail", rendered)

    def test_main_busy_mirror_strips_sensitive_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_file = Path(tmp) / "main.ics"
            source_file.write_text(BUSY_SOURCE, encoding="utf-8")

            rendered = _render_mirror_ics(
                source_file=source_file,
                target_kind="busy",
                source_connection=CalendarConnection(
                    kind="google",
                    name="Main",
                    slug="main",
                    path=tmp,
                    role="main",
                ),
            )

        self.assertIn("SUMMARY:Busy", rendered)
        self.assertIn("CLASS:PRIVATE", rendered)
        self.assertIn("TRANSP:OPAQUE", rendered)
        self.assertNotIn("DESCRIPTION:S", rendered)
        self.assertNotIn("LOCATION:Office", rendered)
        self.assertIn("X-HRAFN-MIRROR-KIND:busy", rendered)


if __name__ == "__main__":
    unittest.main()
