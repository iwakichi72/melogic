import tempfile
import unittest
from pathlib import Path

from melogic.analyzer import AnalysisError
from melogic.gui_io import sanitize_audio_filename, save_audio_bytes, unique_path


class GuiIoTests(unittest.TestCase):
    def test_sanitize_audio_filename_keeps_safe_suffix(self):
        self.assertEqual(sanitize_audio_filename("My Take 01.WAV", "recording.wav"), "My_Take_01.wav")

    def test_sanitize_audio_filename_uses_default_for_blank_name(self):
        self.assertEqual(sanitize_audio_filename("", "recording.wav"), "recording.wav")

    def test_save_audio_bytes_writes_supported_audio_into_inputs_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            saved = save_audio_bytes(b"RIFF", "take.wav", temp_dir)

            self.assertEqual(saved.display_name, "take.wav")
            self.assertEqual(saved.path.parent, Path(temp_dir) / "_inputs")
            self.assertEqual(saved.path.read_bytes(), b"RIFF")

    def test_save_audio_bytes_rejects_unsupported_extension(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(AnalysisError):
                save_audio_bytes(b"nope", "take.txt", temp_dir)

    def test_unique_path_adds_suffix_when_path_exists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "take.wav"
            path.write_bytes(b"")

            unique = unique_path(path)

            self.assertNotEqual(unique, path)
            self.assertTrue(unique.name.startswith("take_"))
            self.assertEqual(unique.suffix, ".wav")


if __name__ == "__main__":
    unittest.main()
