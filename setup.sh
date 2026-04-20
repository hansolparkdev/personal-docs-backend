#!/bin/bash
set -e

python3 -m venv agents/.venv
agents/.venv/bin/pip install --upgrade pip
agents/.venv/bin/pip install -r agents/requirements.txt

echo "✓ 설치 완료"
echo "  .env 파일에 OPENAI_API_KEY 설정 후 사용하세요."
