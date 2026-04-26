import unittest

from streamlit_app import audio_data_url, build_left_flow_note_view, midi_note_name


class StreamlitVisualizationTests(unittest.TestCase):
    def test_build_left_flow_note_view_contains_keyboard_and_notes(self):
        html, height = build_left_flow_note_view(
            [
                {
                    "index": 1,
                    "note_number": 60,
                    "note_name": "C4",
                    "note_label": "C4 / 60",
                    "start_time": 0.0,
                    "end_time": 0.5,
                    "duration": 0.5,
                    "velocity": 90,
                    "confidence": None,
                }
            ],
            preview_audio=b"RIFF",
        )

        self.assertGreaterEqual(height, 260)
        self.assertIn("同期ノーツビュー", html)
        self.assertIn("data:audio/wav;base64,UklGRg==", html)
        self.assertIn("melogic-key", html)
        self.assertNotIn("melogic-horizontal-piano", html)
        self.assertIn("melogic-note", html)
        self.assertIn("audio.currentTime", html)
        self.assertNotIn("@keyframes melogic-flow-left", html)
        self.assertIn("C4", html)

    def test_audio_data_url_returns_none_for_missing_audio(self):
        self.assertIsNone(audio_data_url(None))
        self.assertIsNone(audio_data_url(b""))

    def test_audio_data_url_encodes_wav_bytes(self):
        self.assertEqual(audio_data_url(b"RIFF"), "data:audio/wav;base64,UklGRg==")

    def test_midi_note_name_matches_standard_octaves(self):
        self.assertEqual(midi_note_name(60), "C4")
        self.assertEqual(midi_note_name(61), "C#4")
        self.assertEqual(midi_note_name(69), "A4")


if __name__ == "__main__":
    unittest.main()
