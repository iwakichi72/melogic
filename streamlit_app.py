from __future__ import annotations

import base64
from html import escape
from importlib.util import find_spec
import json
from pathlib import Path
import sys

import streamlit as st
import streamlit.components.v1 as components

from melogic import AnalysisError, ExportError, analyze_audio, export_analysis
from melogic.gui_io import save_audio_bytes
from melogic.visualization import build_piano_roll_rows


DEFAULT_OUTPUT_DIR = Path("out/gui")


def main() -> None:
    st.set_page_config(page_title="Melogic", layout="wide")
    inject_styles()

    st.title("Melogic")
    st.caption("録音または音声ファイルからMIDI、ノート一覧、確認用WAVを生成します。")
    status_message = st.session_state.pop("status_message", None)
    if status_message:
        st.success(status_message)
    render_runtime_notice()

    left, right = st.columns([0.9, 1.1], gap="large")
    with left:
        source_bytes, source_name, output_dir = render_input_panel()
    with right:
        render_result_panel()

    if source_bytes is not None and st.button("変換する", type="primary", use_container_width=True):
        run_conversion(source_bytes, source_name, output_dir)


def render_input_panel() -> tuple[bytes | None, str | None, Path]:
    st.subheader("入力")
    input_mode = st.radio("入力方法", ["録音", "ファイル"], horizontal=True)
    output_dir = Path(st.text_input("出力先", value=str(DEFAULT_OUTPUT_DIR))).expanduser()

    source_bytes = None
    source_name = None

    if input_mode == "録音":
        recorded_audio = st.audio_input("マイクで録音", sample_rate=44_100)
        if recorded_audio is not None:
            source_bytes = recorded_audio.getvalue()
            source_name = timestamped_recording_name()
            st.audio(source_bytes, format="audio/wav")
    else:
        uploaded_audio = st.file_uploader(
            "音声ファイルを選択",
            type=["wav", "mp3", "aiff", "aif"],
            accept_multiple_files=False,
        )
        if uploaded_audio is not None:
            source_bytes = uploaded_audio.getvalue()
            source_name = uploaded_audio.name
            st.audio(source_bytes, format=uploaded_audio.type or "audio/wav")

    st.info("変換すると、MIDI / JSON / CSV / 確認用WAVが出力先に保存されます。")
    return source_bytes, source_name, output_dir


def render_result_panel() -> None:
    st.subheader("解析結果")
    result = st.session_state.get("last_conversion")
    if result is None:
        st.write("まだ変換結果はありません。録音またはファイルを選んで変換してください。")
        return

    paths = result["paths"]
    notes = result["notes"]

    metrics = st.columns(3)
    metrics[0].metric("Notes", len(notes))
    metrics[1].metric("MIDI", paths.midi.name)
    metrics[2].metric("Preview", paths.preview_wav.name if paths.preview_wav else "off")

    preview_audio = paths.preview_wav.read_bytes() if paths.preview_wav is not None and paths.preview_wav.exists() else None

    piano_roll_tab, table_tab = st.tabs(["横ノーツビュー", "一覧"])
    with piano_roll_tab:
        render_piano_roll(notes, preview_audio)
    with table_tab:
        st.dataframe(notes, use_container_width=True, hide_index=True)
    render_downloads(paths)


def render_piano_roll(notes: list[dict], preview_audio: bytes | None) -> None:
    rows = build_piano_roll_rows(notes)
    if not rows:
        st.write("表示できるノートがありません。")
        return

    html, height = build_left_flow_note_view(rows, preview_audio)
    components.html(html, height=height, scrolling=True)


