## ADDED Requirements

### Requirement: SSO 콜백 처리 및 토큰 발급

Keycloak SSO 인증 완료 후 프론트엔드가 전달하는 authorization code를 받아 Keycloak token endpoint와 code 교환한다. 교환 성공 시 JWT 클레임에서 사용자 정보를 추출해 DB `users`에 upsert(첫 로그인이면 신규 생성)하고, 토큰을 JSON으로 반환한다.

#### Scenario 1: 정상 SSO 콜백 — 첫 로그인 (DB 레코드 미존재)

- **Given** Keycloak SSO 인증이 완료되어 유효한 authorization code가 발급된 상태
- **And** 해당 사용자의 DB `users` 레코드가 존재하지 않음
- **When** `GET /api/v1/auth/callback?code=<valid_code>&redirect_uri=<uri>` 요청
- **Then** 백엔드가 Keycloak token endpoint에 authorization_code grant로 token 교환 요청
- **And** 교환된 JWT의 `sub`, `preferred_username`, `email`, `name` 클레임으로 DB `users` 신규 레코드가 생성된다
- **And** `last_login_at`이 현재 시각으로 설정된다
- **And** HTTP 200 응답에 `access_token`, `refresh_token`, `token_type`, `expires_in`이 포함된다

#### Scenario 2: 정상 SSO 콜백 — 재로그인 (DB 레코드 존재)

- **Given** 유효한 authorization code가 발급된 상태
- **And** 해당 사용자의 DB `users` 레코드가 이미 존재함
- **When** `GET /api/v1/auth/callback?code=<valid_code>&redirect_uri=<uri>` 요청
- **Then** DB `users` 레코드가 upsert로 갱신되고 `last_login_at`이 업데이트된다
- **And** HTTP 200 응답에 토큰이 반환된다

#### Scenario 3: 유효하지 않거나 만료된 authorization code

- **Given** Keycloak이 발급한 code가 만료되었거나 이미 사용된 상태
- **When** `GET /api/v1/auth/callback?code=<invalid_code>&redirect_uri=<uri>` 요청
- **Then** Keycloak token endpoint가 4xx 오류를 반환
- **And** HTTP 400 응답이 반환된다
- **And** 응답 body `detail`에 code 오류 메시지가 포함된다
- **And** DB upsert가 수행되지 않는다

#### Scenario 4: redirect_uri 파라미터 누락

- **Given** 요청 쿼리 파라미터에 `redirect_uri`가 없는 상태
- **When** `GET /api/v1/auth/callback?code=<valid_code>` 요청
- **Then** HTTP 422 응답이 반환된다

#### Scenario 5: code 파라미터 누락

- **Given** 요청 쿼리 파라미터에 `code`가 없는 상태
- **When** `GET /api/v1/auth/callback` 요청
- **Then** HTTP 422 응답이 반환된다

#### Scenario 6: Keycloak 장애

- **Given** Keycloak token endpoint가 응답하지 않거나 5xx 오류 반환
- **When** `GET /api/v1/auth/callback?code=<code>&redirect_uri=<uri>` 요청
- **Then** HTTP 502 응답이 반환된다
- **And** DB upsert가 수행되지 않는다
