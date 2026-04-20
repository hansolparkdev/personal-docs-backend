## Why

personal-docs 서비스는 사용자별 파일·챗 데이터 격리가 필수다. 현재 인증 레이어가 없어 어떤 API도 사용자를 식별하지 못하며, id/password 직접 가입과 Keycloak SSO 두 경로 모두에서 백엔드 DB에 users 레코드를 생성·연결하는 메커니즘이 없다. 이를 해결하지 않으면 파일 관리·RAG 챗 기능의 다중 사용자 지원이 불가능하다.

## What Changes

- `POST /api/v1/auth/register` 엔드포인트 신설 — Keycloak Admin API로 유저 생성 후 DB users 레코드 생성
- `POST /api/v1/auth/token` 엔드포인트 신설 — password grant를 통해 Keycloak에서 토큰 발급, DB upsert
- `GET /api/v1/auth/callback` 엔드포인트 신설 — SSO authorization code를 token으로 교환, DB upsert
- `POST /api/v1/auth/refresh` 엔드포인트 신설 — refresh_token으로 새 access_token 발급
- `GET /api/v1/auth/me` 엔드포인트 신설 — Bearer 토큰 검증 후 현재 사용자 정보 반환
- `app/db/models/user.py` 신설 — users 테이블 ORM 모델 (UUID PK, auth_id, username, email, name, timestamps)
- `app/core/security.py` 신설 — Keycloak 공개키 기반 JWT 검증, `get_current_user` 의존성
- `app/core/config.py` 수정 — Keycloak 연동 환경변수 추가 (URL, realm, client_id, client_secret)
- `app/services/user_service.py` 신설 — users upsert·조회 비즈니스 로직
- `app/services/keycloak_service.py` 신설 — Keycloak Admin API·token endpoint 호출 로직
- `app/main.py` 수정 — custom_openapi()로 BearerAuth securityScheme 등록
- Alembic 마이그레이션 신설 — users 테이블 생성

## Capabilities

### New Capabilities

- `auth-register`: username·email·password로 Keycloak 유저 생성 및 DB users 레코드 신규 생성
- `auth-token`: username/password → Keycloak password grant → 토큰 발급 + DB users upsert
- `auth-callback`: SSO authorization code → Keycloak token 교환 → DB users upsert → 토큰 반환
- `auth-refresh`: refresh_token → Keycloak refresh grant → 새 토큰 반환
- `auth-me`: Bearer JWT 검증 → DB에서 현재 사용자 정보 반환

### Modified Capabilities

없음. 기존 file-upload, file-list, file-delete, file-download 라우터는 `get_current_user` 의존성을 추가 적용하는 것은 별도 변경 작업으로 분리한다.

## Impact

신규 파일:
- `app/api/v1/auth.py`
- `app/db/models/user.py`
- `app/core/security.py`
- `app/services/user_service.py`
- `app/services/keycloak_service.py`
- `app/schemas/auth.py`
- `alembic/versions/<timestamp>_create_users_table.py`
- `tests/test_auth.py`

수정 파일:
- `app/core/config.py` — Keycloak 환경변수 추가
- `app/core/dependencies.py` — `get_current_user` 공개
- `app/api/v1/router.py` — auth 라우터 등록
- `app/main.py` — custom_openapi BearerAuth 추가
- `.env.example` — Keycloak 환경변수 예시 추가
- `requirements.txt` — python-jose[cryptography], httpx 추가 확인

## Meta

- feature: login
- type: backend
- package: backend

프리로드: folder-conventions.md · dev-flow.md · forbidden-patterns.md
