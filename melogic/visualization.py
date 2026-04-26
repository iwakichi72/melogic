from __future__ import annotations

from typing import Any

from .models import NoteRecord


def build_piano_roll_rows(notes: list[NoteRecord] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for index, note in enumerate(notes, start=1):
        data = note.to_dict() if isinstance(note, NoteRecord) else note
        note_number = int(data["note_number"])
        note_name = str(data["note_name"])
        start_time = float(data["start_time"])
        end_time = float(data["end_time"])
        duration = float(data["duration"])
        velocity = int(data["velocity"])
        confidence = data.get("confidence")

        rows.append(
            {
                "index": index,
                "note_number": note_number,
                "note_name": note_name,
                "note_label": f"{note_name} / {note_number}",
                "start_time": start_time,
                "end_time": end_time,
                "duration": duration,
                "velocity": velocity,
                "confidence": confidence,
            }
        )

    return sorted(rows, key=lambda row: (row["start_time"], row["note_number"], row["index"]))
