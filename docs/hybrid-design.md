# Hybrid 설계

## 배경

Claude Code 하네스에서 에이전트는 모두 같은 Claude 모델 위에서 동작한다.
런타임은 하나고, `.md` 파일에 작성된 프롬프트가 역할을 결정하는 구조다.

이 구조에서 비평·리뷰 에이전트는 두 가지 문제를 가진다:

1. **왕복 비용**: 개발 에이전트 → 메인 → 리뷰어 → 메인 → 개발 에이전트. 메인을 두 번 거치면서 고정 토큰 비용이 반복 소모된다.
2. **단일 모델 편향**: 같은 Claude가 개발하고 리뷰하므로 blind spot이 생길 수 있다.

## 핵심 통찰

비평·리뷰의 입출력은 단순하다:
- 리뷰어: 변경 파일 내용 → 문제점 리스트
- 비평: plan.md 내용 → 문제점 리스트

이 정도는 Python 스크립트로 충분하다. 에이전트가 직접 `python agents/reviewer.py`를 호출하면 메인을 거치지 않아도 된다.

## 구현 방향

### reviewer.py

```
입력: --files <파일 경로 목록> --context <변경 맥락>
처리: LangChain + GPT-4o-mini로 코드 리뷰
출력: JSON { issues: [{ severity, file, line, message }] }
```

개발 에이전트가 tasks 완료 후 직접 실행:
```bash
python agents/reviewer.py --files src/auth.ts src/guard.ts
```

### critic.py

```
입력: --plan <plan.md 경로>
처리: LangChain + GPT-4o-mini로 기획서 분석
출력: JSON { result: PASS|FAIL, issues: [{ message }] }
```

기획 에이전트가 초안 작성 후 직접 실행:
```bash
python agents/critic.py --plan docs/plans/login/plan.md
```

## 스킬 변경

### /dev Step 3 (리뷰)

기존: 리뷰어 Claude 서브에이전트 호출
변경: 개발 에이전트 내부에서 `python agents/reviewer.py` 실행 → 피드백 직접 수신 → 수정

### /planning Step 4 (비평)

기존: 비평 Claude 서브에이전트 호출
변경: 기획 에이전트 내부에서 `python agents/critic.py` 실행 → 피드백 직접 수신 → 수정

## 에이전트 md 처리

- `reviewer.md`, `critic.md` → 삭제 (Python으로 대체)
- `developer.md` → Step 3 지침을 "reviewer.py 실행 후 피드백 반영"으로 수정
- `planner.md` → Step 4 지침을 "critic.py 실행 후 피드백 반영"으로 수정

## 향후 확장

- 모델 교체: `reviewer.py`에서 GPT → Gemini 등으로 쉽게 변경 가능
- 팀 기능 조합: Claude 팀 에이전트 + Python 스크립트 병렬 실행으로 교차 검증
- 비용 측정: Python 호출 비용 vs Claude 서브에이전트 비용 실측 비교
