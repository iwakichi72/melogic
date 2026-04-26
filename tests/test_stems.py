import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from melogic.analyzer import AnalysisError
from melogic.stems import (
    AnalysisMode,
    analysis_mode_label,
    output_stem_for_mode,
    parse_major_minor,
    prepare_analysis_input,
    torchaudio_needs_torchcodec,
)


class StemPreparationTests(unittest.TestCase):
    def test_standard_mode_uses_original_audio(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "band.wav"
            audio_path.write_bytes(b"RIFF")

            prepared = prepare_analysis_input(audio_path, AnalysisMode.STANDARD, temp_dir)

        self.assertEqual(prepared.path, audio_path)
        self.assertEqual(prepared.source_path, audio_path)
        self.assertFalse(prepared.used_demucs)
        self.assertEqual(prepared.label, "標準（そのまま解析）")

    def test_missing_demucs_has_actionable_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "band.wav"
            audio_path.write_bytes(b"RIFF")

            with patch("melogic.stems.find_spec", return_value=None):
                with self.assertRaises(AnalysisError) as raised:
                    prepare_analysis_input(audio_path, AnalysisMode.VOCAL, temp_dir)

        self.assertIn("requirements-band.txt", str(raised.exception))

    def test_missing_torchcodec_has_actionable_error_before_running_demucs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "band.wav"
            audio_path.write_bytes(b"RIFF")

            def fake_find_spec(name):
                if name == "torchcodec":
                    return None
                return object()

            with patch("melogic.stems.find_spec", side_effect=fake_find_spec):
                with patch("melogic.stems.version", side_effect=lambda name: "2.11.0"):
                    with patch("melogic.stems.subprocess.run") as run_mock:
                        with self.assertRaises(AnalysisError) as raised:
                            prepare_analysis_input(audio_path, AnalysisMode.VOCAL, temp_dir)

        self.assertIn("torchcodec", str(raised.exception))
        self.assertIn("requirements-band.txt", str(raised.exception))
        run_mock.assert_not_called()

    def test_vocal_mode_runs_demucs_and_returns_vocal_stem(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "band.wav"
            audio_path.write_bytes(b"RIFF")

            def fake_run(command, check, capture_output, text):
                self.assertTrue(check)
                self.assertTrue(capture_output)
                self.assertTrue(text)
                stems_root = Path(command[command.index("-o") + 1])
                stem_dir = stems_root / "htdemucs" / "band"
                stem_dir.mkdir(parents=True)
                (stem_dir / "vocals.wav").write_bytes(b"RIFF")
                (stem_dir / "no_vocals.wav").write_bytes(b"RIFF")
                return subprocess.CompletedProcess(command, 0, "", "")

            with patch("melogic.stems.find_spec", return_value=object()):
                with patch("melogic.stems.subprocess.run", side_effect=fake_run) as run_mock:
                    prepared = prepare_analysis_input(audio_path, AnalysisMode.VOCAL, temp_dir)

        self.assertEqual(prepared.path.name, "vocals.wav")
        self.assertEqual(prepared.source_path, audio_path)
        self.assertTrue(prepared.used_demucs)
        run_mock.assert_called_once()

    def test_accompaniment_mode_returns_no_vocals_stem(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "band.wav"
            audio_path.write_bytes(b"RIFF")

            def fake_run(command, check, capture_output, text):
                stem_dir = Path(command[command.index("-o") + 1]) / "htdemucs" / "band"
                stem_dir.mkdir(parents=True)
                (stem_dir / "no_vocals.wav").write_bytes(b"RIFF")
                return subprocess.CompletedProcess(command, 0, "", "")

            with patch("melogic.stems.find_spec", return_value=object()):
                with patch("melogic.stems.subprocess.run", side_effect=fake_run):
                    prepared = prepare_analysis_input(audio_path, "accompaniment", temp_dir)

        self.assertEqual(prepared.path.name, "no_vocals.wav")
        self.assertEqual(prepared.label, analysis_mode_label("accompaniment"))

    def test_output_stem_for_mode_adds_readable_suffix(self):
        self.assertEqual(output_stem_for_mode("song mix.wav", AnalysisMode.STANDARD), "song_mix")
        self.assertEqual(output_stem_for_mode("song mix.wav", AnalysisMode.VOCAL), "song_mix_vocals")
        self.assertEqual(
            output_stem_for_mode("song mix.wav", AnalysisMode.ACCOMPANIMENT),
            "song_mix_no_vocals",
        )

    def test_torchaudio_version_detection_for_torchcodec(self):
        self.assertEqual(parse_major_minor("2.11.0"), (2, 11))
        self.assertFalse(torchaudio_needs_torchcodec("2.8.2"))
        self.assertTrue(torchaudio_needs_torchcodec("2.9.0"))
        self.assertTrue(torchaudio_needs_torchcodec("2.11.0"))


if __name__ == "__main__":
    unittest.main()
