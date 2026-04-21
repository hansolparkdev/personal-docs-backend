---
name: spec
description: plan.md 기반 새 기능 스펙 생성, 또는 기존 스펙 변경/제거. 사용법 /spec {feature 또는 변경 요구사항}
---

## 모드 판별

/spec <arguments> 호출 시:
- `docs/plans/<arguments>/plan.md` 존재 → **Mode 1** (새 기능)
- 미존재 → `docs/specs/main/` 존재 여부 확인
  - 존재 → **Mode 2** (변경) 또는 **Mode 3** (`--remove` 포함 시 제거)
  - 미존재 → "기존 스펙 없음. /planning 먼저" 안내 후 중단

---

## Mode 1: 새 기능 (plan.md 기반)

### 사전 조건
- `docs/plans/<arguments>/plan.md` 존재
- 루트 `CLAUDE.md` 존재

### Step 1: 컨텍스트 추출
- `STRUCTURE`, `PACKAGES_LIST`, `STACK_MAP` from CLAUDE.md
- `EXISTING_CAPABILITIES` = `docs/specs/main/` 하위 폴더 목록

### Step 2: 아키텍트 호출 (Mode 1)
전달 변수: FEATURE, STRUCTURE, PACKAGES, STACK, EXISTING_CAPABILITIES, MODE=1

아키텍트가 plan.md 읽고 feature 폴더 생성:

```
docs/specs/changes/<feature>/
├── proposal.md
├── design.md
├── tasks.md
└── specs/
    ├── <capability-1>/spec.md
    └── <capability-2>/spec.md
```

### Step 3: 산출물 구조 검증

아키텍트 완료 후 아래 항목을 순서대로 검증. 하나라도 실패하면 아키텍트 재호출.

**파일 존재 확인**
- [ ] `docs/specs/changes/<feature>/proposal.md` 존재
- [ ] `docs/specs/changes/<feature>/design.md` 존재
- [ ] `docs/specs/changes/<feature>/tasks.md` 존재
- [ ] `docs/specs/changes/<feature>/specs/` 하위 spec.md 1개 이상 존재

**proposal.md 필드 확인**
- [ ] `## Meta` 섹션 존재
- [ ] `feature:` 필드 존재
- [ ] `type:` 필드 존재 (frontend | backend | fullstack)
- [ ] `package:` 필드 존재

**tasks.md 필드 확인**
- [ ] 각 task에 `수정 파일:` 필드 존재

**spec.md 포맷 확인**
- [ ] `## ADDED Requirements` / `## MODIFIED Requirements` / `## REMOVED Requirements` 중 하나 이상 존재
- [ ] 각 Scenario에 Given/When/Then 존재

검증 통과 후 유저 보고:

```
✓ 스펙 생성 완료

feature: <feature>
specs:
- <capability-1>/spec.md (ADDED)
- <capability-2>/spec.md (MODIFIED)

다음 단계: /dev <feature>
```

---

## Mode 2: 스펙 변경

### 사전 조건
- `docs/specs/main/` 하위에 기존 스펙 존재
- `<arguments>`는 변경 요구사항 텍스트

### Step 1: 아키텍트 호출 (Mode 2)
전달 변수: REQUIREMENT_TEXT=<arguments>, EXISTING_CAPABILITIES, MAIN_SPECS_PATH=docs/specs/main/, STACK, MODE=2

아키텍트가 `docs/specs/main/` 하위 모든 spec.md를 읽고 영향 Requirement 식별 후 산출물 생성.

### Step 2: 유저에게 변경 영향 보고

```
✓ 스펙 변경 산출물 생성

change: <change-name>
영향 Requirement:
- <capability>/<requirement-name> (MODIFIED)

다음 단계: /dev <change-name>
```

---

## Mode 3: 스펙 제거

Mode 2와 동일하되 `--remove` 포함. 아키텍트에 MODE=3 전달. proposal에 REMOVED 마킹.

```
✓ 스펙 제거 산출물 생성

change: <change-name>
제거 Requirement:
- <capability>/<requirement-name> (REMOVED)

다음 단계: /dev <change-name>
```

---

## 규칙
- 이 스킬은 스펙 생성만. 개발은 `/dev`가 담당.
- Mode 1은 plan.md 이외 파일 재편집 금지.
- Mode 2/3은 `docs/specs/main/` 읽기만. 직접 수정은 `/dev` Sync에서.
