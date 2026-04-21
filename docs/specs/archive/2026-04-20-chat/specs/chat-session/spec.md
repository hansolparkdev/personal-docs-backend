## ADDED Requirements

### Requirement: 세션 생성

인증된 사용자가 새 대화 세션을 생성한다. 세션은 JWT sub(user_id)에 귀속되며, 제목은 첫 번째 메시지가 전송될 때 자동으로 설정된다.

#### Scenario 1: 정상 세션 생성

- **Given** 유효한 JWT를 가진 인증된 사용자
- **When** `POST /api/v1/chats` 요청
- **Then** HTTP 201, 신규 `chat_sessions` 레코드 생성
- **And** 응답 body에 `id`, `title`(빈 문자열 또는 null), `created_at`, `updated_at` 포함
- **And** `user_id` 필드는 요청한 사용자의 JWT sub와 동일

#### Scenario 2: 미인증 요청

- **Given** JWT 없음 또는 만료된 JWT
- **When** `POST /api/v1/chats` 요청
- **Then** HTTP 401

---

### Requirement: 세션 목록 조회

인증된 사용자가 자신의 세션 목록을 최신순으로 조회한다. 최대 50개를 반환한다.

#### Scenario 1: 정상 목록 조회

- **Given** 유효한 JWT, 세션이 3개 이상 존재하는 사용자
- **When** `GET /api/v1/chats` 요청
- **Then** HTTP 200, 배열 형태 응답
- **And** 각 항목에 `id`, `title`, `created_at`, `updated_at` 포함
- **And** `updated_at` 내림차순 정렬

#### Scenario 2: 세션 없음

- **Given** 유효한 JWT, 세션이 없는 사용자
- **When** `GET /api/v1/chats` 요청
- **Then** HTTP 200, 빈 배열 `[]`

#### Scenario 3: 50개 초과 세션

- **Given** 유효한 JWT, 세션이 60개인 사용자
- **When** `GET /api/v1/chats` 요청
- **Then** HTTP 200, 최신 50개만 반환

#### Scenario 4: 다른 사용자 세션 미노출

- **Given** 사용자 A와 사용자 B 각각 세션 보유
- **When** 사용자 A가 `GET /api/v1/chats` 요청
- **Then** 사용자 A의 세션만 반환, 사용자 B의 세션 미포함

---

### Requirement: 세션 단건 조회

인증된 사용자가 특정 세션과 그 안의 메시지 이력을 조회한다.

#### Scenario 1: 정상 단건 조회

- **Given** 유효한 JWT, 본인 소유 세션
- **When** `GET /api/v1/chats/{session_id}` 요청
- **Then** HTTP 200
- **And** 응답 body에 세션 정보 + `messages` 배열 포함
- **And** `messages` 배열은 `created_at` 오름차순 정렬
- **And** 각 메시지에 `id`, `role`, `content`, `sources`, `created_at` 포함

#### Scenario 2: 타인 세션 접근

- **Given** 유효한 JWT, 타인 소유 세션 ID
- **When** `GET /api/v1/chats/{session_id}` 요청
- **Then** HTTP 404

#### Scenario 3: 존재하지 않는 세션

- **Given** 유효한 JWT, 존재하지 않는 session_id
- **When** `GET /api/v1/chats/{session_id}` 요청
- **Then** HTTP 404

---

### Requirement: 세션 삭제

인증된 사용자가 자신의 세션을 삭제한다. 세션에 포함된 모든 메시지가 함께 삭제된다(CASCADE).

#### Scenario 1: 정상 삭제

- **Given** 유효한 JWT, 본인 소유 세션
- **When** `DELETE /api/v1/chats/{session_id}` 요청
- **Then** HTTP 204
- **And** `chat_sessions` 레코드 삭제
- **And** 해당 세션의 `chat_messages` 레코드 전체 CASCADE 삭제

#### Scenario 2: 타인 세션 삭제 시도

- **Given** 유효한 JWT, 타인 소유 세션 ID
- **When** `DELETE /api/v1/chats/{session_id}` 요청
- **Then** HTTP 404

#### Scenario 3: 존재하지 않는 세션 삭제 시도

- **Given** 유효한 JWT, 존재하지 않는 session_id
- **When** `DELETE /api/v1/chats/{session_id}` 요청
- **Then** HTTP 404

---

### Requirement: 세션 제목 자동 설정

세션에 첫 번째 메시지가 전송될 때 메시지 내용의 앞 20자를 세션 제목으로 저장한다.

#### Scenario 1: 첫 메시지로 제목 설정

- **Given** 제목이 없는(null/빈 문자열) 세션
- **When** 해당 세션에 첫 메시지 전송 (content: "오늘 미팅 요약 내용이 어떻게 됐지?")
- **Then** 세션 title이 "오늘 미팅 요약 내용이 어떻게 됐" (앞 20자)로 설정
- **And** `updated_at` 갱신

#### Scenario 2: 두 번째 이후 메시지는 제목 불변

- **Given** 제목이 이미 설정된 세션
- **When** 해당 세션에 두 번째 메시지 전송
- **Then** 세션 title 변경 없음

#### Scenario 3: 20자 미만 첫 메시지

- **Given** 제목이 없는 세션
- **When** 첫 메시지 content가 "안녕" (2자)
- **Then** 세션 title이 "안녕" (전체 content)으로 설정
