from __future__ import annotations

import importlib
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.util import find_spec
from pathlib import Path
from typing import Any, Sequence

from .models import AnalysisResult, NoteRecord, note_number_to_name


SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".aiff", ".aif"}


@dataclass(frozen=True)
class PitchDetectionParams:
    """Tunable Basic Pitch parameters surfaced to callers."""

    onset_threshold: float = 0.5
    frame_threshold: float = 0.3
    minimum_note_length: float = 127.70  # milliseconds
    minimum_frequency: float | None = None
    maximum_frequency: float | None = None


DEFAULT_BALANCED = PitchDetectionParams()
"""Basic Pitch defaults — keep existing behavior for general/instrumental sources."""

VOCAL_SUSTAIN = PitchDetectionParams(
    onset_threshold=0.6,
    frame_threshold=0.18,
    minimum_note_length=180.0,
    minimum_frequency=80.0,
    maximum_frequency=1100.0,
)
"""Vocal preset: keep sustained tails alive and reject sub-180ms fragments."""

KEYS_GUITAR = PitchDetectionParams(
    onset_threshold=0.5,
    frame_threshold=0.3,
    minimum_note_length=80.0,
)
"""Decay-instrument preset: pick up fast passages without merging too aggressively."""


class AnalysisError(RuntimeError):
    """Raised when audio analysis cannot be completed."""


def validate_input_audio(input_audio: str | Path) -> Path:
    path = Path(input_audio).expanduser()
    if not path.exists():
        raise AnalysisError(f"Input audio file does not exist: {path}")
    if not path.is_file():
        raise AnalysisError(f"Input audio path is not a file: {path}")
    if path.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_AUDIO_EXTENSIONS))
        raise AnalysisError(f"Unsupported audio extension '{path.suffix}'. Supported: {supported}")
    return path


def note_event_to_record(note_event: Sequence[Any]) -> NoteRecord:
    """Normalize a Basic Pitch note event into the app's stable note shape."""
    if len(note_event) < 4:
        raise AnalysisError(f"Invalid Basic Pitch note event: {note_event!r}")

    start_time = float(note_event[0])
    end_time = float(note_event[1])
    note_number = int(note_event[2])
    amplitude = float(note_event[3])
    if end_time < start_time:
        raise AnalysisError(f"Invalid Basic Pitch note event timing: {note_event!r}")

    return NoteRecord(
        note_number=note_number,
        note_name=note_number_to_name(note_number),
        start_time=start_time,
        end_time=end_time,
        duration=end_time - start_time,
        velocity=amplitude_to_velocity(amplitude),
        confidence=None,
    )


def amplitude_to_velocity(amplitude: float) -> int:
    velocity = round(amplitude * 127)
    return max(0, min(127, velocity))


def analyze_audio(
    input_audio: str | Path,
    params: PitchDetectionParams = DEFAULT_BALANCED,
) -> AnalysisResult:
    input_path = validate_input_audio(input_audio)

    try:
        from basic_pitch.inference import predict
    except ImportError as exc:
        raise AnalysisError(
            "Basic Pitch or one of its dependencies could not be imported. "
            f"Details: {exc}. "
            "Use the project virtual environment and run: .venv/bin/python -m pip install -r requirements.txt"
        ) from exc

    predict_kwargs: dict[str, Any] = {
        "onset_threshold": params.onset_threshold,
        "frame_threshold": params.frame_threshold,
        "minimum_note_length": params.minimum_note_length,
        "minimum_frequency": params.minimum_frequency,
        "maximum_frequency": params.maximum_frequency,
    }

    try:
        model_path = preferred_basic_pitch_model_path()
        if model_path is not None:
            _model_output, midi_data, note_events = predict(
                str(input_path), model_or_model_path=model_path, **predict_kwargs
            )
        else:
            _model_output, midi_data, note_events = predict(str(input_path), **predict_kwargs)
    except Exception as exc:  # Basic Pitch can raise runtime-specific backend errors.
        raise AnalysisError(f"Basic Pitch analysis failed for {input_path}: {exc}") from exc

    notes = [note_event_to_record(note_event) for note_event in note_events]
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    return AnalysisResult(
        source_audio=str(input_path),
        generated_at=generated_at,
        notes=notes,
        midi_data=midi_data,
    )


def preferred_basic_pitch_model_path() -> Path | None:
    """Use ONNX when available to avoid fragile CoreML compilation in local apps."""
    if find_spec("onnxruntime") is None:
        return None

    try:
        from basic_pitch import ICASSP_2022_MODEL_PATH
    except ImportError:
        return None

    onnx_path = Path(ICASSP_2022_MODEL_PATH).with_suffix(".onnx")
    if onnx_path.exists():
        enable_basic_pitch_onnx_runtime()
        return onnx_path
    return None


def enable_basic_pitch_onnx_runtime() -> None:
    """Refresh Basic Pitch ONNX globals if onnxruntime was installed after import."""
    try:
        onnxruntime = importlib.import_module("onnxruntime")
        basic_pitch = importlib.import_module("basic_pitch")
        basic_pitch_inference = importlib.import_module("basic_pitch.inference")
    except ImportError:
        return

    setattr(basic_pitch, "ONNX_PRESENT", True)
    setattr(basic_pitch_inference, "ONNX_PRESENT", True)
    setattr(basic_pitch_inference, "ort", onnxruntime)
