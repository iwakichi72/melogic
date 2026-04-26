# Melogic Audio-to-MIDI解析ツール

Melogicは、読み取り専用のAudio-to-MIDI解析ツールです。既存音源や録音音声から、ノート、音程、タイミング、MIDI情報を抽出することに集中しています。音声編集、ピッチ補正、タイミング補正、ノートのドラッグ編集は行いません。

初期版はCLIとStreamlit GUIの両方から使える構成です。解析処理と書き出し処理はUIから分離しているため、将来的にTauri + Reactへ移行する場合も同じ中核モジュールを再利用できます。

## 機能

- `.wav`, `.mp3`, `.aiff`, `.aif` ファイルを読み込みます。
- Basic Pitchを使ってAudio-to-MIDI変換を行います。
- `.mid`, `.json`, `.csv` を書き出します。
- 生成したMIDIをすぐ確認するための簡易 `.wav` プレビューを作成できます。
- Streamlit GUIから録音し、そのままブラウザ上で変換できます。
- GUIでは変換後のノートをDAW/音ゲー風のノーツビューで確認できます。
- CLIではノート一覧をターミナルに表示します。
- 将来のピアノロール表示に備えて、UIに依存しないノートデータ構造を使います。

## 必要環境

Basic Pitch 0.4.0はPython 3.8-3.11を主な対象にしています。特にmacOSでは、Python 3.10または3.11の利用を推奨します。

```bash
/opt/homebrew/bin/python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`/opt/homebrew/bin/python3.11` が使えない場合は、先にPython 3.10または3.11をインストールし、そのPythonで仮想環境を作成してください。

## 使い方

### GUI

```bash
./run_gui.sh
```

GUIでは、マイク録音と音声ファイルのアップロードに対応しています。変換すると、デフォルトでは `out/gui` にMIDI、JSON、CSV、確認用WAVを書き出します。

録音時は、ブラウザがマイク利用の許可を求めます。Streamlitの `st.audio_input` でWAV音声を録音し、Melogicは解析前にそのテイクを `out/gui/_inputs` に保存します。

変換後は、確認用WAVと同期するノーツビュー、一覧表、各ファイルのダウンロードを同じ画面で確認できます。ノーツビューは音源の再生・停止・シークに追従します。

同じことを手動で実行する場合:

```bash
.venv/bin/python -m streamlit run streamlit_app.py
```

### CLI

```bash
python audio_to_midi.py ./samples/vocal.wav ./out
```

生成したMIDIをすぐ聴ける確認用WAVも作成する場合:

```bash
python audio_to_midi.py ./samples/vocal.wav ./out --preview-wav
```

`./samples/vocal.wav` を入力した場合、CLIは次のファイルを書き出します。

```text
out/vocal.mid
out/vocal.json
out/vocal.csv
out/vocal_preview.wav  # --preview-wav 指定時のみ
```

ターミナルには、ノート名、開始時刻、終了時刻、長さ、ベロシティ、confidenceを含むノート一覧も表示します。

確認用WAVは、`pretty_midi` の内蔵シンセサイザーでMIDIから生成します。最終品質の音源ではなく、音程とタイミングを素早く確認するためのものです。

## JSON形式

```json
{
  "source_audio": "samples/vocal.wav",
  "generated_at": "2026-04-26T12:00:00+00:00",
  "note_count": 1,
  "notes": [
    {
      "note_number": 60,
      "note_name": "C4",
      "start_time": 0.25,
      "end_time": 1.0,
      "duration": 0.75,
      "velocity": 102,
      "confidence": null
    }
  ]
}
```

`confidence` は将来の拡張に備えてフィールドとして含めています。ただし、このMVPで使用しているBasic Pitchのnote eventからはノート単位の直接的なconfidence値を取得できないため、値は `null` になります。Basic PitchのamplitudeはMIDI velocityの算出にのみ使います。

## 注意点と制限

- Basic Pitchは解析時にステレオ音声を内部でモノラル化します。
- 音声は解析前に内部でリサンプリングされます。
- 長い音源は処理に時間がかかり、ディスク容量やメモリを多く使う場合があります。
- このツールは解析専用です。ピッチ補正、タイミング補正、音声編集、ノート編集は行いません。

## トラブルシューティング

GUIで `Basic Pitch or one of its dependencies could not be imported` と表示される場合は、別のPython環境でStreamlitを起動している可能性があります。一度Streamlitを停止し、次のコマンドで起動し直してください。

```bash
./run_gui.sh
```

依存関係を入れ直す場合:

```bash
.venv/bin/python -m pip install -r requirements.txt
```

`basic_pitch.inference ok` と表示されれば、Basic Pitchの読み込みは成功しています。

```bash
.venv/bin/python -c "from basic_pitch.inference import predict; print('basic_pitch.inference ok')"
```

## 開発

ユニットテストを実行する場合:

```bash
python -m unittest discover -s tests
```
