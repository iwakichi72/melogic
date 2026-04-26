import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import audio_to_midi
from melogic import AnalysisError, ExportPaths
from melogic.models import AnalysisResult, NoteRecord


class CliTests(unittest.TestCase):
    def make_result(self):
        return AnalysisResult(
            source_audio="samples/vocal.wav",
            generated_at="2026-04-26T12:00:00+00:00",
            notes=[
                NoteRecord(
                    note_number=60,
                    note_name="C4",
                    start_time=0.25,
                    end_time=1.0,
                    duration=0.75,
                    velocity=102,
                    confidence=None,
                )
            ],
            midi_data=object(),
        )

    def test_main_prints_exports_and_note_table_on_success(self):
        result = self.make_result()

        with tempfile.TemporaryDirectory() as temp_dir:
            paths = ExportPaths(
                midi=Path(temp_dir) / "vocal.mid",
                json=Path(temp_dir) / "vocal.json",
                csv=Path(temp_dir) / "vocal.csv",
            )
            stdout = io.StringIO()
            stderr = io.StringIO()

            with patch("audio_to_midi.analyze_audio", return_value=result) as analyze_mock:
                with patch("audio_to_midi.export_analysis", return_value=paths) as export_mock:
                    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                        exit_code = audio_to_midi.main(["samples/vocal.wav", temp_dir])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertIn("Notes: 1", stdout.getvalue())
        self.assertIn("C4", stdout.getvalue())
        analyze_mock.assert_called_once_with(Path("samples/vocal.wav"))
        export_mock.assert_called_once_with(result, Path(temp_dir), preview_wav=False)

    def test_main_can_request_preview_wav_export(self):
        result = self.make_result()

        with tempfile.TemporaryDirectory() as temp_dir:
            paths = ExportPaths(
                midi=Path(temp_dir) / "vocal.mid",
                json=Path(temp_dir) / "vocal.json",
                csv=Path(temp_dir) / "vocal.csv",
                preview_wav=Path(temp_dir) / "vocal_preview.wav",
            )
            stdout = io.StringIO()
            stderr = io.StringIO()

            with patch("audio_to_midi.analyze_audio", return_value=result):
                with patch("audio_to_midi.export_analysis", return_value=paths) as export_mock:
                    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                        exit_code = audio_to_midi.main(["samples/vocal.wav", temp_dir, "--preview-wav"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertIn("Preview WAV:", stdout.getvalue())
        export_mock.assert_called_once_with(result, Path(temp_dir), preview_wav=True)

    def test_main_returns_one_for_analysis_error(self):
        stdout = io.StringIO()
        stderr = io.StringIO()

        with patch("audio_to_midi.analyze_audio", side_effect=AnalysisError("boom")):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = audio_to_midi.main(["missing.wav", "out"])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("Error: boom", stderr.getvalue())

    def test_main_rejects_file_output_path_before_analysis(self):
        stdout = io.StringIO()
        stderr = io.StringIO()

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "not-a-directory"
            output_file.write_text("occupied", encoding="utf-8")

            with patch("audio_to_midi.analyze_audio") as analyze_mock:
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    exit_code = audio_to_midi.main(["samples/vocal.wav", str(output_file)])

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("Output path exists and is not a directory", stderr.getvalue())
        analyze_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
