from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def note_number_to_name(note_number: int) -> str:
    """Convert a MIDI note number to a note name such as C4."""
    octave = note_number // 12 - 1
    name = NOTE_NAMES[note_number % 12]
    return f"{name}{octave}"


@dataclass(frozen=True)
class NoteRecord:
    note_number: int
    note_name: str
    start_time: float
    end_time: float
    duration: float
    velocity: int
    confidence: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "note_number": self.note_number,
            "note_name": self.note_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "velocity": self.velocity,
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class AnalysisResult:
    source_audio: str
    generated_at: str
    notes: list[NoteRecord]
    midi_data: Any = field(default=None, repr=False, compare=False)

    @property
    def note_count(self) -> int:
        return len(self.notes)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "source_audio": self.source_audio,
            "generated_at": self.generated_at,
            "note_count": self.note_count,
            "notes": [note.to_dict() for note in self.notes],
        }
