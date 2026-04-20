## ADDED Requirements

### Requirement: 파일 다운로드 (presigned URL)

인증된 사용자가 `GET /api/v1/files/{file_id}/download`를 호출하면 서버는 소유권을 확인한 뒤 MinIO presigned URL을 반환한다. 클라이언트는 이 URL로 MinIO에서 직접 원본 파일을 내려받는다. 서버는 파일 바이트를 스트림하지 않는다.

#### Scenario 1: 본인 파일 다운로드 URL 요청 정상 흐름

- **Given** user_id="user-A"인 사용자가 인증되어 있고, file_id="abc"인 파일을 소유한다
- **When** `GET /api/v1/files/abc/download`를 호출한다
- **Then** 서버는 200을 반환하고, 응답 바디에 `download_url` 필드와 `expires_in` 필드가 포함된다
- **And** `download_url`은 MinIO가 발급한 presigned URL이다
- **And** URL 유효시간은 3600초(1시간)이다
- **And** 클라이언트가 해당 URL로 GET 요청하면 원본 파일 바이트를 수신할 수 있다

#### Scenario 2: 타인 파일 다운로드 URL 요청 시도

- **Given** user_id="user-A"인 사용자가 인증되어 있고, file_id="xyz"는 user-B 소유이다
- **When** `GET /api/v1/files/xyz/download`를 호출한다
- **Then** 서버는 404 Not Found를 반환한다
- **And** presigned URL이 발급되지 않는다

#### Scenario 3: 존재하지 않는 파일 다운로드 URL 요청

- **Given** user_id="user-A"인 사용자가 인증되어 있다
- **When** 존재하지 않는 file_id로 `GET /api/v1/files/{file_id}/download`를 호출한다
- **Then** 서버는 404 Not Found를 반환한다

#### Scenario 4: 인증 없이 다운로드 URL 요청

- **Given** JWT 토큰이 없거나 만료된 요청이다
- **When** `GET /api/v1/files/{file_id}/download`를 호출한다
- **Then** 서버는 401 Unauthorized를 반환한다

#### Scenario 5: 파일 삭제 후 기발급 presigned URL 접근

- **Given** user_id="user-A"가 `GET /api/v1/files/abc/download`로 presigned URL을 발급받았다
- **When** 이후 `DELETE /api/v1/files/abc`가 완료된 뒤 클라이언트가 기발급 URL로 요청한다
- **Then** MinIO는 해당 객체가 없으므로 오류를 반환한다
- **And** 삭제된 파일에 대한 접근이 차단된다

### Requirement: 서버 직접 파일 노출 금지

서버는 파일 바이트를 응답 바디에 직접 포함하거나 스트림하지 않는다. 모든 파일 전송은 MinIO presigned URL을 통해 이루어진다.

#### Scenario 1: presigned URL 방식 강제

- **Given** 다운로드 엔드포인트가 구현되어 있다
- **When** `GET /api/v1/files/{file_id}/download`를 호출한다
- **Then** 응답 Content-Type이 `application/json`이고, 바디에 URL 문자열만 포함된다
- **And** 응답 바디에 파일 바이트 데이터가 포함되지 않는다