def build_left_flow_note_view(rows: list[dict], preview_audio: bytes | None = None) -> tuple[str, int]:
    note_numbers = sorted({int(row["note_number"]) for row in rows})
    min_note = min(note_numbers)
    max_note = max(note_numbers)
    lanes = list(range(max_note, min_note - 1, -1))
    lane_count = len(lanes)
    lane_height = 26 if lane_count <= 28 else 22
    track_height = max(220, lane_count * lane_height)
    component_height = min(820, track_height + 142)
    px_per_second = 72
    max_end_time = max(float(row["end_time"]) for row in rows)
    audio_source = audio_data_url(preview_audio)
    audio_markup = (
        f'<audio id="melogic-audio" class="melogic-audio" controls preload="metadata" src="{audio_source}"></audio>'
        if audio_source
        else '<div class="melogic-audio melogic-audio--missing">確認用WAVがないため、同期再生は利用できません。</div>'
    )

    lane_index = {note_number: index for index, note_number in enumerate(lanes)}
    key_markup = "\n".join(
        render_piano_key(note_number, lane_height) for note_number in lanes
    )
    note_markup = "\n".join(
        render_flow_note(row, lane_index[int(row["note_number"])], lane_height, px_per_second)
        for row in rows
    )
    note_payload = json.dumps(
        [
            {
                "start": max(0.0, float(row["start_time"])),
                "end": max(0.0, float(row["end_time"])),
            }
            for row in rows
        ],
        ensure_ascii=False,
    )

    html = f"""
<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<style>
  * {{
    box-sizing: border-box;
  }}
  body {{
    margin: 0;
    background: transparent;
    color: #f8f4ec;
    font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Helvetica Neue", sans-serif;
  }}
  .melogic-flow {{
    width: 100%;
    min-width: 720px;
    border: 1px solid rgba(28, 23, 19, 0.18);
    border-radius: 8px;
    overflow: hidden;
    background: #11120f;
    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.04);
  }}
  .melogic-flow__header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    min-height: 42px;
    padding: 10px 14px;
    background: #1d211c;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }}
  .melogic-flow__title {{
    font-size: 14px;
    font-weight: 760;
    letter-spacing: 0;
    color: #fff7e6;
  }}
  .melogic-flow__meta {{
    font-size: 12px;
    color: #c9c0b1;
    white-space: nowrap;
  }}
  .melogic-transport {{
    display: grid;
    grid-template-columns: minmax(220px, 1fr) auto;
    align-items: center;
    gap: 14px;
    padding: 10px 14px;
    background: #121510;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }}
  .melogic-audio {{
    width: 100%;
    height: 34px;
  }}
  .melogic-audio--missing {{
    display: flex;
    align-items: center;
    color: #d9cdbb;
    font-size: 12px;
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 8px;
    padding: 0 12px;
    background: rgba(255,255,255,0.04);
  }}
  .melogic-clock {{
    min-width: 136px;
    color: #fff7e6;
    font-size: 12px;
    font-weight: 760;
    text-align: right;
    font-variant-numeric: tabular-nums;
  }}
  .melogic-flow__body {{
    display: grid;
    grid-template-columns: 92px 1fr;
    height: {track_height}px;
    min-height: 220px;
  }}
  .melogic-keys {{
    position: relative;
    height: {track_height}px;
    background: #0a0b0a;
    border-right: 2px solid #31423c;
  }}
  .melogic-key {{
    height: {lane_height}px;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    padding: 0 10px 0 6px;
    border-bottom: 1px solid rgba(34, 28, 22, 0.22);
    font-size: 11px;
    font-weight: 720;
    letter-spacing: 0;
  }}
  .melogic-key--white {{
    background: linear-gradient(90deg, #f8f0de, #ded2bc);
    color: #18130f;
  }}
  .melogic-key--black {{
    width: 72%;
    margin-left: auto;
    background: linear-gradient(90deg, #23241f, #0c0d0b);
    color: #f5ebd8;
    border-bottom-color: rgba(255,255,255,0.10);
  }}
  .melogic-stream {{
    position: relative;
    height: {track_height}px;
    overflow: hidden;
    background:
      linear-gradient(90deg, rgba(255,255,255,0.06) 1px, transparent 1px) 0 0 / 72px 100%,
      linear-gradient(180deg, rgba(255,255,255,0.045) 1px, transparent 1px) 0 0 / 100% {lane_height}px,
      radial-gradient(circle at 82% 20%, rgba(240,111,73,0.15), transparent 20rem),
      #121610;
  }}
  .melogic-hitline {{
    position: absolute;
    left: 28px;
    top: 0;
    bottom: 0;
    width: 3px;
    background: #f06f49;
    box-shadow: 0 0 18px rgba(240,111,73,0.62);
    z-index: 4;
  }}
  .melogic-note {{
    position: absolute;
    left: 0;
    top: var(--lane-y);
    width: var(--note-width);
    height: {max(12, lane_height - 7)}px;
    border-radius: 999px;
    background: linear-gradient(90deg, #ffe39a, #f06f49);
    box-shadow: 0 0 12px rgba(240,111,73,0.38), inset 0 0 0 1px rgba(255,255,255,0.35);
    transform: translateX(var(--note-x));
    transition: opacity 120ms linear;
    z-index: 3;
  }}
  .melogic-note--past {{
    opacity: 0.18;
  }}
  .melogic-note::after {{
    content: attr(data-label);
    position: absolute;
    left: 10px;
    top: 50%;
    transform: translateY(-50%);
    color: #21150c;
    font-size: 10px;
    font-weight: 800;
    white-space: nowrap;
    opacity: 0.86;
  }}
</style>
</head>
<body>
  <div class="melogic-flow">
    <div class="melogic-flow__header">
      <div class="melogic-flow__title">同期ノーツビュー</div>
      <div class="melogic-flow__meta">{len(rows)} notes / {min_note}-{max_note} MIDI / {max_end_time:.2f}s</div>
    </div>
    <div class="melogic-transport">
      {audio_markup}
      <div id="melogic-clock" class="melogic-clock">0.000s / {max_end_time:.3f}s</div>
    </div>
    <div class="melogic-flow__body">
      <div class="melogic-keys" aria-label="piano keys">
        {key_markup}
      </div>
      <div class="melogic-stream" aria-label="left flowing notes">
        <div class="melogic-hitline"></div>
        {note_markup}
      </div>
    </div>
  </div>
  <script>
    const notes = {note_payload};
    const noteElements = Array.from(document.querySelectorAll(".melogic-note"));
    const audio = document.getElementById("melogic-audio");
    const clock = document.getElementById("melogic-clock");
    const hitlineX = 28;
    const pxPerSecond = {px_per_second};
    const maxEndTime = {max_end_time:.6f};

    function updateNotes() {{
      const currentTime = audio && typeof audio.currentTime === "number" ? audio.currentTime : 0;
      noteElements.forEach((element, index) => {{
        const note = notes[index];
        const x = hitlineX + (note.start - currentTime) * pxPerSecond;
        element.style.setProperty("--note-x", `${{x}}px`);
        element.classList.toggle("melogic-note--past", note.end < currentTime);
      }});
      if (clock) {{
        const duration = audio && Number.isFinite(audio.duration) ? audio.duration : maxEndTime;
        clock.textContent = `${{currentTime.toFixed(3)}}s / ${{duration.toFixed(3)}}s`;
      }}
    }}

    function animate() {{
      updateNotes();
      if (audio && !audio.paused && !audio.ended) {{
        requestAnimationFrame(animate);
      }}
    }}

    if (audio && audio.tagName === "AUDIO") {{
      audio.addEventListener("play", () => requestAnimationFrame(animate));
      audio.addEventListener("pause", updateNotes);
      audio.addEventListener("seeked", updateNotes);
      audio.addEventListener("timeupdate", updateNotes);
      audio.addEventListener("loadedmetadata", updateNotes);
    }}
    updateNotes();
  </script>
</body>
</html>
"""
    return html, component_height


