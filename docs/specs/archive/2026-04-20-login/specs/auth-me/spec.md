## ADDED Requirements

### Requirement: 현재 사용자 정보 조회

Authorization 헤더의 Bearer JWT를 검증하고, JWT의 `sub` 클레임으로 DB `users` 테이블에서 사용자 정보를 조회해 반환한다. `get_current_user` 의존성을 통해 다른 라우터도 동일한 인증 흐름을 재사용한다.

#### Scenario 1: 정상 조회

- **Given** 유효하고 만료되지 않은 access_token을 보유한 사용자
- **When** `GET /api/v1/auth/me` `Authorization: Bearer <valid_token>` 요청
- **Then** JWT 서명 및 만료 검증이 성공한다
- **And** JWT `sub` 클레임으로 DB `users` 레코드를 조회한다
- **And** HTTP 200 응답에 `user_id`(내부 UUID), `username`, `email`, `name`, `created_at`, `last_login_at`이 포함된다

#### Scenario 2: Authorization 헤더 누락

- **Given** 요청에 Authorization 헤더가 없는 상태
- **When** `GET /api/v1/auth/me` 요청 (헤더 없음)
- **Then** HTTP 401 응답이 반환된다
- **And** 응답 body `detail`에 인증 필요 메시지가 포함된다

#### Scenario 3: 만료된 access_token

- **Given** 만료된 access_token
- **When** `GET /api/v1/auth/me` `Authorization: Bearer <expired_token>` 요청
- **Then** JWT 만료 검증이 실패한다
- **And** HTTP 401 응답이 반환된다
- **And** 응답 body `detail`에 토큰 만료 메시지가 포함된다

#### Scenario 4: 서명이 유효하지 않은 토큰

- **Given** 잘못된 서명을 가진 JWT (변조된 토큰)
- **When** `GET /api/v1/auth/me` `Authorization: Bearer <tampered_token>` 요청
- **Then** JWKS 기반 서명 검증이 실패한다
- **And** HTTP 401 응답이 반환된다

#### Scenario 5: 유효한 토큰이지만 DB에 users 레코드 미존재

- **Given** Keycloak에는 유저가 존재하고 유효한 토큰을 보유했지만 DB `users` 레코드가 없는 상태
- **When** `GET /api/v1/auth/me` 요청
- **Then** DB 조회 결과가 없으므로 HTTP 404 응답이 반환된다
- **And** 응답 body `detail`에 사용자 미존재 메시지가 포함된다

#### Scenario 6: Keycloak JWKS endpoint 장애 시 캐시 재사용

- **Given** 인메모리 JWKS 캐시가 유효한 상태이고 Keycloak JWKS endpoint가 일시 장애 중
- **When** `GET /api/v1/auth/me` 요청
- **Then** 캐시된 공개키로 JWT 검증이 성공한다
- **And** HTTP 200 응답이 정상 반환된다

#### Scenario 7: JWKS 캐시 만료 후 검증 실패 → 재시도 성공

- **Given** JWKS 캐시가 만료된 상태이고 Keycloak이 새로운 키를 반환
- **When** `GET /api/v1/auth/me` 유효한 토큰으로 요청
- **Then** 캐시 무효화 후 JWKS를 다시 fetch하여 검증에 성공한다
- **And** HTTP 200 응답이 반환된다

### Requirement: get_current_user 공통 의존성

FastAPI `Depends(get_current_user)`로 주입 가능한 공통 인증 의존성. `app/core/dependencies.py`에 위치하며 모든 보호된 라우터가 재사용한다.

#### Scenario 1: 의존성 정상 주입

- **Given** 유효한 Bearer 토큰이 Authorization 헤더에 있는 요청
- **When** `get_current_user` 의존성이 주입된 엔드포인트 호출
- **Then** `User` ORM 객체가 반환되어 라우터 핸들러에서 사용 가능하다

#### Scenario 2: 의존성 인증 실패

- **Given** 유효하지 않은 또는 누락된 Bearer 토큰
- **When** `get_current_user` 의존성이 주입된 엔드포인트 호출
- **Then** `HTTPException(status_code=401)`이 raise되어 요청이 중단된다
- **And** 라우터 핸들러 로직이 실행되지 않는다
