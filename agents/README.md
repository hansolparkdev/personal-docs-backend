# agents/

Claude 서브에이전트 대신 외부 모델(GPT-4o-mini)을 직접 호출하는 Python 스크립트.
토큰 비용 절감 + 에이전트 내부 루프 소유 목적.

## 스크립트

| 파일 | 역할 | 호출자 | 모델 |
|------|------|--------|------|
| `critic.py` | 기획서 비평 — FAIL 기준 3가지만 판정 | planner 에이전트 | gpt-4o-mini |
| `reviewer.py` | 코드 리뷰 — 금지 패턴 위반 탐지 | developer 에이전트 | gpt-4o-mini |

## 출력 형식

**critic.py**
```json
{"result": "PASS"|"FAIL"|"ERROR", "issues": ["..."], "improvements": ["..."]}
```

**reviewer.py**
```json
{"result": "PASS"|"FAIL"|"ERROR", "issues": [{"severity": "P0"|"P1", "file": "...", "message": "..."}]}
```

종료 코드: `0` = PASS, `1` = FAIL, `2` = ERROR

## 오류 처리

`result: ERROR` 반환 시 호출한 에이전트가 직접 수동 판단 후 진행.

## 설치

```bash
bash setup.sh
```

`.env`에 `OPENAI_API_KEY` 설정 필요.

## 모델 변경

`critic.py` / `reviewer.py`의 `ChatOpenAI(model=...)` 한 줄만 수정.