def audio_data_url(audio_bytes: bytes | None) -> str | None:
    if not audio_bytes:
        return None
    encoded = base64.b64encode(audio_bytes).decode("ascii")
    return f"data:audio/wav;base64,{encoded}"


def render_piano_key(note_number: int, lane_height: int) -> str:
    note_name = midi_note_name(note_number)
    key_class = "melogic-key--black" if "#" in note_name else "melogic-key--white"
    return (
        f'<div class="melogic-key {key_class}" style="height:{lane_height}px">'
        f"{escape(note_name)}</div>"
    )


def render_flow_note(
    row: dict,
    lane_index: int,
    lane_height: int,
    px_per_second: int,
) -> str:
    start_time = max(0.0, float(row["start_time"]))
    duration = max(0.05, float(row["duration"]))
    note_width = max(22, int(duration * px_per_second))
    start_x = int(start_time * px_per_second)
    lane_y = lane_index * lane_height + 4
    velocity = max(0, min(127, int(row["velocity"])))
    saturation = 48 + int((velocity / 127) * 28)
    label = escape(str(row["note_name"]))
    title = escape(
        f'{row["note_name"]} / start {start_time:.3f}s / duration {duration:.3f}s / velocity {velocity}'
    )
    return (
        '<div class="melogic-note" '
        f'data-label="{label}" title="{title}" '
        f'style="--note-x:{start_x}px; --lane-y:{lane_y}px; --note-width:{note_width}px; '
        f'filter:saturate({saturation}%);"></div>'
    )


def midi_note_name(note_number: int) -> str:
    note_names = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
    return f"{note_names[note_number % 12]}{note_number // 12 - 1}"


def render_downloads(paths) -> None:
    st.write("ダウンロード")
    cols = st.columns(4)
    download_specs = [
        (cols[0], "MIDI", paths.midi, "audio/midi"),
        (cols[1], "JSON", paths.json, "application/json"),
        (cols[2], "CSV", paths.csv, "text/csv"),
        (cols[3], "Preview WAV", paths.preview_wav, "audio/wav"),
    ]
    for column, label, path, mime in download_specs:
        if path is None or not path.exists():
            column.button(label, disabled=True, use_container_width=True)
            continue
        column.download_button(
            label,
            data=path.read_bytes(),
            file_name=path.name,
            mime=mime,
            use_container_width=True,
        )


