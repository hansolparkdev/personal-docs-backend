## ADDED Requirements

### Requirement: 파일 삭제

인증된 사용자가 `DELETE /api/v1/files/{file_id}`를 호출하면 서버는 소유권을 확인한 뒤 MinIO 원본, DB files 레코드, 연관 file_chunks를 일괄 제거한다. 삭제 후에는 해당 파일의 내용이 RAG 응답에 등장하지 않는다.

#### Scenario 1: 본인 파일 삭제 정상 흐름

- **Given** user_id="user-A"인 사용자가 인증되어 있고, file_id="abc"인 파일을 소유한다
- **When** `DELETE /api/v1/files/abc`를 호출한다
- **Then** 서버는 204 No Content를 반환한다
- **And** MinIO에서 해당 파일 객체가 제거된다
- **And** DB `files` 테이블에서 해당 레코드가 삭제된다
- **And** DB `file_chunks` 테이블에서 file_id="abc"인 모든 청크가 삭제된다

#### Scenario 2: 타인 파일 삭제 시도

- **Given** user_id="user-A"인 사용자가 인증되어 있고, file_id="xyz"는 user-B 소유이다
- **When** `DELETE /api/v1/files/xyz`를 호출한다
- **Then** 서버는 404 Not Found를 반환한다
- **And** MinIO 원본 및 DB 레코드는 변경되지 않는다

#### Scenario 3: 존재하지 않는 파일 삭제 시도

- **Given** user_id="user-A"인 사용자가 인증되어 있다
- **When** 존재하지 않는 file_id로 `DELETE /api/v1/files/{file_id}`를 호출한다
- **Then** 서버는 404 Not Found를 반환한다

#### Scenario 4: 인증 없이 삭제 시도

- **Given** JWT 토큰이 없거나 만료된 요청이다
- **When** `DELETE /api/v1/files/{file_id}`를 호출한다
- **Then** 서버는 401 Unauthorized를 반환한다

#### Scenario 5: MinIO 삭제 실패 시 일관성 보장

- **Given** user_id="user-A"인 사용자가 인증되어 있고, file_id="abc"인 파일을 소유한다
- **When** `DELETE /api/v1/files/abc`를 호출하는데 MinIO가 일시적으로 오류를 반환한다
- **Then** 서버는 500 Internal Server Error를 반환한다
- **And** DB의 files 레코드와 file_chunks는 삭제되지 않고 유지된다
- **And** 데이터 일관성이 보장된다

### Requirement: 삭제 후 RAG 격리

파일이 삭제되면 해당 파일에서 생성된 file_chunks가 제거되어, 이후 RAG 질의에서 해당 파일 내용이 검색 결과에 포함되지 않는다.

#### Scenario 1: 삭제 후 RAG 질의에서 제외

- **Given** user_id="user-A"가 file_id="abc" 파일을 소유하며, 이 파일의 청크가 pgvector에 색인되어 있다
- **When** `DELETE /api/v1/files/abc`가 완료된 후 RAG 챗이 user-A의 indexed 청크를 조회한다
- **Then** file_id="abc"에서 유래한 청크가 조회 결과에 포함되지 않는다

#### Scenario 2: deleted_at 설정된 파일 청크가 검색에서 제외됨 (방어 필터)

- **Given** `files` 테이블에 file_id="abc" 레코드가 존재하나 `deleted_at`이 현재 시각으로 설정되어 있다
- **And** `file_chunks` 테이블에 file_id="abc" 청크가 존재한다
- **When** RAG 챗에서 `search_similar_chunks(db, "user-A", query_embedding)` 호출
- **Then** file_id="abc" 청크가 검색 결과에 포함되지 않는다
- **And** `File.deleted_at IS NULL` 조건이 쿼리에 적용된다
