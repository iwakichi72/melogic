import csv
import json
import tempfile
import unittest
from pathlib import Path

from melogic.exporters import ExportError, export_analysis, write_csv, write_json, write_midi
from melogic.models import AnalysisResult, NoteRecord


class FakeMidi:
    def __init__(self):
        self.write_path = None
        self.synthesize_sample_rate = None

    def write(self, path):
        self.write_path = path
        Path(path).write_bytes(b"MThd")

    def synthesize(self, fs):
        self.synthesize_sample_rate = fs
        return [0.0, 0.25, -0.25, 0.0]


class ExporterTests(unittest.TestCase):
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
            midi_data=FakeMidi(),
        )

    def test_write_json_exports_expected_shape(self):
        result = self.make_result()

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "notes.json"
            write_json(result, output_path)

            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["source_audio"], "samples/vocal.wav")
        self.assertEqual(payload["note_count"], 1)
        self.assertEqual(payload["notes"][0]["note_name"], "C4")
        self.assertIsNone(payload["notes"][0]["confidence"])

    def test_write_csv_exports_same_note_fields(self):
        result = self.make_result()

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "notes.csv"
            write_csv(result, output_path)

            with output_path.open("r", encoding="utf-8", newline="") as file:
                rows = list(csv.DictReader(file))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["note_number"], "60")
        self.assertEqual(rows[0]["note_name"], "C4")
        self.assertEqual(rows[0]["confidence"], "")

    def test_export_analysis_writes_mid_json_and_csv(self):
        result = self.make_result()

        with tempfile.TemporaryDirectory() as temp_dir:
            paths = export_analysis(result, temp_dir)

            self.assertEqual(paths.midi.name, "vocal.mid")
            self.assertEqual(paths.json.name, "vocal.json")
            self.assertEqual(paths.csv.name, "vocal.csv")
            self.assertTrue(paths.midi.exists())
            self.assertTrue(paths.json.exists())
            self.assertTrue(paths.csv.exists())
            self.assertIsNone(paths.preview_wav)
            self.assertEqual(result.midi_data.write_path, str(paths.midi))

    def test_export_analysis_optionally_writes_preview_wav(self):
        result = self.make_result()

        with tempfile.TemporaryDirectory() as temp_dir:
            paths = export_analysis(result, temp_dir, preview_wav=True)

            self.assertEqual(paths.preview_wav.name, "vocal_preview.wav")
            self.assertTrue(paths.preview_wav.exists())
            self.assertEqual(result.midi_data.synthesize_sample_rate, 44100)

    def test_write_midi_requires_midi_data(self):
        result = AnalysisResult(
            source_audio="samples/vocal.wav",
            generated_at="2026-04-26T12:00:00+00:00",
            notes=[],
            midi_data=None,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ExportError):
                write_midi(result, Path(temp_dir) / "vocal.mid")


if __name__ == "__main__":
    unittest.main()
