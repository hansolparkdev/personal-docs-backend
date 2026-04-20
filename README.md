# claude-code-harness-hybrid

**Claude Code의 서브에이전트 시스템과 외부 Python 에이전트를 혼합(hybrid)해 토큰 비용과 컨텍스트 오염을 줄이는 하네스 구조.**

> **Status**: Experimental (v0.1)
> **Base**: [claude-harness](https://github.com/hansolparkdev/claude-harness) v1에서 리뷰어·비평가를 Python으로 분리한 v2 구조
> **Dependencies**: Python 3.10+, LangChain, OpenAI API (GPT-4o-mini)

Claude Code 하네스에 Python 기반 외부 모델(GPT-4o-mini 등)을 혼합한 하이브리드 에이전트 워크플로우.

## 핵심 아이디어

기존 하네스는 모든 에이전트를 Claude 서브에이전트로 실행합니다. 매번 서브에이전트를 열면 시스템 프롬프트·툴 정의 등 고정 비용(측정 결과 약 17k 토큰)이 반복 소모되고, 메인 컨텍스트를 거치는 왕복 구조가 토큰 낭비와 컨텍스트 오염을 유발합니다.

**비평·리뷰처럼 입출력이 단순한 역할**은 Python 스크립트로 분리해 에이전트 내부에서 직접 호출합니다. 메인을 거치지 않으므로 왕복이 사라지고, Claude 고정 비용 없이 더 저렴한 모델로 처리할 수 있습니다.

## 구조 변경

**기존**
```
개발 에이전트 → 메인 → 리뷰어 에이전트 → 메인 → 개발 에이전트
기획 에이전트 → 메인 → 비평 에이전트  → 메인 → 기획 에이전트
```

**개선**
```
개발 에이전트 → python agents/reviewer.py → 피드백 → 내부 수정
기획 에이전트 → python agents/critic.py  → 피드백 → 내부 수정
```

## 분리 기준

**Python으로 분리한 역할** (입출력 단순, 결정적 검증 비중 큼):
- `critic`: plan 텍스트를 받아 PASS/FAIL 판정
- `reviewer`: CHANGED_FILES를 받아 PASS/FAIL + 이슈 목록 반환

**Claude 서브에이전트로 유지** (파일 시스템 조작·다단계 추론·도구 다수 사용):
- `planner`: 사용자와 대화하며 plan 작성
- `architect`: 스펙 4파일(proposal/design/tasks/spec) 생성
- `developer`: 다수 파일 수정 + TDD 사이클
- `tester`: E2E 시나리오 선별 + Playwright 실행

분리 기준은 **"입력과 출력이 단순한가"** 와 **"Claude Code 내장 도구(Read/Write/Bash 등)에 의존하는가"** 이다.

## 트레이드오프

| | 기존 | 개선 |
|--|------|------|
| 리뷰·비평 토큰 | Claude 고정비용 매번 | Python 호출, 고정비용 없음 |
| 메인 컨텍스트 | 왕복마다 오염 | 보호됨 |
| 피드백 정확도 | 메인이 리뷰를 재해석해 개발자에게 전달 | 개발자가 리뷰 원문(JSON)을 직접 수신 |
| 모델 다양성 | Claude 단일 | GPT-4o-mini 등 교차 검증 |
| 의존성 | 없음 | Python 환경 필요 |

## 구성

```
.claude/
  agents/
    developer.md      Claude 서브에이전트 (TDD 구현)
    planner.md        Claude 서브에이전트 (기획서 작성)
    architect.md      Claude 서브에이전트 (스펙 산출)
    tester.md         Claude 서브에이전트 (E2E)
  skills/
    dev/SKILL.md      리뷰어 호출을 python으로 변경
    planning/SKILL.md 비평 호출을 python으로 변경

agents/               Python 에이전트
  reviewer.py         GPT-4o-mini 기반 코드 리뷰
  critic.py           GPT-4o-mini 기반 기획서 비평

docs/
  hybrid-design.md    설계 상세
  harness.md          훅·에이전트 설계 개념
  rules/              워크플로우 규율
```

### 외부 모델 선택

Python 에이전트는 **GPT-4o-mini**를 기본으로 사용한다. 선택 근거:

1. **비용**: Claude Sonnet 대비 입력 토큰 기준 약 10배 저렴
2. **교차 검증**: Claude가 작성한 코드·기획서를 다른 프로바이더로 검증해 단일 모델 편향을 줄임
3. **속도**: 비평·리뷰의 단순 판정에는 충분한 품질, latency 낮음

모델 교체는 환경변수 또는 설정 파일로 가능하도록 설계한다.

## 워크플로우

```
/planning → 기획 에이전트 → critic.py → 피드백 반영 → plan.md
/spec     → 아키텍트 에이전트 → 스펙 산출
/dev      → 개발 에이전트 → reviewer.py → 피드백 반영 → 완료
```

자세한 설계는 [docs/hybrid-design.md](docs/hybrid-design.md) 참조.
