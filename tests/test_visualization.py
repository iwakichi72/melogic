import unittest

from melogic.models import NoteRecord
from melogic.visualization import build_piano_roll_rows


class VisualizationTests(unittest.TestCase):
    def test_build_piano_roll_rows_accepts_note_records(self):
        rows = build_piano_roll_rows(
            [
                NoteRecord(
                    note_number=64,
                    note_name="E4",
                    start_time=1.0,
                    end_time=1.5,
                    duration=0.5,
                    velocity=80,
                    confidence=None,
                )
            ]
        )

        self.assertEqual(rows[0]["note_label"], "E4 / 64")
        self.assertEqual(rows[0]["start_time"], 1.0)
        self.assertEqual(rows[0]["end_time"], 1.5)
        self.assertEqual(rows[0]["velocity"], 80)

    def test_build_piano_roll_rows_sorts_by_time_then_note(self):
        rows = build_piano_roll_rows(
            [
                {
                    "note_number": 72,
                    "note_name": "C5",
                    "start_time": 1.0,
                    "end_time": 1.5,
                    "duration": 0.5,
                    "velocity": 90,
                    "confidence": None,
                },
                {
                    "note_number": 60,
                    "note_name": "C4",
                    "start_time": 0.5,
                    "end_time": 1.0,
                    "duration": 0.5,
                    "velocity": 100,
                    "confidence": None,
                },
            ]
        )

        self.assertEqual([row["note_name"] for row in rows], ["C4", "C5"])


if __name__ == "__main__":
    unittest.main()
