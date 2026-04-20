## Context

현재 프로젝트는 FastAPI 스캐폴딩만 존재하며, DB 모델·서비스·라우터가 아직 구현되지 않았다. PostgreSQL + pgvector, MinIO, Keycloak JWT 인프라는 docker-compose로 준비되어 있고, LangChain/MarkItDown은 requirements.txt에 추가 예정이다.

## Goals / Non-Goals

**Goals:**
- 사용자별 파일 원본을 MinIO에 안전하게 보관한다
- 지원 포맷(PDF, DOCX, PPTX, XLSX, MD, TXT)은 MarkItDown으로 Markdown 변환 후 LangChain 청킹 → pgvector 임베딩 색인한다
- 모든 파일 접근은 JWT sub(user_id)로 소유권 검증 후에만 허용한다
- 삭제 시 MinIO 원본·DB 메타데이터·file_chunks를 일괄 제거하여 RAG 응답에서 완전 배제한다
- 파일 다운로드는 MinIO presigned URL로만 제공한다 (서버 직접 스트림 금지)

**Non-Goals:**
- 파일 내용 수정·버전 관리·폴더/태그
- 이미지·오디오·영상 내용 기반 검색
- 관리자 전체 파일 조회
- 업로드 용량/요금제 관리
- 파일 공유·권한 위임

## Decisions

### 1. DB 모델 — files / file_chunks 분리

`files` 테이블은 파일 메타데이터와 처리 상태만 보관하고, 청크·임베딩은 `file_chunks`에 분리한다.

**이유**: 파일 삭제 시 `WHERE file_id = ?`로 청크 일괄 삭제가 간단하다. 임베딩 컬럼(vector 1536)은 행이 많아지면 크기가 커지므로 메타데이터와 분리해야 목록 조회 쿼리가 가볍다.

`files` 스키마:
- `id`: UUID, PK
- `user_id`: str (Keycloak sub), NOT NULL, 인덱스
- `filename`: str (원본 파일명)
- `content_type`: str (MIME)
- `size_bytes`: int
- `minio_path`: str (`{user_id}/{file_id}/{filename}`)
- `index_status`: enum (`pending` / `indexing` / `indexed` / `failed` / `unsupported`)
- `created_at`: datetime (UTC)
- `deleted_at`: datetime | NULL (soft delete 보조용; 현재는 hard delete)

`file_chunks` 스키마:
- `id`: UUID, PK
- `file_id`: UUID, FK → files.id ON DELETE CASCADE
- `user_id`: str (검색 시 JOIN 없이 필터 가능하도록 역정규화)
- `chunk_index`: int
- `content`: text
- `embedding`: vector(1536)

### 2. index_status enum — pending 시작

업로드 완료 시 즉시 `pending`으로 기록하고, 백그라운드 태스크가 `indexing` → `indexed` / `failed` / `unsupported`로 전이한다.

**이유**: 업로드 API 응답 지연을 최소화한다. 사용자는 업로드 완료 즉시 응답을 받고, 목록 조회로 상태를 확인한다. 동기 처리는 대용량 파일에서 타임아웃 위험이 있어 배제한다.

### 3. 파일 처리 파이프라인 — MarkItDown → LangChain RecursiveCharacterTextSplitter

MarkItDown(`markitdown[all]`)으로 파일을 Markdown 변환한 뒤 LangChain `RecursiveCharacterTextSplitter`(chunk_size=1000, chunk_overlap=200)로 청크 분할하고 OpenAI `text-embedding-3-small`(1536 차원)로 임베딩한다.

**이유**: MarkItDown은 PDF·DOCX·PPTX·XLSX·MD·TXT를 단일 인터페이스로 처리한다. RecursiveCharacterTextSplitter는 문단·문장·단어 순으로 분할해 의미 경계를 최대한 보존한다. text-embedding-3-small은 비용 대비 성능이 우수하고 1536 차원은 pgvector 기본 설정과 일치한다.

### 4. 백그라운드 처리 — FastAPI BackgroundTasks

임베딩 색인을 `BackgroundTasks`로 분리한다. 별도 큐(Celery 등) 없이 FastAPI 내장 기능만 사용한다.

**이유**: 초기 단계에서 외부 큐 인프라 추가는 복잡도 과잉이다. `BackgroundTasks`는 응답 반환 후 같은 프로세스에서 실행되어 추가 설정 없이 비동기 처리가 가능하다. 트래픽이 증가하면 Celery/ARQ로 교체한다.

### 5. 파일 다운로드 — MinIO presigned URL

`GET /api/v1/files/{file_id}/download`는 MinIO presigned URL(유효시간 1시간)을 JSON으로 반환한다. 서버가 바이트를 스트림하지 않는다.

**이유**: forbidden-patterns.md에 "MinIO presigned URL 없이 파일 직접 노출 금지" 명시. presigned URL은 서버 대역폭을 절약하고 MinIO가 직접 클라이언트에 전달하므로 성능이 우수하다.

### 6. 소유권 검증 — 404 통일 (403 미사용)

타인 파일 접근 시도 시 404로 응답한다.

**이유**: 403은 해당 리소스가 존재함을 노출한다. 404로 통일하면 파일 존재 여부 자체를 숨겨 정보 노출을 방지한다. plan.md Open Questions에서 "없음과 동일한 응답" 방향을 지시하고 있다.

### 7. 삭제 처리 — Hard Delete + CASCADE

파일 삭제는 hard delete로 처리한다. `file_chunks`는 FK CASCADE로 함께 삭제되고, MinIO 원본은 서비스 레이어에서 명시적으로 제거한다.

**이유**: 개인 문서는 삭제 후 RAG 응답에서 즉시 배제되어야 한다. Soft delete는 필터 누락 위험이 있다. MinIO 삭제 실패 시 DB 트랜잭션을 롤백하여 불일치를 방지한다.

### 8. 중복 업로드 — 허용 (중복 판단 없음)

동일 파일명·동일 내용이라도 별도 file_id로 저장한다.

**이유**: plan.md Open Questions에서 중복 판단 기준이 미결이다. 해시 계산은 대용량 파일에서 업로드 지연을 유발한다. 1차 구현에서는 허용하고 추후 정책을 추가한다.

## Risks / Trade-offs

- [BackgroundTasks 실패]: 색인 실패 시 재시도 메커니즘 없음 → index_status를 `failed`로 기록하고, 추후 재색인 엔드포인트로 보완
- [MinIO-DB 불일치]: MinIO 삭제 실패 후 DB 커밋 완료 시 원본이 MinIO에 잔존 → 삭제를 MinIO 먼저 수행하고 성공 후 DB commit; MinIO 실패 시 500 반환
- [presigned URL 유효시간]: 1시간 URL을 클라이언트가 캐시하면 파일 삭제 후에도 접근 가능 → 허용(삭제 후 MinIO 객체 제거로 URL 무효화됨)
- [1536 차원 고정]: 임베딩 모델 교체 시 기존 벡터와 차원 불일치 → 모델 교체 시 전체 재색인 필요; 현재는 단일 모델만 지원
