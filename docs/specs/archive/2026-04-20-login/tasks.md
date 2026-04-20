## 1. 환경변수 및 설정 확장

- [ ] 1.1 Keycloak 연동 환경변수 추가
  - 수정 파일: `app/core/config.py`, `.env.example`
  - 추가 변수: `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_CLIENT_SECRET`, `KEYCLOAK_JWKS_CACHE_TTL`

- [ ] 1.2 의존 패키지 추가
  - 수정 파일: `requirements.txt`
  - 추가: `python-jose[cryptography]`, `httpx`, `passlib[bcrypt]` (미존재 시)

## 2. DB 모델 및 마이그레이션

- [ ] 2.1 users ORM 모델 생성
  - 수정 파일: `app/db/models/user.py`
  - 컬럼: `id`(UUID PK), `auth_id`(String unique), `username`(String unique), `email`(String unique), `name`(String nullable), `created_at`, `updated_at`, `last_login_at`

- [ ] 2.2 모델을 Base 메타데이터에 등록
  - 수정 파일: `app/db/base.py`

- [ ] 2.3 Alembic 마이그레이션 생성 — users 테이블 생성
  - 수정 파일: `alembic/versions/<timestamp>_create_users_table.py`

## 3. Pydantic 스키마 정의

- [ ] 3.1 요청/응답 스키마 작성
  - 수정 파일: `app/schemas/auth.py`
  - 스키마: `RegisterRequest`, `TokenRequest`, `RefreshRequest`, `CallbackRequest`, `TokenResponse`, `UserResponse`

## 4. 서비스 레이어 구현

- [ ] 4.1 Keycloak 서비스 구현
  - 수정 파일: `app/services/keycloak_service.py`
  - 기능:
    - `get_service_account_token()` — client_credentials grant로 admin 토큰 발급
    - `create_keycloak_user(token, username, email, password)` — Admin API POST /users
    - `password_grant(username, password)` — Keycloak token endpoint password grant
    - `refresh_grant(refresh_token)` — Keycloak token endpoint refresh grant
    - `exchange_code(code, redirect_uri)` — authorization_code grant
    - `get_jwks()` — JWKS endpoint fetch (TTL 캐싱 포함)

- [ ] 4.2 users 서비스 구현
  - 수정 파일: `app/services/user_service.py`
  - 기능:
    - `upsert_user(db, auth_id, username, email, name)` — auth_id 기준 ON CONFLICT upsert, last_login_at 갱신
    - `get_user_by_auth_id(db, auth_id)` — auth_id로 단건 조회
    - `get_user_by_id(db, user_id)` — UUID로 단건 조회

## 5. JWT 검증 및 공통 의존성

- [ ] 5.1 JWT 검증 로직 구현
  - 수정 파일: `app/core/security.py`
  - 기능: JWKS 기반 서명 검증, 만료 검증, 인메모리 캐싱(TTL 600s), 검증 실패 시 캐시 무효화 후 1회 재시도

- [ ] 5.2 `get_current_user` 의존성 구현
  - 수정 파일: `app/core/dependencies.py`
  - Bearer 토큰 추출 → `security.verify_token()` 호출 → DB에서 User 반환

## 6. 라우터 구현

- [ ] 6.1 auth 라우터 구현
  - 수정 파일: `app/api/v1/auth.py`
  - 엔드포인트:
    - `POST /api/v1/auth/register` → `keycloak_service.create_keycloak_user` + `user_service.upsert_user` → 201
    - `POST /api/v1/auth/token` → `keycloak_service.password_grant` + `user_service.upsert_user` → `TokenResponse`
    - `GET /api/v1/auth/callback` → `keycloak_service.exchange_code` + `user_service.upsert_user` → `TokenResponse`
    - `POST /api/v1/auth/refresh` → `keycloak_service.refresh_grant` → `TokenResponse`
    - `GET /api/v1/auth/me` → `Depends(get_current_user)` → `UserResponse`

- [ ] 6.2 v1 라우터에 auth 라우터 등록
  - 수정 파일: `app/api/v1/router.py`

## 7. OpenAPI BearerAuth 설정

- [ ] 7.1 `custom_openapi()` 구현으로 Swagger UI에 BearerAuth securityScheme 추가
  - 수정 파일: `app/main.py`
