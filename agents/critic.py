"""
기획서 비평 에이전트 (GPT-4o-mini)

사용법:
  python agents/critic.py --plan docs/plans/login/plan.md --round 1

출력 (stdout, JSON):
  {"result": "PASS"|"FAIL", "issues": ["..."], "improvements": ["..."]}

종료 코드:
  0 = PASS, 1 = FAIL, 2 = 실행 오류
"""

import argparse
import json
import sys
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

SYSTEM_PROMPT = """당신은 기획서 비평가입니다. 기획서의 품질을 평가합니다.

## FAIL 기준 (하나라도 해당하면 FAIL — 이것만 FAIL)
1. 사용자/맥락 정의 누락 — 누가 어떤 상황에서 쓰는지 전혀 없음
2. 핵심 기능 ↔ 목표 불일치 — 논리 모순이 있음
3. 정상 흐름 또는 예외 흐름 중 하나라도 완전히 누락

## PASS 처리 (improvements에만 기록)
- 정량 지표 부족 (예: "N초 이내" 없음)
- 상태 전이 세부사항 (예: "다시 시작 후 X가 선공인가")
- 완료 기준의 표현 방식
- 사용자 정의의 범위 확장 여부
- 기타 개선 제안

## 회차 규칙
- 1회차: 위 FAIL 기준 전체 검토
- 2~3회차: 이전 회차에서 지적한 FAIL 항목이 반영됐는지만 확인. 새 FAIL 항목 추가 금지.

## 절대 규칙
- 구현 방법(파일명·컴포넌트·라이브러리·색상·애니메이션)은 비평 대상 아님
- FAIL 기준 3가지 외의 이유로 FAIL 금지
- 칭찬 금지, 문제만 지적

## 출력 형식 (JSON만, 다른 텍스트 금지)
{"result": "PASS" or "FAIL", "issues": ["FAIL 사유 (FAIL 기준 번호 포함)"], "improvements": ["개선 제안"]}

PASS이면: {"result": "PASS", "issues": [], "improvements": ["개선 제안 (없으면 빈 배열)"]}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="기획서 비평 에이전트")
    parser.add_argument("--plan", required=True, help="plan.md 파일 경로")
    parser.add_argument("--round", type=int, default=1, help="비평 회차 (1~3)")
    args = parser.parse_args()

    plan_path = Path(args.plan)
    if not plan_path.exists():
        print(json.dumps({"error": f"파일 없음: {args.plan}"}), file=sys.stderr)
        return 2

    plan_text = plan_path.read_text(encoding="utf-8")

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content=f"현재 {args.round}회차입니다. 아래 기획서를 비평하세요.\n\n{plan_text}"
        ),
    ]

    try:
        response = llm.invoke(messages)
        raw = response.content.strip()

        if raw.startswith("```"):
            lines = raw.splitlines()
            raw = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        result = json.loads(raw)
    except Exception as e:
        # 실행 오류 시 수동 비평 모드로 전환 — planner가 직접 판단
        print(json.dumps({
            "result": "ERROR",
            "error": str(e),
            "fallback": "Python 스크립트 실행 오류. planner가 직접 기획서를 검토하세요.",
        }, ensure_ascii=False))
        return 2

    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("result") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
