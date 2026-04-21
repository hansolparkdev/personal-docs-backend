#!/usr/bin/env bash
# pre_bash_server.sh
# Bash 툴 실행 전 서버 기동 명령어 감지 → 포트 점유 시 차단

COMMAND="${CLAUDE_TOOL_INPUT_COMMAND:-}"

# 서버 기동 명령 패턴 감지
if echo "$COMMAND" | grep -qE '(pnpm|npm|npx).*(dev|start|start:dev)\b'; then
  for PORT in 3000 3001; do
    PID=$(lsof -ti:$PORT 2>/dev/null)
    if [ -n "$PID" ]; then
      echo "BLOCKED: 포트 $PORT 이미 점유 중 (PID $PID). 서버를 새로 띄울 수 없습니다. 기존 프로세스를 재사용하거나 유저에게 에스컬레이션하세요." >&2
      exit 2
    fi
  done
fi

exit 0
