## Why

RAG 출처 응답(`event: sources`)에 페이지 번호가 없어 사용자가 PDF 원본에서 해당 내용을 직접 찾기 어렵다. `file_chunks.page_number`를 추가해 청킹 시 PDF 페이지 정보를 보존하고, sources 이벤트에 `page_number`를 포함함으로써 출처 추적성을 높인다.

## What Changes

- `file_chunks` 테이블에 `page_number` Integer nullable 컬럼 추가 (PDF는 1-based 페이지 번호, 비PDF는 null)
- `file_parser.py` — MarkItDown 전체 텍스트 반환 방식을 PDF에 한해 pypdf 페이지별 추출로 교체, `[(page_num, text)]` 리스트 반환
- `file_service.py` — 청킹 루프에서 `page_number`를 `FileChunk` 레코드에 함께 저장
- `rag_service.py` — sources 딕셔너리에 `page_number` 필드 추가
- Alembic 마이그레이션 스크립트 생성 (`alembic revision --autogenerate`)

## Capabilities

### Modified Capabilities

- `file-upload`: 청킹 파이프라인이 PDF 페이지 번호를 보존하여 `file_chunks` 레코드에 저장
- `chat-message`: `event: sources` 이벤트의 각 항목에 `page_number` 필드 추가

## Impact

- `app/db/models/file_chunk.py` — `page_number` 컬럼 추가
- `app/utils/file_parser.py` — PDF 파싱 로직 교체
- `app/services/file_service.py` — 청킹 시 `page_number` 저장
- `app/services/rag_service.py` — sources 직렬화에 `page_number` 포함
- `app/schemas/` — sources 응답 스키마에 `page_number` 추가
- `alembic/versions/` — 신규 마이그레이션 파일

## Meta

- feature: add-page-number
- type: backend
- package: .

프리로드: folder-conventions.md · dev-flow.md · forbidden-patterns.md
