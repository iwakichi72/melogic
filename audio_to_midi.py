#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from melogic import (
    AnalysisError,
    AnalysisMode,
    ExportError,
    analysis_mode_label,
    analysis_mode_values,
    analyze_audio,
    export_analysis,
    output_stem_for_mode,
    prepare_analysis_input,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze an audio file with Basic Pitch and export MIDI, JSON, and CSV note data."
    )
    parser.add_argument("input_audio", help="Path to a .wav, .mp3, .aiff, or .aif audio file.")
    parser.add_argument("output_dir", help="Directory where .mid, .json, and .csv files will be written.")
    parser.add_argument(
        "--preview-wav",
        action="store_true",
        help="Also render a simple WAV preview of the generated MIDI for quick listening.",
    )
    parser.add_argument(
        "--mode",
        choices=analysis_mode_values(),
        default=AnalysisMode.STANDARD.value,
        help=(
            "Analysis mode. Use 'vocal' or 'accompaniment' to run optional Demucs "
            "stem separation before Basic Pitch."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    input_audio = Path(args.input_audio)
    output_dir = Path(args.output_dir).expanduser()

    try:
        validate_output_target(output_dir)
        if args.mode == AnalysisMode.STANDARD.value:
            result = analyze_audio(input_audio)
            paths = export_analysis(result, output_dir, preview_wav=args.preview_wav)
            prepared_input = None
        else:
            prepared_input = prepare_analysis_input(input_audio, args.mode, output_dir)
            result = analyze_audio(prepared_input.path)
            paths = export_analysis(
                result,
                output_dir,
                preview_wav=args.preview_wav,
                output_stem=output_stem_for_mode(input_audio, args.mode),
            )
    except AnalysisError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except ExportError as exc:
        print(f"Error: Failed to export analysis: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Error: Failed to write output files: {exc}", file=sys.stderr)
        return 1

    print(f"Source: {result.source_audio}")
    print(f"Analysis Mode: {analysis_mode_label(args.mode)}")
    if prepared_input is not None:
        print(f"Original Source: {prepared_input.source_path}")
        print(f"Analysis Input: {prepared_input.path}")
    print(f"Notes: {result.note_count}")
    print(f"MIDI: {paths.midi}")
    print(f"JSON: {paths.json}")
    print(f"CSV: {paths.csv}")
    if paths.preview_wav is not None:
        print(f"Preview WAV: {paths.preview_wav}")
    print()
    print_note_table(result)
    return 0


def validate_output_target(output_dir: Path) -> None:
    if output_dir.exists() and not output_dir.is_dir():
        raise ExportError(f"Output path exists and is not a directory: {output_dir}")


def print_note_table(result) -> None:
    if not result.notes:
        print("No notes detected.")
        return

    headers = ("#", "note", "start", "end", "duration", "velocity", "confidence")
    print(f"{headers[0]:>4}  {headers[1]:<6}  {headers[2]:>9}  {headers[3]:>9}  {headers[4]:>9}  {headers[5]:>8}  {headers[6]:>10}")
    print("-" * 76)
    for index, note in enumerate(result.notes, start=1):
        confidence = "" if note.confidence is None else f"{note.confidence:.3f}"
        print(
            f"{index:>4}  "
            f"{note.note_name:<6}  "
            f"{note.start_time:>9.3f}  "
            f"{note.end_time:>9.3f}  "
            f"{note.duration:>9.3f}  "
            f"{note.velocity:>8}  "
            f"{confidence:>10}"
        )


if __name__ == "__main__":
    raise SystemExit(main())
