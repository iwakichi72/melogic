#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
  echo "Error: .venv/bin/python が見つかりません。" >&2
  echo "先に次を実行してください:" >&2
  echo "  /opt/homebrew/bin/python3.11 -m venv .venv" >&2
  echo "  .venv/bin/python -m pip install -r requirements.txt" >&2
  exit 1
fi

exec .venv/bin/python -m streamlit run streamlit_app.py "$@"
