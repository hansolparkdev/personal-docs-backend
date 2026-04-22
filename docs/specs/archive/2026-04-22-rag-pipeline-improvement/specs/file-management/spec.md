## MODIFIED Requirements

### Requirement: 파일 삭제 후 RAG 격리 (deleted_at 방어 필터)

파일이 삭제된 이후 RAG 검색에서 해당 파일 청크가 제외되는 것은 기존 스펙과 동일하다. 이번 변경에서 `search_similar_chunks`에 `File.deleted_at IS NULL` 조건이 추가되어, 하드 삭제 타이밍 외에도 소프트 삭제 상태에서도 RAG 격리가 보장된다.

#### Scenario 1: 하드 삭제 후 청크 조회 결과 없음 (기존 동작 유지)

- **Given** user_id="user-A"가 file_id="abc"를 삭제하여 DB `files` 레코드와 `file_chunks` 레코드가 제거되었다
- **When** RAG 챗에서 `search_similar_chunks(db, "user-A", query_embedding)` 호출
- **Then** file_id="abc"에서 유래한 청크가 검색 결과에 포함되지 않는다

#### Scenario 2: deleted_at 설정된 파일 청크가 검색에서 제외됨 (신규 방어 계층)

- **Given** `files` 테이블에 file_id="abc" 레코드가 존재하나 `deleted_at`이 현재 시각으로 설정되어 있다
- **And** `file_chunks` 테이블에 file_id="abc" 청크가 존재한다
- **When** RAG 챗에서 `search_similar_chunks(db, "user-A", query_embedding)` 호출
- **Then** file_id="abc" 청크가 검색 결과에 포함되지 않는다
- **And** `File.deleted_at IS NULL` 조건이 쿼리에 적용된다
