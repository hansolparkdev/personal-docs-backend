## MODIFIED Requirements

### Requirement: 벡터 유사도 검색 (pgvector 네이티브)

RAG 파이프라인은 청크 검색 시 pgvector의 `<=>` 코사인 거리 연산자를 사용하여 DB 레벨에서 상위 N개 청크를 반환한다. Python/numpy 기반 코사인 유사도 계산은 사용하지 않는다.

#### Scenario 1: pgvector 검색으로 유사 청크 반환

- **Given** user_id="user-A"의 file_chunks 테이블에 임베딩이 색인된 청크가 10개 있다
- **When** `search_similar_chunks(db, "user-A", query_embedding, limit=5)` 호출
- **Then** pgvector `<=>` 연산자로 코사인 거리가 가장 작은 5개 청크가 반환된다
- **And** 반환된 청크는 모두 user_id="user-A" 소유 파일에서 유래한다
- **And** numpy 모듈이 호출 스택에 개입하지 않는다

#### Scenario 2: 청크가 없을 때 빈 리스트 반환

- **Given** user_id="user-A"의 색인된 청크가 없다
- **When** `search_similar_chunks(db, "user-A", query_embedding, limit=5)` 호출
- **Then** 빈 리스트 `[]`가 반환된다
- **And** 예외가 발생하지 않는다

#### Scenario 3: limit보다 청크 수가 적을 때

- **Given** user_id="user-A"의 색인된 청크가 3개이고 limit=5로 호출
- **When** `search_similar_chunks()` 호출
- **Then** 3개 청크만 반환된다

---

### Requirement: 히스토리 중복 없는 RAG 응답

RAG 응답 생성 시 LLM에 전달되는 대화 히스토리에는 현재 질문이 포함되지 않는다. 현재 질문은 LLM 호출의 human turn에 직접 전달된다.

#### Scenario 1: 첫 번째 메시지 — 히스토리 없음

- **Given** 세션에 메시지가 없다
- **When** 사용자가 첫 질문을 전송한다
- **Then** LLM에 전달되는 히스토리는 빈 리스트이다
- **And** 현재 질문은 human turn으로 단 1회만 전달된다

#### Scenario 2: 두 번째 이후 메시지 — 이전 대화만 히스토리에 포함

- **Given** 세션에 이미 2턴(user+assistant) 대화가 저장되어 있다
- **When** 사용자가 세 번째 질문을 전송한다
- **Then** LLM에 전달되는 히스토리에는 직전 2턴만 포함된다
- **And** 현재 질문(세 번째)은 히스토리에 포함되지 않고 human turn으로만 전달된다

#### Scenario 3: 응답 완료 후 메시지 저장 순서

- **Given** RAG 응답 스트리밍이 완료된다
- **When** 메시지 저장이 수행된다
- **Then** user 메시지가 먼저 DB에 저장된다
- **And** assistant 메시지가 user 메시지 저장 후 DB에 저장된다
- **And** 다음 요청의 히스토리 조회 시 현재 턴이 이전 대화로 정상 포함된다

---

### Requirement: 삭제된 파일 청크 RAG 제외

벡터 검색 시 `deleted_at IS NOT NULL`인 파일에 속한 청크는 결과에서 제외된다.

#### Scenario 1: 삭제된 파일의 청크가 검색에서 제외됨

- **Given** user_id="user-A"가 file_id="abc"를 삭제하여 `files.deleted_at`이 설정되었다
- **And** file_id="abc"에서 유래한 청크가 `file_chunks` 테이블에 존재한다
- **When** `search_similar_chunks(db, "user-A", query_embedding)` 호출
- **Then** file_id="abc" 청크는 검색 결과에 포함되지 않는다

#### Scenario 2: 삭제되지 않은 파일 청크는 정상 검색됨

- **Given** user_id="user-A"가 file_id="def"를 소유하며 deleted_at이 null이다
- **When** `search_similar_chunks(db, "user-A", query_embedding)` 호출
- **Then** file_id="def" 청크가 검색 결과 후보에 포함된다

#### Scenario 3: 다른 유저의 청크는 항상 제외

- **Given** user_id="user-B"의 파일 청크가 존재한다 (deleted_at=null)
- **When** user_id="user-A"로 `search_similar_chunks()` 호출
- **Then** user-B의 청크는 결과에 포함되지 않는다
