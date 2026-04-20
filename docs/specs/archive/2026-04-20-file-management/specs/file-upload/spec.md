## ADDED Requirements

### Requirement: 파일 업로드

인증된 사용자가 파일을 `POST /api/v1/files`로 전송하면 서버는 크기·포맷을 검증한 뒤 원본을 MinIO에 저장하고, 메타데이터를 DB에 기록하며, 백그라운드에서 텍스트 추출·임베딩 색인을 수행한다. 사용자에게는 저장 완료 즉시 응답이 반환된다.

#### Scenario 1: 지원 포맷 파일 업로드 정상 흐름

- **Given** 유효한 Keycloak JWT를 소지한 사용자가 있다
- **When** 지원 포맷(PDF, DOCX, PPTX, XLSX, MD, TXT) 파일을 `POST /api/v1/files`로 전송한다
- **Then** 서버는 201을 반환하고, 응답 바디에 file_id, filename, index_status="pending", created_at이 포함된다
- **And** MinIO의 `{user_id}/{file_id}/{filename}` 경로에 원본이 저장된다
- **And** DB `files` 테이블에 index_status="pending" 레코드가 생성된다
- **And** 백그라운드에서 MarkItDown 변환 → LangChain 청킹 → pgvector 임베딩이 진행된다
- **And** 색인 완료 후 `files.index_status`가 "indexed"로 갱신된다

#### Scenario 2: 미지원 포맷 파일 업로드

- **Given** 유효한 JWT를 소지한 사용자가 있다
- **When** 미지원 포맷(예: .exe, .zip, .png) 파일을 `POST /api/v1/files`로 전송한다
- **Then** 서버는 415 Unsupported Media Type을 반환하고 업로드를 거부한다

#### Scenario 3: 허용 크기 초과 파일 업로드

- **Given** 유효한 JWT를 소지한 사용자가 있다
- **When** 설정된 최대 파일 크기(예: 50MB)를 초과하는 파일을 전송한다
- **Then** 서버는 413 Request Entity Too Large를 반환하고 업로드를 거부한다

#### Scenario 4: 인증 없이 업로드 시도

- **Given** JWT 토큰이 없거나 만료된 요청이다
- **When** `POST /api/v1/files`를 호출한다
- **Then** 서버는 401 Unauthorized를 반환한다

#### Scenario 5: MarkItDown 파싱 실패 (텍스트 추출 불가)

- **Given** 유효한 JWT를 소지한 사용자가 지원 MIME이지만 손상된 파일을 업로드한다
- **When** 백그라운드 태스크에서 MarkItDown 변환이 실패한다
- **Then** MinIO의 원본 파일은 유지된다
- **And** `files.index_status`가 "failed"로 갱신된다
- **And** 사용자는 목록 조회에서 해당 파일의 상태가 "failed"임을 확인할 수 있다

### Requirement: 소유권 기반 파일 격리

업로드된 파일은 JWT sub(user_id)로 식별된 소유자에게만 속하며, 다른 사용자는 해당 파일에 접근할 수 없다.

#### Scenario 1: 업로드 시 user_id 자동 연결

- **Given** user_id="user-A"인 사용자가 인증되어 있다
- **When** 파일을 업로드한다
- **Then** `files.user_id`에 "user-A"가 저장된다
- **And** MinIO 경로가 `user-A/{file_id}/{filename}`으로 기록된다
