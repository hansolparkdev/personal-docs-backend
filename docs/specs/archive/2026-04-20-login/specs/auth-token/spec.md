## ADDED Requirements

### Requirement: id/password 로그인 및 토큰 발급

username·password로 Keycloak password grant를 요청하여 access_token·refresh_token을 발급받는다. 로그인 성공 시 DB `users` 테이블에 upsert하여 레코드가 없는 경우 자동 생성하고, `last_login_at`을 갱신한다.

#### Scenario 1: 정상 로그인

- **Given** Keycloak에 해당 username·password로 등록된 유저가 존재
- **When** `POST /api/v1/auth/token` body `{username, password}` 요청
- **Then** Keycloak password grant 요청이 성공하고 토큰을 반환받는다
- **And** DB `users` 테이블에 해당 `auth_id`(Keycloak sub)로 레코드가 upsert된다
- **And** `last_login_at`이 현재 시각으로 갱신된다
- **And** HTTP 200 응답에 `access_token`, `refresh_token`, `token_type`, `expires_in`이 포함된다

#### Scenario 2: 잘못된 비밀번호

- **Given** Keycloak에 username은 존재하지만 password가 틀린 상태
- **When** `POST /api/v1/auth/token` body `{username, wrongpassword}` 요청
- **Then** Keycloak이 401 Unauthorized를 반환
- **And** HTTP 401 응답이 반환된다
- **And** 응답 body `detail`에 자격증명 오류 메시지가 포함된다
- **And** DB upsert가 수행되지 않는다

#### Scenario 3: 존재하지 않는 username

- **Given** Keycloak에 해당 username이 존재하지 않는 상태
- **When** `POST /api/v1/auth/token` body `{unknownuser, password}` 요청
- **Then** Keycloak이 401을 반환
- **And** HTTP 401 응답이 반환된다

#### Scenario 4: DB에 users 레코드가 없는 첫 로그인 (SSO 가입 사용자 포함)

- **Given** Keycloak에 유저는 존재하지만 DB `users`에 레코드가 없는 상태
- **When** `POST /api/v1/auth/token` 요청으로 로그인 성공
- **Then** Keycloak 토큰의 `sub`, `preferred_username`, `email` 클레임으로 DB에 새 레코드가 생성된다
- **And** HTTP 200 응답에 토큰이 반환된다

#### Scenario 5: Keycloak 장애

- **Given** Keycloak 서버가 응답하지 않거나 5xx 오류 반환
- **When** `POST /api/v1/auth/token` 요청
- **Then** HTTP 502 응답이 반환된다

#### Scenario 6: 필수 필드 누락

- **Given** 요청 body에 `password` 필드가 없는 상태
- **When** `POST /api/v1/auth/token` body `{username}` 요청
- **Then** HTTP 422 응답이 반환된다
