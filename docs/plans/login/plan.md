# 기획서: login

## Meta
- type: feature
- package: backend

## Problem

### 사용자 및 맥락
- **주 사용자**: 자신의 문서를 업로드·검색하려는 개인 로그인 사용자.
- **보조 사용자**: 보호된 API를 호출해야 하는 프론트엔드 SPA 클라이언트.
- **맥락**: 사용자가 브라우저에서 `/login` 화면을 열어 ① 이메일·비밀번호 폼으로 직접 가입·로그인하거나 ② "Keycloak 계정으로 계속하기" 버튼으로 Keycloak 페이지에서 가입·로그인한다. 어느 경로든 JWT를 발급받아 파일 관리·RAG 챗 API를 호출한다.

### 문제
personal-docs 서비스는 사용자별 데이터 격리가 필수다. 인증 서버(Keycloak)가 별도 운영되므로 프론트가 client_secret·realm 설정을 직접 다루면 시크릿이 브라우저에 노출된다. 또한 두 가입 경로(id/password, SSO)를 통해 유입된 사용자가 모두 백엔드 DB에 존재해야 파일·챗 데이터와 연결할 수 있는데, SSO 경로는 백엔드를 거치지 않으므로 첫 로그인 시 DB 레코드 자동 생성 메커니즘이 없다.

## Goals
- 불특정 다수가 id/password로 회원가입하고 로그인할 수 있다.
- SSO(Keycloak 페이지)로 가입·로그인한 사용자도 첫 로그인 시 백엔드 DB에 자동으로 users 레코드가 생성된다.
- 만료된 access_token을 refresh_token으로 갱신할 수 있다.
- 유효한 access_token으로 현재 로그인 사용자 정보를 조회할 수 있다.
- 다른 API 라우터가 공통 JWT 검증 의존성을 재사용할 수 있다.
- Swagger UI에서 Bearer 토큰으로 보호된 엔드포인트를 테스트할 수 있다.

## Non-goals
- 비밀번호 재설정·이메일 검증 (Keycloak이 관리).
- 소셜 로그인(Google, GitHub 등) 연동.
- 토큰 블랙리스트 / 강제 로그아웃 서버사이드 세션 관리.
- 역할(Role)·권한(Permission) 기반 인가 정책.
- 관리자용 사용자 목록 조회·계정 정지.

## Capabilities

1. **id/password 회원가입** — username·email·password를 받아 Keycloak Admin API로 유저 생성 + 백엔드 DB `users` 테이블에 레코드 생성 (keycloak_sub 연결).
2. **토큰 발급** — username/password → Keycloak password grant → access_token·refresh_token 반환. 백엔드 DB에 users 레코드 없으면 자동 생성(upsert).
3. **SSO 콜백** — Keycloak이 authorization code를 콜백 URL로 전달 → 백엔드가 token 교환 → DB users upsert → 토큰 반환.
4. **토큰 갱신** — refresh_token → Keycloak refresh grant → 새 토큰 반환.
5. **현재 사용자 조회** — Bearer 토큰 검증 → JWT 클레임에서 사용자 정보(id, username, email) 반환.
6. **공통 인증 의존성** — `get_current_user` FastAPI 의존성. 다른 라우터가 재사용.
7. **Keycloak 연동 설정** — URL·realm·client_id·client_secret 환경변수 관리.
8. **OpenAPI 보안 스키마** — Swagger UI BearerAuth securityScheme.
9. **인증 실패 처리** — 자격증명 오류·만료 토큰·Keycloak 장애를 구분된 HTTP 상태(400/401/502)로 응답.

## API Flow

### id/password 회원가입
1. 프론트 → `POST /api/v1/auth/register` (body: username, email, password)
2. 백엔드 → Keycloak Admin API로 유저 생성
3. 백엔드 → DB `users` 테이블에 레코드 생성 (keycloak_sub 연결)
4. 백엔드 → 201 반환

### id/password 로그인
1. 프론트 → `POST /api/v1/auth/token` (body: username, password)
2. 백엔드 → Keycloak password grant 요청
3. 백엔드 → DB users upsert (첫 로그인 보호)
4. 백엔드 → access_token·refresh_token·expires_in 반환

### SSO 로그인 (Keycloak 페이지 경유)
1. 프론트 → Keycloak 로그인 페이지로 리다이렉트 (프론트 직접 처리)
2. Keycloak → authorization code를 콜백 URL로 전달
3. 프론트 → `GET /api/v1/auth/callback?code=...` 호출
4. 백엔드 → Keycloak에 code → token 교환
5. 백엔드 → DB users upsert (첫 로그인 시 레코드 생성)
6. 백엔드 → 토큰 반환

### 토큰 갱신
1. 프론트 → `POST /api/v1/auth/refresh` (body: refresh_token)
2. 백엔드 → Keycloak refresh grant → 새 토큰 반환

### 현재 사용자 조회
1. 프론트 → `GET /api/v1/auth/me` (Authorization: Bearer)
2. 백엔드 → JWT 검증 → 클레임에서 사용자 정보 반환

### 예외 흐름
- 자격증명 오류 → 401
- Keycloak 다운 → 502
- 토큰 만료 → 401
- 이미 가입된 username/email → 409

## Open Questions
- Keycloak Admin API 접근을 위한 admin 계정 관리 방식 — spec 단계에서 결정.
- SSO 콜백 후 토큰을 프론트에 전달하는 방식 (JSON 응답 vs 쿼리 파라미터 리다이렉트) — spec 단계에서 결정.
- Keycloak 공개키 캐싱 TTL — spec 단계에서 결정.
- DB `users` 테이블 컬럼 범위 (keycloak_sub, username, email, created_at 외 추가 여부) — spec 단계에서 결정.
- 실패 응답 에러 코드 체계 표준화 — spec 단계에서 결정.
