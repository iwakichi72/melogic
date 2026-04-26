import unittest

from melogic.analyzer import AnalysisError, amplitude_to_velocity, note_event_to_record
from melogic.models import note_number_to_name


class NoteConversionTests(unittest.TestCase):
    def test_note_number_to_name_uses_standard_midi_octaves(self):
        self.assertEqual(note_number_to_name(60), "C4")
        self.assertEqual(note_number_to_name(61), "C#4")
        self.assertEqual(note_number_to_name(69), "A4")

    def test_note_event_to_record_normalizes_basic_pitch_tuple(self):
        note = note_event_to_record((0.25, 1.0, 60, 0.8, [0, 1]))

        self.assertEqual(note.note_number, 60)
        self.assertEqual(note.note_name, "C4")
        self.assertEqual(note.start_time, 0.25)
        self.assertEqual(note.end_time, 1.0)
        self.assertEqual(note.duration, 0.75)
        self.assertEqual(note.velocity, 102)
        self.assertIsNone(note.confidence)

    def test_amplitude_to_velocity_is_clamped(self):
        self.assertEqual(amplitude_to_velocity(-0.5), 0)
        self.assertEqual(amplitude_to_velocity(0.0), 0)
        self.assertEqual(amplitude_to_velocity(1.5), 127)

    def test_invalid_note_event_raises_analysis_error(self):
        with self.assertRaises(AnalysisError):
            note_event_to_record((0.0, 1.0, 60))

    def test_reversed_note_timing_raises_analysis_error(self):
        with self.assertRaises(AnalysisError):
            note_event_to_record((1.0, 0.5, 60, 0.8))


if __name__ == "__main__":
    unittest.main()
