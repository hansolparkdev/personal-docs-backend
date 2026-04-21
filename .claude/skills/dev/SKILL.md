---
name: dev
description: 단일 feature를 개발·리뷰·테스트·아카이브까지 처리. 커밋은 하지 않음(사용자 명시 승인 후 별도). 사용법 /dev {feature}
---

단일 feature의 개발부터 아카이브까지 처리. 커밋은 사용자 명시 승인 후 별도.

## 사전 조건
- `docs/specs/changes/<feature>/` 존재 (없으면 `/spec` 먼저)
- 루트 `CLAUDE.md` 존재

## Step 0: 재개 지점 판별

```
tasks.md 읽고 체크박스 상태 확인:
- 전부 [x]      → 개발 건너뛰고 Step 3 (리뷰)로
- 일부 [x]      → 개발 이어서 진행 (미완료 task부터)
- 전부 [ ]      → 처음부터 개발
```

추가 판별: `.status` 파일 존재 시 `reviewed` → Step 4, `tested` → Step 5.

## Step 1: 컨텍스트 로드

- `FEATURE` = `$ARGUMENTS`
- proposal.md `## Meta`에서 `type`, `package` 추출
- proposal.md `## Capabilities`에서 영향 capability 목록 추출
- tasks.md에서 작업 목록
- `docs/specs/changes/<feature>/specs/` 하위 **모든 capability의 spec.md**를 읽어 SCENARIOS로 병합 (capability 폴더 알파벳순)
- CLAUDE.md에서 STACK 추출
- `docs/plans/<feature>/plan.md` 존재 시 UX_POINTS 추출 (frontend만. Mode 2/3은 plan 없을 수 있음 — 없으면 UX_POINTS 빈값)

## Step 2: 개발 에이전트 호출

전달: FEATURE, PACKAGE, TYPE, STACK, UX_POINTS, SCENARIOS, TASKS_PATH

tasks.md 순서대로 TDD 진행. spec 시나리오는 단위/RTL 테스트 검증 기준.

개발 에이전트 착수 전 필수 프리로드: `forbidden-patterns.md`, `folder-conventions.md`, `docs/rules/dev-workflow.md`

`.status`에 `developed` 기록.

## Step 3: 리뷰 (1회)

리뷰는 developer.md 내부에서 직접 실행하므로 SKILL에서 별도 호출하지 않는다. developer 에이전트가 완료 후 리뷰 결과를 반환한다.

**런타임 기동 검증 필수** (CLAUDE.md §금지 패턴 + docs/rules/dev-workflow.md).

- PASS → `reviewed` 기록 → Step 4
- FAIL → 피드백 유저에게 출력 + 유저 개입 대기 (재시도 시 `리뷰만 재실행해줘`)

## Step 4: 테스터 호출

전달: FEATURE, PACKAGE, TYPE, STACK, SCENARIOS

테스터가 E2E 대상 선별 + 보안 검증.

- PASS → `tested` 기록 → Step 5
- FAIL → 유저 보고 후 중단

## Step 5: Sync

```
docs/specs/changes/<feature>/specs/<capability>/spec.md
  → docs/specs/main/<capability>/spec.md

ADDED → 추가 (파일 없으면 생성)
MODIFIED → ### Requirement: {name} 블록 단위 덮어쓰기
REMOVED → 블록 삭제
순서: REMOVED → MODIFIED → ADDED
```

다중 capability면 capability별로 순차 Sync.

## Step 6: Archive

```
docs/specs/changes/<feature>/
  → docs/specs/archive/YYYY-MM-DD-<feature>/
```

원본 폴더 삭제. `.status`도 함께 이동.

## Step 7: 완료 리포트

```
✓ <feature> 아카이브까지 완료 (커밋 안 함)

- 개발: 태스크 N/N
- 리뷰: R회차 PASS
- 테스트: E2E N/N PASS, 보안 critical N / high N
- 커버리지: 라인 XX% / 브랜치 XX% / 함수 XX%
- 아카이브: docs/specs/archive/YYYY-MM-DD-<feature>/

다음 중 선택:
- 내용 확인 후 커밋 원하면: "커밋해줘"
- 다음 feature
```

## 재진입 특수 모드
- `sync만 실행해줘` → Step 5만
- `테스트만 재실행해줘` → Step 4부터
- `리뷰만 재실행해줘` → Step 3부터

## 규칙
- **커밋 금지**: 사용자 명시 승인 후 별도.
- 리뷰어 런타임 검증 필수.
- E2E는 headed 기본 (CI=1 우회 금지).
- 다중 capability spec은 알파벳순 병합.
- 실패 시 `.status`로 단계 기록 → 재호출 시 이어서 진행.
