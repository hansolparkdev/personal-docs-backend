---
name: planning
description: 기획 에이전트 + 비평 에이전트로 plan.md 작성. 사용법 /planning {기능명}
---

기획 에이전트와 비평 에이전트를 활용해 기획서를 작성합니다.

## Step 1: feature 이름 추출

- 입력: `$ARGUMENTS` (예: "로그인 기능")
- {feature}: 영문 소문자·하이픈으로 변환 (예: `login`, `user-profile`)

## Step 2: 구조 감지

루트 `CLAUDE.md`에서:
- `STRUCTURE` = `프로젝트 타입` 값 (frontend | backend | fullstack | monorepo)
- `PACKAGES` = 모노레포면 `워크스페이스 구조`의 apps/* 목록

**CLAUDE.md가 없으면** → `/init` 먼저 실행하라고 유저에게 안내 후 중단.

## Step 2.5: 디자인 참조 확인 (frontend/fullstack/monorepo만)

유저에게 한 번에 묻는다:

```
참조 디자인이 있나요? 있으면 둘 다 답해주세요.

1) 소스 (택1 또는 조합):
   - stitch:projects/<id>
   - figma:<url>
   - docs/design/{feature}/ 같은 로컬 경로
   - 스크린샷 첨부
   - none (없음)

2) 충실도 (택1):
   - strict  — 원본대로 그대로 맞춤 (원본 우선)
   - guide   — 톤·구조만 참고, 충돌 시 프로젝트 원칙 우선
   - loose   — 느슨한 참고용
   - none    — 참조 없음
```

답을 받을 때까지 Step 3로 진행하지 않는다.

- `DESIGN_REF` = 사용자가 준 소스 값 (없으면 `none`)
- `DESIGN_FIDELITY` = 사용자가 준 충실도 (없거나 `DESIGN_REF = none`이면 `none`)

## Step 3: 기획 + 비평 (planner 호출)

planner 에이전트를 호출한다. 비평 루프는 planner 내부에서 직접 실행하므로 SKILL에서 별도 실행하지 않는다.

전달 변수:
- `FEATURE`: {feature}
- `REQUIREMENT`: `$ARGUMENTS` 원문
- `STRUCTURE`: 위에서 추출
- `PACKAGES`: 모노레포만
- `PLAN_PATH`: `docs/plans/{feature}/plan.md`
- `DESIGN_REF`: Step 2.5에서 확정
- `DESIGN_FIDELITY`: Step 2.5에서 확정

planner가 plan.md 저장 + 비평 루프(최대 3회)까지 완료하고 결과를 반환한다.

## Step 4: 완료 안내

```
✓ plan.md 저장 ({비평 결과: PASS 또는 경고})

다음 단계:
- /spec {feature}  — 스펙 생성 (plan.md 기반 capability 스펙 산출)
- /dev {feature}   — 스펙 생성 완료 후 전체 슬라이스 개발
```

## 참고
디자인 필요하면 plan.md 내용을 Google Stitch에 입력. 결과물(stitch-prompt.md, ui.png)은 docs/design/{feature}/ 에 유저가 직접 저장.
