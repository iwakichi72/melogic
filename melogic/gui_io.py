from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .analyzer import AnalysisError, SUPPORTED_AUDIO_EXTENSIONS


@dataclass(frozen=True)
class SavedAudioInput:
    path: Path
    display_name: str


def save_audio_bytes(
    data: bytes,
    original_name: str | None,
    output_dir: str | Path,
    default_name: str = "recording.wav",
) -> SavedAudioInput:
    if not data:
        raise AnalysisError("Audio input is empty.")

    filename = sanitize_audio_filename(original_name or default_name, default_name)
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_AUDIO_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_AUDIO_EXTENSIONS))
        raise AnalysisError(f"Unsupported audio extension '{suffix}'. Supported: {supported}")

    inputs_dir = Path(output_dir).expanduser() / "_inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    target_path = unique_path(inputs_dir / filename)
    target_path.write_bytes(data)

    return SavedAudioInput(path=target_path, display_name=filename)


def sanitize_audio_filename(name: str, default_name: str) -> str:
    candidate = Path(name).name.strip() or default_name
    stem = Path(candidate).stem
    suffix = Path(candidate).suffix or Path(default_name).suffix

    safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("._-")
    if not safe_stem:
        safe_stem = Path(default_name).stem
    return f"{safe_stem}{suffix.lower()}"


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return path.with_name(f"{path.stem}_{timestamp}{path.suffix}")
