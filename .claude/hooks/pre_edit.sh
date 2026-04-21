#!/usr/bin/env bash
# PreToolUse hook: Claude가 Edit/Write를 호출할 때 실행
# 수정 대상 파일이 TS/TSX면 ESLint로 즉시 검사

FILE=$(echo "$TOOL_INPUT" | jq -r '.file_path // empty')

if [[ -z "$FILE" ]]; then
  exit 0
fi

case "$FILE" in
  *.ts|*.tsx)
    if [[ -f "node_modules/.bin/eslint" ]]; then
      npx eslint --no-warn-ignored "$FILE" 2>&1 || exit 2
    fi
    ;;
esac

exit 0
