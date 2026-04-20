#!/bin/bash
set -e

python3 -m venv agents/.venv
agents/.venv/bin/pip install --upgrade pip
agents/.venv/bin/pip install -r agents/requirements.txt

echo "✓ 설치 완료"
echo "  OPENAI_API_KEY는 .claude/settings.local.json env 항목에서 자동 주입됩니다."
