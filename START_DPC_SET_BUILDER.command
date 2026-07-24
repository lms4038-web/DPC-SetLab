#!/bin/bash
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.10 이상을 설치해주세요."
  read -p "Enter를 누르면 종료합니다."
  exit 1
fi
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
python -m pip install --disable-pip-version-check -q -r requirements.txt
[ -f config.json ] || cp config.example.json config.json
python -m streamlit run app.py
