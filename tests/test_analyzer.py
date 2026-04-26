import tempfile
import unittest
from pathlib import Path

from melogic.analyzer import AnalysisError, validate_input_audio


class AnalyzerInputTests(unittest.TestCase):
    def test_validate_input_audio_accepts_supported_extension_case_insensitively(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "take.WAV"
            audio_path.write_bytes(b"")

            self.assertEqual(validate_input_audio(audio_path), audio_path)

    def test_validate_input_audio_rejects_missing_file(self):
        with self.assertRaises(AnalysisError):
            validate_input_audio("missing.wav")

    def test_validate_input_audio_rejects_unsupported_extension(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "notes.txt"
            input_path.write_text("not audio", encoding="utf-8")

            with self.assertRaises(AnalysisError):
                validate_input_audio(input_path)

    def test_validate_input_audio_rejects_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(AnalysisError):
                validate_input_audio(temp_dir)


if __name__ == "__main__":
    unittest.main()
