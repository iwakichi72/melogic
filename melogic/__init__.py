"""Melogic audio-to-MIDI analysis package."""

from .analyzer import AnalysisError, SUPPORTED_AUDIO_EXTENSIONS, analyze_audio, note_event_to_record
from .exporters import ExportError, ExportPaths, export_analysis
from .models import AnalysisResult, NoteRecord, note_number_to_name
from .preview import DEFAULT_PREVIEW_SAMPLE_RATE, PreviewError, write_preview_wav
from .stems import (
    AnalysisMode,
    PreparedAnalysisInput,
    analysis_mode_description,
    analysis_mode_label,
    analysis_mode_values,
    get_demucs_status,
    output_stem_for_mode,
    prepare_analysis_input,
)
from .visualization import build_piano_roll_rows

__all__ = [
    "AnalysisError",
    "AnalysisMode",
    "AnalysisResult",
    "ExportError",
    "ExportPaths",
    "NoteRecord",
    "PreparedAnalysisInput",
    "PreviewError",
    "SUPPORTED_AUDIO_EXTENSIONS",
    "DEFAULT_PREVIEW_SAMPLE_RATE",
    "analyze_audio",
    "analysis_mode_description",
    "analysis_mode_label",
    "analysis_mode_values",
    "build_piano_roll_rows",
    "export_analysis",
    "get_demucs_status",
    "note_event_to_record",
    "note_number_to_name",
    "output_stem_for_mode",
    "prepare_analysis_input",
    "write_preview_wav",
]
