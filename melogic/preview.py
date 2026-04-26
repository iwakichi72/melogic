from __future__ import annotations

import wave
from math import isfinite
from pathlib import Path
from struct import pack
from typing import Any


DEFAULT_PREVIEW_SAMPLE_RATE = 44_100


class PreviewError(RuntimeError):
    """Raised when MIDI preview audio cannot be generated."""


def write_preview_wav(
    midi_data: Any,
    output_path: str | Path,
    sample_rate: int = DEFAULT_PREVIEW_SAMPLE_RATE,
) -> None:
    if midi_data is None:
        raise PreviewError("MIDI data is required to generate a preview WAV.")
    if sample_rate <= 0:
        raise PreviewError(f"Preview sample rate must be positive: {sample_rate}")

    try:
        audio = midi_data.synthesize(fs=sample_rate)
    except Exception as exc:
        raise PreviewError(f"MIDI synthesis failed: {exc}") from exc

    pcm = audio_to_int16_pcm(audio, sample_rate)
    with Path(output_path).open("wb") as file:
        with wave.open(file, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm)


def audio_to_int16_pcm(audio: Any, sample_rate: int) -> bytes:
    samples = list(iter_mono_samples(audio))
    if not samples:
        samples = [0.0] * max(1, sample_rate // 10)

    peak = max(abs(sample) for sample in samples)
    normalization = peak if peak > 1.0 else 1.0

    pcm = bytearray()
    for sample in samples:
        normalized = sample / normalization
        clipped = max(-1.0, min(1.0, normalized))
        pcm.extend(pack("<h", round(clipped * 32767)))
    return bytes(pcm)


def iter_mono_samples(audio: Any):
    for sample in audio:
        yield to_mono_sample(sample)


def to_mono_sample(sample: Any) -> float:
    try:
        values = list(sample)
    except TypeError:
        return safe_float(sample)

    if not values:
        return 0.0
    return sum(safe_float(value) for value in values) / len(values)


def safe_float(value: Any) -> float:
    try:
        sample = float(value)
    except (TypeError, ValueError):
        return 0.0
    return sample if isfinite(sample) else 0.0
