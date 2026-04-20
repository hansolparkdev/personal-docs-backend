## 1. DB 모델 및 마이그레이션

- [ ] 1.1 pgvector 확장 활성화 및 SQLAlchemy Base 설정 확인
  - 수정 파일: `app/db/base.py`

- [ ] 1.2 `files` ORM 모델 작성 (id, user_id, filename, content_type, size_bytes, minio_path, index_status enum, created_at, deleted_at)
  - 수정 파일: `app/db/models/file.py`

- [ ] 1.3 `file_chunks` ORM 모델 작성 (id, file_id FK CASCADE, user_id, chunk_index, content, embedding vector(1536))
  - 수정 파일: `app/db/models/file_chunk.py`

- [ ] 1.4 Alembic 마이그레이션 생성 — pgvector 확장, files, file_chunks 테이블 및 인덱스(user_id, embedding ivfflat)
  - 수정 파일: `alembic/versions/<revision>_add_files_and_file_chunks.py`

## 2. Pydantic 스키마

- [ ] 2.1 파일 업로드 응답, 목록 응답, 단건 응답, 다운로드 URL 응답 스키마 정의
  - 수정 파일: `app/schemas/file.py`

## 3. 유틸리티 — MarkItDown 래퍼

- [ ] 3.1 MarkItDown 인스턴스를 통해 파일 바이트를 Markdown 문자열로 변환하는 함수 작성; 미지원 포맷은 `UnsupportedFormatError` 발생
  - 수정 파일: `app/utils/file_parser.py`

## 4. 서비스 레이어

- [ ] 4.1 MinIO 클라이언트 초기화 및 버킷 존재 보장 로직 작성
  - 수정 파일: `app/services/file_service.py`

- [ ] 4.2 파일 업로드 서비스: MinIO 원본 저장 → DB files 레코드 생성(pending) → 반환
  - 수정 파일: `app/services/file_service.py`

- [ ] 4.3 임베딩 색인 서비스: MarkItDown 변환 → LangChain 청킹 → OpenAI 임베딩 → file_chunks 벌크 저장 → index_status 갱신
  - 수정 파일: `app/services/file_service.py`

- [ ] 4.4 파일 목록 조회 서비스: user_id 필터로 files 전체 반환
  - 수정 파일: `app/services/file_service.py`

- [ ] 4.5 파일 단건 조회 서비스: user_id + file_id 필터, 없으면 None 반환
  - 수정 파일: `app/services/file_service.py`

- [ ] 4.6 파일 삭제 서비스: MinIO 객체 삭제 → file_chunks CASCADE 삭제 → files 레코드 삭제
  - 수정 파일: `app/services/file_service.py`

- [ ] 4.7 presigned URL 생성 서비스: MinIO generate_presigned_url (유효시간 3600초)
  - 수정 파일: `app/services/file_service.py`

- [ ] 4.8 RAG 내부 인터페이스: user_id 기준 indexed 상태 file_chunks 조회 함수 (외부 API 아님)
  - 수정 파일: `app/services/file_service.py`

## 5. API 라우터

- [ ] 5.1 `POST /api/v1/files` 엔드포인트: 파일 크기·MIME 검증 → 업로드 서비스 호출 → BackgroundTasks로 임베딩 색인 등록 → 201 응답
  - 수정 파일: `app/api/v1/files.py`

- [ ] 5.2 `GET /api/v1/files` 엔드포인트: 목록 조회 서비스 호출 → 200 응답
  - 수정 파일: `app/api/v1/files.py`

- [ ] 5.3 `GET /api/v1/files/{file_id}` 엔드포인트: 단건 조회 서비스 호출 → 없으면 404 → 200 응답
  - 수정 파일: `app/api/v1/files.py`

- [ ] 5.4 `DELETE /api/v1/files/{file_id}` 엔드포인트: 소유권 확인 후 삭제 서비스 호출 → 없으면 404 → 204 응답
  - 수정 파일: `app/api/v1/files.py`

- [ ] 5.5 `GET /api/v1/files/{file_id}/download` 엔드포인트: 소유권 확인 후 presigned URL 반환 → 없으면 404 → 200 응답
  - 수정 파일: `app/api/v1/files.py`

- [ ] 5.6 files 라우터를 v1 라우터에 등록
  - 수정 파일: `app/api/v1/router.py`

## 6. 설정 및 의존성

- [ ] 6.1 MinIO 접속 정보(endpoint, access_key, secret_key, bucket_name), OpenAI API key, 파일 업로드 제한(max_size_bytes, allowed_mime_types) 환경변수 추가
  - 수정 파일: `app/core/config.py`, `.env.example`

- [ ] 6.2 `requirements.txt`에 `markitdown[all]`, `langchain`, `langchain-openai`, `pgvector`, `minio`, `sqlalchemy[asyncio]`, `asyncpg` 추가
  - 수정 파일: `requirements.txt`
