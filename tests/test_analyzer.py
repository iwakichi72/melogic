import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from melogic.analyzer import AnalysisError, preferred_basic_pitch_model_path, validate_input_audio


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

    def test_preferred_basic_pitch_model_path_uses_onnx_when_available(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "nmp.mlpackage"
            onnx_path = Path(temp_dir) / "nmp.onnx"
            onnx_path.write_bytes(b"onnx")

            fake_basic_pitch = type("BasicPitch", (), {"ICASSP_2022_MODEL_PATH": model_path})
            with patch("melogic.analyzer.find_spec", return_value=object()):
                with patch("melogic.analyzer.enable_basic_pitch_onnx_runtime") as enable_mock:
                    with patch.dict("sys.modules", {"basic_pitch": fake_basic_pitch}):
                        self.assertEqual(preferred_basic_pitch_model_path(), onnx_path)

        enable_mock.assert_called_once()

    def test_preferred_basic_pitch_model_path_returns_none_without_onnxruntime(self):
        with patch("melogic.analyzer.find_spec", return_value=None):
            self.assertIsNone(preferred_basic_pitch_model_path())


if __name__ == "__main__":
    unittest.main()