def run_conversion(source_bytes: bytes, source_name: str | None, output_dir: Path) -> None:
    try:
        saved_input = save_audio_bytes(source_bytes, source_name, output_dir)
        with st.spinner("Basic Pitchで解析しています。長い音源は少し時間がかかります。"):
            analysis = analyze_audio(saved_input.path)
            paths = export_analysis(analysis, output_dir, preview_wav=True)
    except (AnalysisError, ExportError, OSError) as exc:
        st.error(f"変換に失敗しました: {exc}")
        return

    st.session_state["last_conversion"] = {
        "paths": paths,
        "notes": [note.to_dict() for note in analysis.notes],
        "source": str(saved_input.path),
    }
    st.session_state["status_message"] = "変換が完了しました。"
    st.rerun()


def render_runtime_notice() -> None:
    status = get_basic_pitch_status()
    if not status["ok"]:
        st.warning(
            "Basic Pitchを読み込めていません。ターミナルでこのアプリを停止し、"
            "`./run_gui.sh` で起動し直してください。"
        )

    with st.expander("実行環境", expanded=not status["ok"]):
        st.write(f"Python: `{sys.executable}`")
        st.write(f"Basic Pitch: `{status['message']}`")


def get_basic_pitch_status() -> dict[str, object]:
    missing = [name for name in ("basic_pitch", "pkg_resources") if find_spec(name) is None]
    if missing:
        return {"ok": False, "message": f"missing: {', '.join(missing)}"}
    return {"ok": True, "message": "OK"}


def timestamped_recording_name() -> str:
    from datetime import datetime

    return f"recording_{datetime.now().strftime('%Y%m%d-%H%M%S')}.wav"


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
          --melogic-text: #1c1713;
          --melogic-muted: #514840;
          --melogic-panel: rgba(255, 255, 255, 0.86);
          --melogic-line: rgba(34, 28, 22, 0.16);
          --melogic-accent: #1f6f61;
        }
        .stApp {
          background:
            radial-gradient(circle at top left, rgba(42, 130, 113, 0.14), transparent 28rem),
            linear-gradient(180deg, #fbfaf6 0%, #f1efe7 100%);
          color: var(--melogic-text);
        }
        .stApp,
        .stApp p,
        .stApp li,
        .stApp span,
        .stApp label,
        .stApp div,
        [data-testid="stMarkdownContainer"],
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stWidgetLabel"],
        [data-testid="stMetricLabel"],
        [data-testid="stMetricValue"] {
          color: var(--melogic-text);
        }
        h1, h2, h3 {
          letter-spacing: 0;
          font-weight: 760;
          color: var(--melogic-text);
        }
        .stCaptionContainer,
        [data-testid="stCaptionContainer"],
        [data-testid="stMetricDelta"] {
          color: var(--melogic-muted);
        }
        [data-testid="stMetric"] {
          background: var(--melogic-panel);
          border: 1px solid var(--melogic-line);
          border-radius: 8px;
          padding: 0.8rem 0.9rem;
        }
        .stTextInput input {
          color: var(--melogic-text);
          background: #ffffff;
          border: 1px solid var(--melogic-line);
        }
        .stButton > button,
        .stDownloadButton > button {
          border-radius: 8px;
          font-weight: 680;
          min-height: 2.6rem;
        }
        .stButton > button[kind="secondary"] {
          background: #ffffff;
          border: 1px solid #8d806d;
          color: var(--melogic-text) !important;
        }
        .stButton > button[kind="secondary"] *,
        .stButton > button[kind="secondary"] p,
        .stButton > button[kind="secondary"] span {
          color: var(--melogic-text) !important;
        }
        .stButton > button[kind="primary"] {
          background: var(--melogic-accent) !important;
          border-color: var(--melogic-accent) !important;
          color: #ffffff !important;
        }
        .stButton > button[kind="primary"] *,
        .stButton > button[kind="primary"] p,
        .stButton > button[kind="primary"] span {
          color: #ffffff !important;
        }
        .stDownloadButton > button {
          background: #213f3a;
          border: 1px solid #213f3a;
          color: #ffffff !important;
        }
        .stDownloadButton > button *,
        .stDownloadButton > button p,
        .stDownloadButton > button span {
          color: #ffffff !important;
        }
        .stButton > button:disabled,
        .stDownloadButton > button:disabled {
          background: #e5ded2 !important;
          border-color: #d0c5b5 !important;
          color: #6e6256 !important;
        }
        .stButton > button:disabled *,
        .stDownloadButton > button:disabled * {
          color: #6e6256 !important;
        }
        .stButton > button:hover:not(:disabled),
        .stDownloadButton > button:hover:not(:disabled) {
          filter: brightness(0.96);
        }
        .stAlert {
          color: var(--melogic-text);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
