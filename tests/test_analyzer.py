import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from melogic.analyzer import (
    AnalysisError,
    DEFAULT_BALANCED,
    KEYS_GUITAR,
    PitchDetectionParams,
    VOCAL_SUSTAIN,
    analyze_audio,
    preferred_basic_pitch_model_path,
    validate_input_audio,
)


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


class _FakePredict:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def __call__(self, audio_path, **kwargs):
        self.calls.append({"audio_path": audio_path, **kwargs})
        # Basic Pitch returns: model_output dict, midi_data, note_events list.
        return {}, _FakeMidi(), []


class _FakeMidi:
    def write(self, path):  # pragma: no cover - exporters not under test here
        Path(path).write_bytes(b"")

    def synthesize(self, *args, **kwargs):  # pragma: no cover
        return []


def _install_fake_basic_pitch(fake_predict):
    """Install a fake basic_pitch.inference.predict module into sys.modules."""

    fake_inference = types.ModuleType("basic_pitch.inference")
    fake_inference.predict = fake_predict
    fake_pkg = types.ModuleType("basic_pitch")
    fake_pkg.inference = fake_inference
    return patch.dict(
        sys.modules,
        {"basic_pitch": fake_pkg, "basic_pitch.inference": fake_inference},
    )


class AnalyzeAudioParamsTests(unittest.TestCase):
    def _make_audio_file(self, temp_dir: str) -> Path:
        path = Path(temp_dir) / "song.wav"
        path.write_bytes(b"")
        return path

    def test_default_params_match_basic_pitch_defaults(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = self._make_audio_file(temp_dir)
            fake = _FakePredict()
            with _install_fake_basic_pitch(fake), patch(
                "melogic.analyzer.preferred_basic_pitch_model_path",
                return_value=None,
            ):
                analyze_audio(audio_path)

        self.assertEqual(len(fake.calls), 1)
        call = fake.calls[0]
        self.assertEqual(call["onset_threshold"], 0.5)
        self.assertEqual(call["frame_threshold"], 0.3)
        self.assertAlmostEqual(call["minimum_note_length"], 127.70)
        self.assertIsNone(call["minimum_frequency"])
        self.assertIsNone(call["maximum_frequency"])

    def test_vocal_sustain_preset_is_passed_to_predict(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = self._make_audio_file(temp_dir)
            fake = _FakePredict()
            with _install_fake_basic_pitch(fake), patch(
                "melogic.analyzer.preferred_basic_pitch_model_path",
                return_value=None,
            ):
                analyze_audio(audio_path, params=VOCAL_SUSTAIN)

        call = fake.calls[0]
        self.assertEqual(call["frame_threshold"], VOCAL_SUSTAIN.frame_threshold)
        self.assertEqual(call["onset_threshold"], VOCAL_SUSTAIN.onset_threshold)
        self.assertEqual(call["minimum_note_length"], VOCAL_SUSTAIN.minimum_note_length)
        self.assertEqual(call["minimum_frequency"], VOCAL_SUSTAIN.minimum_frequency)
        self.assertEqual(call["maximum_frequency"], VOCAL_SUSTAIN.maximum_frequency)

    def test_custom_params_pass_through(self):
        custom = PitchDetectionParams(
            onset_threshold=0.42,
            frame_threshold=0.11,
            minimum_note_length=210.0,
            minimum_frequency=120.0,
            maximum_frequency=900.0,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = self._make_audio_file(temp_dir)
            fake = _FakePredict()
            with _install_fake_basic_pitch(fake), patch(
                "melogic.analyzer.preferred_basic_pitch_model_path",
                return_value=None,
            ):
                analyze_audio(audio_path, params=custom)

        call = fake.calls[0]
        self.assertEqual(call["frame_threshold"], 0.11)
        self.assertEqual(call["onset_threshold"], 0.42)
        self.assertEqual(call["minimum_note_length"], 210.0)
        self.assertEqual(call["minimum_frequency"], 120.0)
        self.assertEqual(call["maximum_frequency"], 900.0)

    def test_params_passed_alongside_model_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = self._make_audio_file(temp_dir)
            model_path = Path(temp_dir) / "fake_model.onnx"
            model_path.write_bytes(b"x")
            fake = _FakePredict()
            with _install_fake_basic_pitch(fake), patch(
                "melogic.analyzer.preferred_basic_pitch_model_path",
                return_value=model_path,
            ):
                analyze_audio(audio_path, params=KEYS_GUITAR)

        call = fake.calls[0]
        self.assertEqual(call["model_or_model_path"], model_path)
        self.assertEqual(call["minimum_note_length"], KEYS_GUITAR.minimum_note_length)


class PitchDetectionParamsTests(unittest.TestCase):
    def test_default_balanced_matches_basic_pitch_defaults(self):
        self.assertEqual(DEFAULT_BALANCED.onset_threshold, 0.5)
        self.assertEqual(DEFAULT_BALANCED.frame_threshold, 0.3)
        self.assertAlmostEqual(DEFAULT_BALANCED.minimum_note_length, 127.70)
        self.assertIsNone(DEFAULT_BALANCED.minimum_frequency)
        self.assertIsNone(DEFAULT_BALANCED.maximum_frequency)

    def test_vocal_sustain_lowers_frame_threshold(self):
        self.assertLess(VOCAL_SUSTAIN.frame_threshold, DEFAULT_BALANCED.frame_threshold)
        self.assertGreater(VOCAL_SUSTAIN.minimum_note_length, DEFAULT_BALANCED.minimum_note_length)

    def test_params_is_frozen(self):
        with self.assertRaises(Exception):
            DEFAULT_BALANCED.frame_threshold = 0.99  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
