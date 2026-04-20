## Why

RAG 챗이 의미 있는 응답을 생성하려면 사용자가 자신의 문서를 업로드·관리하고 시스템이 이를 검색 가능한 벡터로 색인하는 경로가 선행되어야 한다. 현재 시스템에는 사용자별 파일 수용·보관·임베딩 색인 파이프라인이 없어 RAG 챗이 근거 없이 응답하게 된다.

## What Changes

- `files` 테이블(UUID PK, user_id, filename, content_type, size_bytes, minio_path, index_status, created_at, deleted_at) 신설
- `file_chunks` 테이블(UUID PK, file_id FK, user_id, chunk_index, content, embedding vector(1536)) 신설
- Alembic 마이그레이션으로 두 테이블 및 pgvector 확장 적용
- 파일 업로드 API: MinIO 원본 저장 후 MarkItDown 파싱 → LangChain 청킹 → pgvector 임베딩 색인 (백그라운드 처리)
- 파일 목록·단건 조회 API: 소유자 user_id 필터 적용
- 파일 삭제 API: MinIO 원본 + DB 메타데이터 + file_chunks 일괄 제거
- 파일 다운로드 API: MinIO presigned URL 반환 (서버 직접 노출 금지)
- 미지원 포맷은 원본만 MinIO 보관, index_status = "unsupported"로 기록
- RAG 서비스에서 소유자의 indexed 청크를 조회하는 내부 인터페이스 노출

## Capabilities

### New Capabilities

- `file-upload`: 인증 사용자가 파일을 업로드하면 MinIO에 원본을 저장하고 백그라운드에서 텍스트 추출·임베딩 색인을 수행한다
- `file-list`: 인증 사용자가 자신이 업로드한 파일 목록과 각 파일의 index_status를 조회한다
- `file-delete`: 인증 사용자가 자신의 파일을 삭제하면 MinIO 원본·DB 메타데이터·file_chunks가 일괄 제거된다
- `file-download`: 인증 사용자가 자신의 파일을 재내려받을 수 있도록 MinIO presigned URL을 반환한다

### Modified Capabilities

없음 (신규 기능)

## Impact

- 신규 파일: `app/db/models/file.py`, `app/db/models/file_chunk.py`
- 신규 파일: `app/api/v1/files.py`
- 신규 파일: `app/services/file_service.py`
- 신규 파일: `app/schemas/file.py`
- 신규 파일: `app/utils/file_parser.py` (MarkItDown 래퍼)
- 수정 파일: `app/api/v1/router.py` (files 라우터 등록)
- 신규 파일: `alembic/versions/<revision>_add_files_and_file_chunks.py`
- 신규 파일: `tests/test_files.py`

## Meta

- feature: file-management
- type: backend
- package: backend

프리로드: folder-conventions.md · dev-flow.md · forbidden-patterns.md
