from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from importlib.metadata import PackageNotFoundError, version
from importlib.util import find_spec
from pathlib import Path

from .analyzer import AnalysisError, validate_input_audio


DEFAULT_DEMUCS_MODEL = "htdemucs"


class AnalysisMode(str, Enum):
    STANDARD = "standard"
    VOCAL = "vocal"
    ACCOMPANIMENT = "accompaniment"


ANALYSIS_MODE_LABELS = {
    AnalysisMode.STANDARD: "標準（そのまま解析）",
    AnalysisMode.VOCAL: "ボーカル優先（Demucs vocals）",
    AnalysisMode.ACCOMPANIMENT: "伴奏/リード候補（Demucs no_vocals）",
}

ANALYSIS_MODE_DESCRIPTIONS = {
    AnalysisMode.STANDARD: "Basic Pitchへ元音源をそのまま渡します。",
    AnalysisMode.VOCAL: "歌メロを拾いたい時向けです。Demucsでボーカルを分離してから解析します。",
    AnalysisMode.ACCOMPANIMENT: "ギター、シンセ、伴奏側のリードを拾いたい時向けです。ボーカル抜き音源を解析します。",
}

DEMUCS_STEM_FILENAMES = {
    AnalysisMode.VOCAL: "vocals.wav",
    AnalysisMode.ACCOMPANIMENT: "no_vocals.wav",
}

OUTPUT_STEM_SUFFIXES = {
    AnalysisMode.STANDARD: "",
    AnalysisMode.VOCAL: "vocals",
    AnalysisMode.ACCOMPANIMENT: "no_vocals",
}


@dataclass(frozen=True)
class PreparedAnalysisInput:
    path: Path
    source_path: Path
    mode: AnalysisMode
    label: str
    used_demucs: bool = False


def analysis_mode_values() -> list[str]:
    return [mode.value for mode in AnalysisMode]


def analysis_mode_label(mode: str | AnalysisMode) -> str:
    return ANALYSIS_MODE_LABELS[coerce_analysis_mode(mode)]


def analysis_mode_description(mode: str | AnalysisMode) -> str:
    return ANALYSIS_MODE_DESCRIPTIONS[coerce_analysis_mode(mode)]


def coerce_analysis_mode(mode: str | AnalysisMode) -> AnalysisMode:
    if isinstance(mode, AnalysisMode):
        return mode
    try:
        return AnalysisMode(mode)
    except ValueError as exc:
        supported = ", ".join(analysis_mode_values())
        raise AnalysisError(f"Unsupported analysis mode '{mode}'. Supported: {supported}") from exc


def prepare_analysis_input(
    input_audio: str | Path,
    mode: str | AnalysisMode,
    output_dir: str | Path,
    demucs_model: str = DEFAULT_DEMUCS_MODEL,
) -> PreparedAnalysisInput:
    source_path = validate_input_audio(input_audio)
    selected_mode = coerce_analysis_mode(mode)
    if selected_mode is AnalysisMode.STANDARD:
        return PreparedAnalysisInput(
            path=source_path,
            source_path=source_path,
            mode=selected_mode,
            label=analysis_mode_label(selected_mode),
        )

    stem_path = separate_with_demucs(source_path, selected_mode, Path(output_dir), demucs_model)
    return PreparedAnalysisInput(
        path=stem_path,
        source_path=source_path,
        mode=selected_mode,
        label=analysis_mode_label(selected_mode),
        used_demucs=True,
    )


def separate_with_demucs(
    input_audio: Path,
    mode: AnalysisMode,
    output_dir: Path,
    demucs_model: str = DEFAULT_DEMUCS_MODEL,
) -> Path:
    demucs_status = get_demucs_status()
    if not demucs_status["ok"]:
        raise AnalysisError(
            f"Demucs runtime is not ready: {demucs_status['message']}. "
            "Install it with: .venv/bin/python -m pip install -r requirements-band.txt"
        )

    stem_filename = DEMUCS_STEM_FILENAMES.get(mode)
    if stem_filename is None:
        raise AnalysisError(f"Demucs separation is not used for analysis mode: {mode.value}")

    stems_root = output_dir.expanduser() / "_stems"
    command = [
        sys.executable,
        "-m",
        "demucs",
        "--two-stems=vocals",
        "-n",
        demucs_model,
        "-o",
        str(stems_root),
        str(input_audio),
    ]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or "").strip()
        message = f"Demucs stem separation failed for {input_audio}."
        if details:
            message = f"{message} Details: {details}"
        raise AnalysisError(message) from exc
    except OSError as exc:
        raise AnalysisError(f"Could not run Demucs: {exc}") from exc

    return find_demucs_stem(stems_root, demucs_model, input_audio.stem, stem_filename)


def find_demucs_stem(stems_root: Path, demucs_model: str, track_stem: str, stem_filename: str) -> Path:
    expected_path = stems_root / demucs_model / track_stem / stem_filename
    if expected_path.exists():
        return expected_path

    model_dir = stems_root / demucs_model
    candidates = sorted(model_dir.glob(f"*/{stem_filename}")) if model_dir.exists() else []
    if len(candidates) == 1:
        return candidates[0]

    raise AnalysisError(
        "Demucs finished, but the expected stem file was not found: "
        f"{expected_path}"
    )


def output_stem_for_mode(source_audio: str | Path, mode: str | AnalysisMode) -> str:
    selected_mode = coerce_analysis_mode(mode)
    base_stem = sanitize_output_stem(Path(source_audio).stem)
    suffix = OUTPUT_STEM_SUFFIXES[selected_mode]
    if not suffix:
        return base_stem
    return f"{base_stem}_{suffix}"


def sanitize_output_stem(stem: str) -> str:
    safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("._-")
    return safe_stem or "analysis"


def is_demucs_available() -> bool:
    return find_spec("demucs") is not None


def get_demucs_status() -> dict[str, object]:
    if not is_demucs_available():
        return {"ok": False, "message": "not installed (optional)"}
    missing = [name for name in ("torch", "torchaudio") if find_spec(name) is None]
    if missing:
        return {"ok": False, "message": f"missing: {', '.join(missing)}"}

    torchaudio_version = package_version_or_unknown("torchaudio")
    if torchaudio_needs_torchcodec(torchaudio_version) and find_spec("torchcodec") is None:
        return {
            "ok": False,
            "message": f"missing: torchcodec (required by torchaudio {torchaudio_version})",
        }

    try:
        demucs_version = version("demucs")
    except PackageNotFoundError:
        demucs_version = "installed"
    return {"ok": True, "message": f"{demucs_version} / torchaudio {torchaudio_version}"}


def package_version_or_unknown(package_name: str) -> str:
    try:
        return version(package_name)
    except PackageNotFoundError:
        return "unknown"


def torchaudio_needs_torchcodec(torchaudio_version: str) -> bool:
    parsed = parse_major_minor(torchaudio_version)
    if parsed is None:
        return False
    return parsed >= (2, 9)


def parse_major_minor(version_text: str) -> tuple[int, int] | None:
    match = re.match(r"^(\d+)\.(\d+)", version_text)
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2))
