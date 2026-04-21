---
name: init
description: 프로젝트 초기화. 소스 분석 또는 인터뷰로 CLAUDE.md + docs/rules/ 생성. 사용법 /init
---

프로젝트의 CLAUDE.md와 docs/rules/를 생성합니다. 스캐폴딩은 하지 않습니다.

## Step 1: 소스 탐지

하네스 파일(`.claude/`, `docs/rules/`, `agents/`, `setup.sh`, `requirements.txt`)을 제외하고 실제 프로젝트 소스가 있는지 확인한다.

**소스 있음** 판단 기준 (하나라도 해당):
- `package.json` / `pyproject.toml` / `go.mod` / `Cargo.toml` 존재
- `src/` / `app/` / `lib/` 디렉토리 존재
- `turbo.json` / `nx.json` / `pnpm-workspace.yaml` 존재

소스 있음 → Step 2A (분석 모드)
소스 없음 → Step 2B (인터뷰 모드)

---

## Step 2A: 분석 모드 (소스 있을 때)

아래 항목을 코드베이스에서 직접 읽어 감지한다.

### 감지 항목
- **프로젝트 타입**: turbo.json/nx.json → monorepo, Next.js → fullstack, React/Vue/Svelte → frontend, Express/FastAPI/NestJS → backend
- **언어·프레임워크**: package.json `dependencies` / pyproject.toml
- **패키지 매니저**: `pnpm-lock.yaml` → pnpm, `yarn.lock` → yarn, `package-lock.json` → npm, `poetry.lock` → poetry
- **단위 테스트**: package.json `devDependencies`에서 vitest/jest/pytest 탐지
- **E2E**: `@playwright/test` / `cypress` 탐지
- **UI 라이브러리**: `tailwindcss` / `@mui` / `shadcn` 탐지
- **DB**: `prisma` / `typeorm` / `sqlalchemy` / `drizzle` 탐지
- **테스트 폴더**: `tests/` / `__tests__/` / `src/**/*.test.*` 패턴 탐지
- **개발 서버 명령**: package.json `scripts.dev` 또는 `scripts.start`
- **테스트 명령**: package.json `scripts.test`
- **커버리지 명령**: package.json `scripts.coverage` 또는 `scripts.test:coverage`

감지 후 불명확한 항목만 유저에게 한 번에 확인:

```
감지 결과 확인해주세요. 모르면 엔터.

- 단위 테스트 명령: {감지값 또는 "?"}
- 커버리지 명령: {감지값 또는 "?"}
- DB: {감지값 또는 "없음"}
```

확인 받은 뒤 Step 3으로.

---

## Step 2B: 인터뷰 모드 (소스 없을 때)

한 번에 모든 걸 묻지 않는다. 답변에 따라 필요한 것만 추가로 묻는다.

**질문 1 — 프로젝트 타입:**
```
어떤 프로젝트입니까?

1. 단일 프론트엔드 (React/Vue/Svelte 등)
2. 단일 백엔드 (Express/FastAPI/NestJS 등)
3. 풀스택 단일 (Next.js App Router 등)
4. 모노레포 (Turborepo / Nx)
```

**질문 2 — 스택 (타입 답변 후):**
```
스택을 알려주세요. (모르는 항목 엔터)

- 언어·프레임워크:
- 패키지 매니저 (npm/pnpm/poetry/...):
- 단위 테스트 (Vitest/Jest/pytest/...):
```

**질문 3 — 타입별 추가 질문:**
- 프론트 포함(1/3/4): `E2E (Playwright/없음):` + `UI 라이브러리 (Tailwind/shadcn/MUI/없음):`
- 백엔드 포함(2/3/4): `DB (PostgreSQL/SQLite/없음):`
- 모노레포(4): `apps/ 목록:` + `packages/ 목록:`

답변 완료 후 Step 3으로.

---

## Step 3: CLAUDE.md 생성

감지/인터뷰 결과로 루트에 CLAUDE.md 작성.

```markdown
# CLAUDE.md

## 프로젝트 타입

{frontend | backend | fullstack | monorepo}

## 기술 스택

- 언어·프레임워크: {값}
- 패키지 매니저: {값}
- 단위 테스트: {값}
- E2E: {값 — 프론트 계열만}
- UI 라이브러리: {값 — 프론트 계열만}
- DB: {값 — 백엔드 계열만}

## 아키텍처

- 테스트 폴더: {위치}

## 개발 서버

{명령}

## 단위 테스트 명령

- 전체: {명령}
- 커버리지: {명령}

## E2E 명령 (프론트 계열만)

- 로컬: {명령} --headed
- CI: {명령}

## 보안 스캔

{npm audit / pip-audit / ...}

## 참조 문서

| 주제 | 문서 |
| --- | --- |
| 금지 패턴 | [docs/rules/forbidden-patterns.md](docs/rules/forbidden-patterns.md) |
| 폴더 규약 | [docs/rules/folder-conventions.md](docs/rules/folder-conventions.md) |
| 명령어 | [docs/rules/commands.md](docs/rules/commands.md) |
| 에이전트 워크플로우 | [docs/rules/dev-workflow.md](docs/rules/dev-workflow.md) |
| SDD 트랙 | [docs/rules/dev-flow.md](docs/rules/dev-flow.md) |
```

모노레포면 루트 CLAUDE.md 생성 후 `apps/*`, `packages/*`별로 단일 프로젝트 형식 CLAUDE.md 추가 생성.

---

## Step 4: docs/rules/ 생성

`docs/rules/` 없으면 생성.

**분석 모드**: 코드베이스 읽어서 초안 작성.
- `forbidden-patterns.md`: 실제 코드에서 안티패턴 탐지 후 금지 항목 등재. 발견 안 된 것도 스택 기반으로 추가.
- `folder-conventions.md`: 실제 폴더·파일 구조 역산해서 현재 규약 기술.
- `commands.md`: package.json / pyproject.toml / Makefile에서 실제 스크립트 추출.

**인터뷰 모드**: 플레이스홀더로 기본 틀만 생성 (유저가 채울 것).

두 모드 공통 — `dev-workflow.md`, `dev-flow.md`는 이미 있으면 덮어쓰지 않는다.

---

## Step 5: 완료 안내

```
✓ CLAUDE.md 생성 ({분석 모드 | 인터뷰 모드})
✓ docs/rules/ ({분석: 자동 작성 | 인터뷰: 플레이스홀더})

다음 단계:
- /planning {기능명}  — 기획서 작성
- /spec {기능명}      — 스펙 생성
```

## 규칙

- 스캐폴딩·패키지 설치 금지 — 이 스킬은 문서만 생성한다
- 기존 CLAUDE.md 있으면 덮어쓰기 전에 유저 확인
- 감지 불명확한 항목만 유저에게 질문 — 전부 다 묻지 않는다
- 실패 시 즉시 유저 보고 후 중단
