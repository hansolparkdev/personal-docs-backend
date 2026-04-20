# AI 개발 워크플로우 하네스 설계

## 개요

하네스 = 에이전트 행동을 강제하는 구조

강제 방법은 크게 두 가지:
1. **훅** - 코드 레벨에서 실행을 차단/허용
2. **에이전트 역할 + 출력 강제** - 시스템 프롬프트와 출력 형식으로 제어

---

## 1. Claude Code 훅

### 역할
Claude가 파일을 수정하기 **전**에 가로채서 검사.
위반 시 즉시 차단 → Claude가 방향을 바꿈.

### 언제 써야 하나
- Claude가 자율적으로 많은 파일을 수정할 때
- 잘못된 패턴이 퍼지기 전에 막고 싶을 때
- 빌드 사이클이 느려서 빠른 피드백이 필요할 때

### 설정

**settings.json:**
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/pre_edit.sh"
          }
        ]
      }
    ]
  }
}
```

**.claude/hooks/pre_edit.sh:**
```bash
FILE=$(echo $TOOL_INPUT | jq -r '.file_path')

if [[ "$FILE" == *".ts"* || "$FILE" == *".tsx"* ]]; then
  npx eslint $FILE
fi

exit $?
```

### 핵심 원칙
- **훅은 실행기만** — 복잡한 로직은 ESLint에 위임
- **규칙은 .eslintrc에** — 훅은 손대지 않아도 됨
- **테스트는 훅에서 돌리지 않음** — 파일마다 실행되어 무한루프 위험

### ESLint 규칙 예시
```js
// .eslintrc
{
  "rules": {
    "no-explicit-any": "error",
    "no-console": "error",
    "no-restricted-syntax": [
      "error",
      {
        "selector": "CallExpression[callee.name='useEffect'] CallExpression[callee.name='fetch']",
        "message": "useEffect에서 fetch 직접 사용 금지. react-query 또는 SWR 사용하세요."
      }
    ],
    "no-restricted-imports": [
      "error",
      {
        "name": "axios",
        "message": "axios 직접 사용 금지. apiClient 사용하세요."
      }
    ]
  }
}
```

---

## 2. Pre-commit 훅 (Husky + lint-staged)

### 역할
git commit 시도 시 가로채서 검사.
사람과 Claude 둘 다 적용되는 **최종 게이트**.

### 설정

```bash
npm install --save-dev husky lint-staged
npx husky init
```

**.husky/pre-commit:**
```bash
npx lint-staged
```

**package.json:**
```json
{
  "lint-staged": {
    "*.{ts,tsx}": [
      "eslint --fix",
      "prettier --write"
    ],
    "*.{css,scss}": [
      "stylelint --fix"
    ]
  }
}
```

### 핵심 원칙
- 수정된 파일만 검사 (lint-staged)
- 전체 테스트는 여기서 돌리지 않음 → `/dev` 스킬의 테스터 에이전트가 담당

---

## 두 훅의 역할 비교

| | Claude Code 훅 | Pre-commit 훅 |
|--|---------------|--------------|
| 시점 | Claude가 파일 수정할 때 | git commit 할 때 |
| 대상 | Claude 행동 제어 | 사람 + Claude 둘 다 |
| 도구 | settings.json | Husky + lint-staged |
| 목적 | 개발 중 빠른 피드백 | 커밋 전 최종 보장 |

```
Claude가 파일 수정
→ [Claude Code 훅] ESLint 즉시 피드백

git commit
→ [pre-commit 훅] 최종 게이트
```

---

## 3. 나머지는 에이전트로

훅으로 강제하기 어려운 것들 — 워크플로우, 순서, 품질, 검증 — 은
**에이전트 역할과 출력 형식으로 강제**합니다.

### 워크플로우 강제 (CLAUDE.md + 스킬)

```
새 기능은 반드시 아래 순서로 진행:
1. /planning  — 기획서 작성 (기획 에이전트 + 비평 에이전트)
2. /spec      — 스펙 산출 (아키텍트 에이전트)
3. /dev       — 개발·리뷰·테스트·아카이브 자동 수행
```

### 출력 형식 강제 (에이전트 시스템 프롬프트)

각 에이전트는 고정 출력 형식을 강제합니다. 예시:

```markdown
결과: PASS | FAIL
금지 패턴: N건 위반
런타임: error 0 / warning 0
```

### 피드백 루프 (오케스트레이터 = 메인 Claude)

```
메인 Claude (오케스트레이터)
      ↓
