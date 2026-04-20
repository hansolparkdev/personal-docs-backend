"""
코드 리뷰 에이전트 (GPT-4o-mini)

사용법:
  python agents/reviewer.py --files src/auth.ts src/guard.ts --context "로그인 기능 구현"

출력 (stdout, JSON):
  {"result": "PASS"|"FAIL", "issues": [{"severity": "P0"|"P1", "file": "...", "message": "..."}]}

종료 코드:
  0 = PASS, 1 = FAIL, 2 = 실행 오류
"""

import argparse
import json
import sys
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

SYSTEM_PROMPT = """당신은 코드 리뷰어입니다. 변경된 파일을 검토해 금지 패턴 위반을 찾습니다.

## 검토 항목

### 보안
- localStorage/sessionStorage에 토큰 저장
- NEXT_PUBLIC_* 환경변수로 API 키 노출
- RBAC를 프론트엔드에서만 처리
- 비즈니스 로직 본체가 클라이언트에 노출

### 상태 관리
- 문자열 리터럴 Query Key (queryKey: ["user"] 형태)
- setState + await 조합의 낙관적 업데이트
- fetch-on-render (useEffect 없이 컴포넌트 렌더시 fetch)
- Server Component에서 lib/api.ts 직접 호출

### 라우팅
- app/ 하위 라우팅 파일 외부 배치
- middleware.ts 사용
- 라우트 컴포넌트 테스트 누락

### 타입
- any 또는 @ts-ignore 무근거 사용
- Prisma 클라이언트를 매 요청마다 new로 생성

### UI
- 로딩/에러/빈 상태 3가지 미처리

## PASS 기준
위반이 0건이면 PASS.

## FAIL 기준
P0 (치명) 또는 P1 (주의) 위반이 1건 이상이면 FAIL.
- P0: 보안, 런타임 에러 유발 가능 항목
- P1: 상태·타입·UI 항목

## 출력 형식 (JSON만, 다른 텍스트 금지)
{"result": "PASS" or "FAIL", "issues": [{"severity": "P0" or "P1", "file": "파일경로", "message": "문제 설명"}]}

위반 없으면: {"result": "PASS", "issues": []}
"""


def read_files(file_paths: list[str]) -> str:
    parts = []
    for path_str in file_paths:
        path = Path(path_str)
        if not path.exists():
            parts.append(f"### {path_str}\n[파일 없음 — 삭제된 파일일 수 있음]")
            continue
        content = path.read_text(encoding="utf-8")
        parts.append(f"### {path_str}\n```\n{content}\n```")
    return "\n\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description="코드 리뷰 에이전트")
    parser.add_argument("--files", nargs="+", required=True, help="검토할 파일 경로 목록")
    parser.add_argument("--context", default="", help="변경 맥락 설명")
    args = parser.parse_args()

    files_content = read_files(args.files)

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    user_message = f"아래 파일들을 리뷰하세요."
    if args.context:
        user_message += f"\n\n변경 맥락: {args.context}"
    user_message += f"\n\n{files_content}"

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_message),
    ]

    try:
        response = llm.invoke(messages)
        raw = response.content.strip()

        if raw.startswith("```"):
            lines = raw.splitlines()
            raw = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        result = json.loads(raw)
    except Exception as e:
        # 실행 오류 시 수동 리뷰 모드로 전환 — developer가 직접 판단
        print(json.dumps({
            "result": "ERROR",
            "error": str(e),
            "fallback": "Python 스크립트 실행 오류. developer가 직접 코드를 검토하세요.",
        }, ensure_ascii=False))
        return 2

    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("result") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
