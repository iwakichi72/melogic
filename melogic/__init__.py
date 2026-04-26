"""Melogic audio-to-MIDI analysis package."""

from .analyzer import AnalysisError, SUPPORTED_AUDIO_EXTENSIONS, analyze_audio, note_event_to_record
from .exporters import ExportError, ExportPaths, export_analysis
from .models import AnalysisResult, NoteRecord, note_number_to_name
from .preview import DEFAULT_PREVIEW_SAMPLE_RATE, PreviewError, write_preview_wav
from .visualization import build_piano_roll_rows

__all__ = [
    "AnalysisError",
    "AnalysisResult",
    "ExportError",
    "ExportPaths",
    "NoteRecord",
    "PreviewError",
    "SUPPORTED_AUDIO_EXTENSIONS",
    "DEFAULT_PREVIEW_SAMPLE_RATE",
    "analyze_audio",
    "build_piano_roll_rows",
    "export_analysis",
    "note_event_to_record",
    "note_number_to_name",
    "write_preview_wav",
]
