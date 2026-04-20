## ADDED Requirements

### Requirement: id/password 회원가입

username·email·password를 받아 Keycloak Admin API로 Keycloak 유저를 생성하고, 백엔드 DB `users` 테이블에 레코드를 생성한다. 두 단계 모두 성공해야 201을 반환한다.

#### Scenario 1: 정상 가입

- **Given** Keycloak이 정상 동작 중이고, 해당 username·email이 Keycloak과 DB 모두에 미존재
- **When** `POST /api/v1/auth/register` body `{username, email, password}` 요청
- **Then** Keycloak에 신규 유저가 생성되고 DB `users` 테이블에 레코드가 삽입된다
- **And** HTTP 201 응답이 반환된다
- **And** 응답 body에 `user_id`, `username`, `email`이 포함된다

#### Scenario 2: 이미 사용 중인 username

- **Given** 동일한 username이 Keycloak 또는 DB에 이미 존재
- **When** `POST /api/v1/auth/register` body `{username, email, password}` 요청
- **Then** Keycloak Admin API가 409 Conflict를 반환하거나 DB unique 제약 위반이 발생
- **And** HTTP 409 응답이 반환된다
- **And** 응답 body `detail`에 충돌 원인을 설명하는 메시지가 포함된다

#### Scenario 3: 이미 사용 중인 email

- **Given** 동일한 email이 Keycloak 또는 DB에 이미 존재
- **When** `POST /api/v1/auth/register` body `{username, email, password}` 요청
- **Then** HTTP 409 응답이 반환된다
- **And** 응답 body `detail`에 email 충돌 메시지가 포함된다

#### Scenario 4: Keycloak Admin API 장애

- **Given** Keycloak 서버가 응답하지 않거나 5xx 오류 반환
- **When** `POST /api/v1/auth/register` 요청
- **Then** HTTP 502 응답이 반환된다
- **And** DB에 users 레코드가 생성되지 않는다

#### Scenario 5: 필수 필드 누락

- **Given** 요청 body에 `password`가 없는 상태
- **When** `POST /api/v1/auth/register` body `{username, email}` 요청
- **Then** HTTP 422 응답이 반환된다
- **And** 응답 body에 누락 필드 정보가 포함된다

#### Scenario 6: password 최소 길이 미달

- **Given** 요청 body의 password가 8자 미만
- **When** `POST /api/v1/auth/register` 요청
- **Then** HTTP 422 응답이 반환된다
