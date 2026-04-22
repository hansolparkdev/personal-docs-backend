## Why

RAG 파이프라인에 세 가지 결함이 있다. 첫째, numpy 기반 코사인 유사도 계산이 Python 레벨에서 수행되어 전체 청크를 메모리에 로드해야 한다. 둘째, 현재 질문이 히스토리에 중복 포함되어 LLM 컨텍스트가 오염된다. 셋째, 소프트 삭제(deleted_at)된 파일의 청크가 RAG 검색 결과에 계속 노출된다.

## What Changes

- `file_service.py`의 `get_indexed_chunks()` 제거, pgvector `<=>` 연산자를 사용하는 `search_similar_chunks(db, user_id, query_embedding, limit=5)` 신규 추가
- `rag_service.py`의 `_cosine_sim()` 및 numpy 의존 벡터 계산 제거, `search_similar_chunks()` 호출로 교체
- `rag_service.py`에서 `save_user_message()` 호출 순서를 AI 응답 저장 직전으로 이동하여 히스토리 중복 제거
- `search_similar_chunks()`에 `FileChunk JOIN File` 및 `File.deleted_at IS NULL` 조건 추가

## Capabilities

### New Capabilities

- 없음

### Modified Capabilities

- `chat-message`: RAG 검색이 pgvector 네이티브 연산자로 교체되고, 히스토리 중복 버그가 수정되며, 삭제된 파일 청크가 검색에서 제외됨
- `file-delete`: 소프트 삭제(deleted_at) 방식 도입 시 RAG 격리 보장 방식이 변경됨 (하드 삭제 유지 or 소프트 삭제 전환 여부 결정 포함)

## Impact

- `app/services/rag_service.py` — 벡터 검색 로직 교체, 메시지 저장 순서 변경
- `app/services/file_service.py` — `get_indexed_chunks()` 제거, `search_similar_chunks()` 추가
- `app/db/models/file_chunk.py` — JOIN 조건 확인 (모델 변경 없음)
- `app/db/models/file.py` — `deleted_at` 컬럼 유무 확인 (없으면 추가 필요)
- `tests/test_chat.py` — 변경된 서비스 계층에 대한 테스트 갱신

## Meta

- feature: rag-pipeline-improvement
- type: backend
- package: .

---

프리로드: folder-conventions.md · dev-flow.md · forbidden-patterns.md
