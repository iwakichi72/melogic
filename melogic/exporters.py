from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path

from .models import AnalysisResult
from .preview import PreviewError, write_preview_wav


class ExportError(RuntimeError):
    """Raised when analysis output cannot be exported."""


NOTE_FIELDNAMES = [
    "note_number",
    "note_name",
    "start_time",
    "end_time",
    "duration",
    "velocity",
    "confidence",
]


@dataclass(frozen=True)
class ExportPaths:
    midi: Path
    json: Path
    csv: Path
    preview_wav: Path | None = None


def export_analysis(
    result: AnalysisResult,
    output_dir: str | Path,
    preview_wav: bool = False,
    output_stem: str | None = None,
) -> ExportPaths:
    out_dir = Path(output_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = sanitize_output_stem(output_stem or Path(result.source_audio).stem)
    paths = ExportPaths(
        midi=out_dir / f"{stem}.mid",
        json=out_dir / f"{stem}.json",
        csv=out_dir / f"{stem}.csv",
        preview_wav=out_dir / f"{stem}_preview.wav" if preview_wav else None,
    )

    write_midi(result, paths.midi)
    write_json(result, paths.json)
    write_csv(result, paths.csv)
    if paths.preview_wav is not None:
        try:
            write_preview_wav(result.midi_data, paths.preview_wav)
        except PreviewError as exc:
            raise ExportError(str(exc)) from exc
    return paths


def sanitize_output_stem(stem: str) -> str:
    safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("._-")
    return safe_stem or "analysis"


def write_midi(result: AnalysisResult, output_path: str | Path) -> None:
    if result.midi_data is None:
        raise ExportError("AnalysisResult.midi_data is required to export MIDI.")
    result.midi_data.write(str(output_path))


def write_json(result: AnalysisResult, output_path: str | Path) -> None:
    with Path(output_path).open("w", encoding="utf-8") as file:
        json.dump(result.to_json_dict(), file, ensure_ascii=False, indent=2)
        file.write("\n")


def write_csv(result: AnalysisResult, output_path: str | Path) -> None:
    with Path(output_path).open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=NOTE_FIELDNAMES)
        writer.writeheader()
        for note in result.notes:
            writer.writerow(note.to_dict())
