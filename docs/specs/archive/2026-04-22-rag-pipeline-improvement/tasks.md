## 1. File 모델 deleted_at 컬럼 확인 및 추가

- [x] 1.1 `File` 모델에 `deleted_at` 컬럼 유무 확인, 없으면 `Optional[datetime]` 컬럼 추가
  - 수정 파일: `app/db/models/file.py` (이미 존재 — 스킵)
- [x] 1.2 Alembic 마이그레이션 생성 (모델 변경 없음 — 스킵)

## 2. file_service — 벡터 검색 함수 교체

- [x] 2.1 `get_indexed_chunks()` 함수 제거
  - 수정 파일: `app/services/file_service.py`
- [x] 2.2 `search_similar_chunks(db: AsyncSession, user_id: str, query_embedding: list[float], limit: int = 5) -> list[FileChunk]` 추가
  - pgvector `<=>` 연산자로 코사인 거리 기준 상위 `limit`개 반환
  - `FileChunk JOIN File ON FileChunk.file_id = File.id` 조건 포함
  - `File.user_id = user_id` 및 `File.deleted_at IS NULL` 필터 필수
  - SQL 문자열 직접 조합 금지 — SQLAlchemy ORM / 파라미터 바인딩 사용
  - 수정 파일: `app/services/file_service.py`

## 3. rag_service — numpy 제거 및 검색 교체

- [x] 3.1 `_cosine_sim()` 함수 및 numpy import 제거
  - 수정 파일: `app/services/rag_service.py`
- [x] 3.2 청크 수집 로직을 `search_similar_chunks()` 호출로 교체
  - 수정 파일: `app/services/rag_service.py`

## 4. rag_service — 히스토리 중복 버그 수정

- [x] 4.1 `save_user_message()` 호출 위치를 AI 응답 완료(스트리밍 종료) 직전으로 이동
  - 변경 전 순서: save_user → get_history → LLM → save_ai
  - 변경 후 순서: get_history → LLM → save_user → save_ai
  - 수정 파일: `app/services/rag_service.py`

## 5. requirements.txt — numpy 제거

- [x] 5.1 `numpy` 의존성 확인 — requirements.txt에 원래 없었음 (스킵)