개발 에이전트 (서브) — TDD 구현
      ↓
리뷰어 에이전트 (서브) → FAIL → 유저 개입
                       → PASS → 테스터 에이전트
                                    ↓
                               PASS → 아카이브
```

---

## 4. CI 게이트 (Continuous Integration)

**"내 코드가 기존 소스와 안전하게 결합되는가?"**

PR 생성 시 GitHub이 자동 감지하여 실행.
실패하면 머지 버튼 잠김.

### 작성 위치
```
.github/workflows/ci.yml
```

### 예시
```yaml
name: CI

on:
  pull_request:
    branches: [main]   # PR 생성 시 자동 실행

jobs:
  gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4

      - name: Type Check
        run: npx tsc --noEmit

      - name: Lint
        run: npx eslint .

      - name: Unit Test
        run: npm test -- --coverage

      - name: Security Scan
        run: npm audit --audit-level=high

      - name: E2E Smoke Test
        run: npx playwright test --grep @smoke
```

### 핵심
- 코드 레벨 검사 (실제 배포 없음)
- 머지 **전에** 실행 → 문제있으면 차단
- push 방식으로 직접 머지하면 머지 후 실행 → 차단 불가

---

## 5. CD 게이트 (Continuous Deployment)

**"합쳐진 코드가 실제 환경에서 동작하는가?"**

main 머지 후 자동 실행. 스테이징에 실제 배포 후 검증.

### 작성 위치
```
.github/workflows/cd.yml
```

### 예시
```yaml
name: CD

on:
  push:
    branches: [main]   # main 머지 후 자동 실행

jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy Staging
        run: ./scripts/deploy.sh staging

      - name: E2E Full Test
        run: npx playwright test
        env:
          BASE_URL: https://staging.yourapp.com

      - name: Lighthouse CI
        run: npx lhci autorun

  deploy-production:
    needs: deploy-staging   # 스테이징 통과 후에만
    environment: production # 수동 승인 게이트
    steps:
      - name: Deploy Production
        run: ./scripts/deploy.sh production
```

### 핵심
- 실제 스테이징 서버에 배포 후 검사
- CI와 달리 실제 DB/API 연동 상태 확인
- 프로덕션은 수동 승인 필수

---

## 6. 브랜치 보호 규칙

main 직접 push를 구조적으로 차단.

```
GitHub Settings → Branches → Branch protection rules
└── main
    ├── Require pull request before merging  ← 직접 push 차단
    ├── Require status checks                ← CI 통과 필수
    └── Require approvals                    ← 승인자 수 설정 (팀 작업 시)
```

---

## 전체 게이트 레이어

```
로컬 개발
├── Claude Code 훅    → 파일 수정 시 ESLint 즉시 피드백
└── Pre-commit 훅     → 커밋 시 린트/포맷 최종 보장

PR/머지
├── 브랜치 보호 규칙  → main 직접 push 차단
├── CI 게이트         → 머지 전 타입/테스트/보안 검사
└── CD 스테이징       → 머지 후 실환경 동작 검증

배포
└── CD 프로덕션       → 수동 승인 후 실배포
```

각 게이트는 이전 게이트가 못 잡은 것을 잡는 구조.

---

## 에이전트 (역할/출력 강제)

훅으로 강제하기 어려운 것들 — 워크플로우, 순서, 품질 — 은
에이전트 역할과 출력 형식으로 강제.

```
CLAUDE.md  → 워크플로우 순서 강제
스킬       → /planning /spec /dev
에이전트   → 역할별 출력 형식 강제
```
