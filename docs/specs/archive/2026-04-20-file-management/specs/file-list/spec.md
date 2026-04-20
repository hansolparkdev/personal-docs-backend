## ADDED Requirements

### Requirement: 파일 목록 조회

인증된 사용자가 `GET /api/v1/files`를 호출하면 자신이 업로드한 파일 목록을 반환받는다. 각 항목에는 파일 메타데이터와 현재 index_status가 포함된다.

#### Scenario 1: 파일이 있는 경우 목록 반환

- **Given** user_id="user-A"인 사용자가 인증되어 있고, 자신의 파일 3개가 DB에 있다
- **When** `GET /api/v1/files`를 호출한다
- **Then** 서버는 200을 반환하고, 응답 바디에 배열로 3개의 파일 메타데이터가 포함된다
- **And** 각 항목은 file_id, filename, content_type, size_bytes, index_status, created_at을 포함한다
- **And** 다른 사용자의 파일은 응답에 포함되지 않는다

#### Scenario 2: 파일이 없는 경우 빈 목록 반환

- **Given** user_id="user-B"인 사용자가 인증되어 있고, 업로드한 파일이 없다
- **When** `GET /api/v1/files`를 호출한다
- **Then** 서버는 200을 반환하고, 응답 바디가 빈 배열 `[]`이다

#### Scenario 3: 다양한 index_status가 혼재하는 목록

- **Given** 사용자가 pending, indexing, indexed, failed, unsupported 상태의 파일을 각각 보유한다
- **When** `GET /api/v1/files`를 호출한다
- **Then** 모든 상태의 파일이 목록에 포함된다
- **And** 각 파일의 index_status 값이 실제 상태와 일치한다

#### Scenario 4: 인증 없이 목록 조회 시도

- **Given** JWT 토큰이 없거나 만료된 요청이다
- **When** `GET /api/v1/files`를 호출한다
- **Then** 서버는 401 Unauthorized를 반환한다

### Requirement: 파일 단건 조회

인증된 사용자가 `GET /api/v1/files/{file_id}`를 호출하면 해당 파일의 메타데이터를 반환받는다.

#### Scenario 1: 본인 파일 단건 조회

- **Given** user_id="user-A"인 사용자가 인증되어 있고, file_id="abc"인 파일을 소유한다
- **When** `GET /api/v1/files/abc`를 호출한다
- **Then** 서버는 200을 반환하고, 해당 파일의 메타데이터가 응답 바디에 포함된다

#### Scenario 2: 타인 파일 단건 조회 시도

- **Given** user_id="user-A"인 사용자가 인증되어 있고, file_id="xyz"는 user-B 소유이다
- **When** `GET /api/v1/files/xyz`를 호출한다
- **Then** 서버는 404 Not Found를 반환한다
- **And** 응답에 파일 소유자 정보가 노출되지 않는다

#### Scenario 3: 존재하지 않는 파일 조회

- **Given** user_id="user-A"인 사용자가 인증되어 있다
- **When** 존재하지 않는 file_id로 `GET /api/v1/files/{file_id}`를 호출한다
- **Then** 서버는 404 Not Found를 반환한다

#### Scenario 4: 인증 없이 단건 조회 시도

- **Given** JWT 토큰이 없거나 만료된 요청이다
- **When** `GET /api/v1/files/{file_id}`를 호출한다
- **Then** 서버는 401 Unauthorized를 반환한다
