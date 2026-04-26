import tempfile
import unittest
import wave
from pathlib import Path

from melogic.preview import PreviewError, audio_to_int16_pcm, write_preview_wav


class FakeMidi:
    def __init__(self, audio):
        self.audio = audio
        self.sample_rate = None

    def synthesize(self, fs):
        self.sample_rate = fs
        return self.audio


class PreviewTests(unittest.TestCase):
    def test_audio_to_int16_pcm_clips_and_converts_samples(self):
        pcm = audio_to_int16_pcm([-2.0, 0.0, 2.0], sample_rate=44100)

        self.assertEqual(len(pcm), 6)

    def test_write_preview_wav_writes_mono_file(self):
        midi = FakeMidi([0.0, 0.5, -0.5, 0.0])

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "preview.wav"
            write_preview_wav(midi, output_path, sample_rate=22050)

            with wave.open(str(output_path), "rb") as wav_file:
                self.assertEqual(wav_file.getnchannels(), 1)
                self.assertEqual(wav_file.getsampwidth(), 2)
                self.assertEqual(wav_file.getframerate(), 22050)
                self.assertEqual(wav_file.getnframes(), 4)

        self.assertEqual(midi.sample_rate, 22050)

    def test_write_preview_wav_requires_midi_data(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(PreviewError):
                write_preview_wav(None, Path(temp_dir) / "preview.wav")


if __name__ == "__main__":
    unittest.main()
