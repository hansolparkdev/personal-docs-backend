# 개발 흐름

## 작업 트랙

| 종류 | 트랙 | 호출 |
|------|------|------|
| 새 기능 | SDD 풀 루프 | `/planning` → `/spec` → `/dev` |
| 기존 스펙 변경 | 스펙 변경 | `/spec "요구사항"` → `/dev` |
| 기존 스펙 제거 | 스펙 제거 | `/spec --remove "대상"` → `/dev` |
| 버그 | 바로 수정 + 커밋 | `fix(scope):` |
| 리팩터 | 바로 수정 + 커밋 | `refactor(scope):` |
| 인프라/스캐폴딩 | `docs/setup.md` Step 누적 | 직접 |

## SDD 산출물 위치

```
docs/plans/<feature>/plan.md
docs/specs/changes/<feature>/
  ├── proposal.md
  ├── design.md
  ├── tasks.md
  └── specs/<capability>/spec.md
docs/specs/main/<capability>/spec.md
docs/specs/archive/YYYY-MM-DD-<feature>/
```

## 역할 (/dev 담당 에이전트)

| 역할 | 담당 |
|------|------|
| 개발 에이전트 | TDD 구현 + 단위/RTL 테스트 + 커버리지 |
| 리뷰어 | 코드 품질 + 금지 패턴 + 런타임 검증 |
| 테스터 | E2E 선별 + 보안 검증 |

전체 에이전트(기획·비평·아키텍트 포함)는 `.claude/agents/` 참조.

## 개념 문서

새 패턴/라이브러리/보안 결정 시 `docs/concepts/`에 작성.
포맷: 한 줄 정의 / 왜 필요한가 / 표준 근거 / 우리 구조 위치 / 대안 trade-off / 참고 자료.

## 실패 시

실패 → 대안 시도 → 전부 실패 시 유저 보고. 바로 중단 금지.
