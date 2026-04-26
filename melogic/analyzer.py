from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from .models import AnalysisResult, NoteRecord, note_number_to_name


SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".aiff", ".aif"}


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


def analyze_audio(input_audio: str | Path) -> AnalysisResult:
    input_path = validate_input_audio(input_audio)

    try:
        from basic_pitch.inference import predict
    except ImportError as exc:
        raise AnalysisError(
            "Basic Pitch or one of its dependencies could not be imported. "
            f"Details: {exc}. "
            "Use the project virtual environment and run: .venv/bin/python -m pip install -r requirements.txt"
        ) from exc

    try:
        _model_output, midi_data, note_events = predict(str(input_path))
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
