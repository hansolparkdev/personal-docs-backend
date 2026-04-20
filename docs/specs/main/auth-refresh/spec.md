## ADDED Requirements

### Requirement: 토큰 갱신

만료된 access_token 대신 유효한 refresh_token을 사용해 Keycloak에서 새로운 access_token·refresh_token 쌍을 발급받는다. 백엔드는 refresh_token을 저장하지 않고 Keycloak에 위임한다.

#### Scenario 1: 정상 토큰 갱신

- **Given** 유효한 refresh_token을 보유한 사용자
- **When** `POST /api/v1/auth/refresh` body `{refresh_token: "<valid_refresh_token>"}` 요청
- **Then** 백엔드가 Keycloak token endpoint에 refresh_token grant 요청을 전달한다
- **And** HTTP 200 응답에 새로운 `access_token`, `refresh_token`, `token_type`, `expires_in`이 포함된다

#### Scenario 2: 만료된 refresh_token

- **Given** 이미 만료된 refresh_token
- **When** `POST /api/v1/auth/refresh` body `{refresh_token: "<expired_token>"}` 요청
- **Then** Keycloak이 4xx 오류를 반환
- **And** HTTP 401 응답이 반환된다
- **And** 응답 body `detail`에 토큰 만료 메시지가 포함된다

#### Scenario 3: 유효하지 않은 refresh_token 형식

- **Given** JWT 형식이 아닌 임의 문자열
- **When** `POST /api/v1/auth/refresh` body `{refresh_token: "notavalidtoken"}` 요청
- **Then** Keycloak이 4xx 오류를 반환
- **And** HTTP 401 응답이 반환된다

#### Scenario 4: refresh_token 필드 누락

- **Given** 요청 body에 `refresh_token` 필드가 없는 상태
- **When** `POST /api/v1/auth/refresh` body `{}` 요청
- **Then** HTTP 422 응답이 반환된다

#### Scenario 5: Keycloak 장애

- **Given** Keycloak token endpoint가 응답하지 않거나 5xx 오류 반환
- **When** `POST /api/v1/auth/refresh` 요청
- **Then** HTTP 502 응답이 반환된다
