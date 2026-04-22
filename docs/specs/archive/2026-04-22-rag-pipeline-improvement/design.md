## Context

현재 `rag_service.py`는 `file_service.get_indexed_chunks()`로 유저의 모든 청크를 메모리에 로드한 뒤 numpy로 코사인 유사도를 계산한다. 히스토리 조회는 `save_user_message()` 이후 `get_recent_messages()`를 호출하므로 현재 질문이 히스토리에 포함된다. `search_similar_chunks`는 `FileChunk` 테이블만 조회하여 `File.deleted_at` 필터가 없다.

## Goals / Non-Goals

**Goals:**
- pgvector `<=>` 연산자로 DB 레벨 벡터 검색 수행 (numpy 제거)
- 히스토리 조회 순서 조정으로 현재 질문 중복 제거
- `FileChunk JOIN File WHERE File.deleted_at IS NULL` 조건으로 삭제 파일 청크 RAG 제외
- 기존 `chat-message` API 인터페이스(SSE 스트리밍, sources 이벤트) 유지

**Non-Goals:**
- 소프트 삭제(soft delete) 방식으로 `file-delete` 전체 재설계
- 벡터 인덱스 타입 변경(HNSW, IVFFlat 튜닝)
- RAG 파이프라인 재설계(LangGraph 그래프 구조 변경)

## Decisions

### 1. pgvector `<=>` 연산자 사용 (코사인 거리)

pgvector는 `<=>` (코사인 거리), `<->` (L2), `<#>` (내적) 연산자를 제공한다. 현재 numpy 구현도 코사인 유사도를 사용하므로 `<=>` 연산자로 교체하면 동일 의미론을 유지하면서 DB 레벨 정렬·LIMIT을 활용할 수 있다.

**이유**: 전체 청크 Python 로드를 제거하여 메모리 사용량과 응답 지연을 줄인다. SQLAlchemy에서 `func` 또는 `text()` 파라미터 바인딩으로 안전하게 표현 가능하다.

### 2. `save_user_message()` 호출 시점을 AI 응답 완료 후로 이동

현재 순서: `save_user_message()` → `get_recent_messages()` → LLM 호출 → `save_ai_message()`.
변경 순서: `get_recent_messages()` → LLM 호출 → `save_user_message()` → `save_ai_message()`.

**이유**: 히스토리는 "이전 대화 맥락"이므로 현재 질문은 LLM 프롬프트의 human turn으로 직접 전달되면 충분하다. 저장 시점만 뒤로 미뤄도 DB 트랜잭션 단위나 세션 조회 API에는 영향이 없다.

### 3. `FileChunk JOIN File WHERE File.deleted_at IS NULL`

`file-delete` 스펙은 하드 삭제(레코드 제거)를 명세하고 있다. 그러나 현재 코드에서 삭제 타이밍과 RAG 검색 간 race condition 가능성이 있으므로, `search_similar_chunks`에 JOIN 조건을 추가해 방어적으로 필터링한다. `File` 모델에 `deleted_at` 컬럼이 없으면 이번 변경에서 추가하되, 실제 삭제 플로우는 기존 하드 삭제를 유지한다.

**이유**: 소프트 삭제로 전체 플로우를 바꾸는 것은 Non-Goal이다. 단순 JOIN 필터로 방어 계층만 추가한다.

## Risks / Trade-offs

- **pgvector 인덱스 미존재 시 성능 저하**: `<=>` 연산자는 인덱스(HNSW/IVFFlat)가 없으면 순차 스캔한다. 현재 데이터 규모에서는 허용 가능하나 인덱스 생성을 권장한다 → 마이그레이션에 인덱스 생성 SQL 포함.
- **메시지 저장 순서 변경으로 인한 롤백 복잡도**: LLM 호출 중 에러 발생 시 user 메시지가 저장되지 않아 대화 이력에 공백이 생긴다 → 기존 구현도 동일 문제가 있으므로 현 범위에서는 허용.
- **deleted_at 컬럼 추가 시 마이그레이션 필요**: `File` 모델에 컬럼이 없으면 Alembic 마이그레이션이 필수다 → forbidden-patterns.md 준수.
