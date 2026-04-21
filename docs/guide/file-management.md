# 파일 관리

## 전체 파일 처리 흐름

```
[클라이언트]          [FastAPI]              [MinIO]      [MarkItDown]   [OpenAI]     [PostgreSQL]

POST /api/v1/files
  multipart/form-data
        |
        +--(유효성 검사)--
        |  - MIME 타입 확인
        |  - 크기 50MB 이하
        |
        +--(MinIO 업로드)-------------------------> 저장
        |   경로: {user_id}/{file_id}/{filename}
        |
        +--(DB 레코드 생성)--------------------------------------------> files 테이블
        |   index_status = "pending"
        |
        <-- 201 FileUploadResponse
        |
        +--(백그라운드 작업 시작: index_file)
              |
              +--(상태 변경)---------------------------------------> index_status = "indexing"
              |
              +--(파일 읽기)-------------------> MinIO에서 바이트 읽기
              |
              +--(파싱)-----------------------------> MarkItDown으로 Markdown 변환
              |
              +--(청크 분할)
              |   chunk_size=1000, chunk_overlap=200
              |   RecursiveCharacterTextSplitter 사용
              |
              +--(임베딩 생성)--------------------------------> OpenAI text-embedding-3-small
              |                                               <-- 1536차원 벡터 배열
              |
              +--(청크/벡터 저장)-----------------------------> file_chunks 테이블 (pgvector)
              |
              +--(상태 변경)---------------------------------------> index_status = "indexed"
```

---

## index_status 상태 전이

파일의 색인 처리 상태는 `files.index_status` 컬럼으로 추적됩니다.

```
[업로드 직후]
    pending
       |
       v (백그라운드 작업 시작)
    indexing
       |
       +--------> indexed      (파싱 + 임베딩 + 저장 성공)
       |
       +--------> failed       (MinIO 읽기 실패 또는 파싱/임베딩 오류)
       |
       +--------> unsupported  (MarkItDown이 해당 파일 포맷을 지원하지 않음)
```

| 상태 | 의미 | RAG 검색 가능 여부 |
|---|---|---|
| `pending` | 업로드 완료, 색인 대기 중 | 불가 |
| `indexing` | 현재 색인 처리 중 | 불가 |
| `indexed` | 색인 완료, RAG 사용 가능 | 가능 |
| `failed` | 처리 중 오류 발생 | 불가 |
| `unsupported` | 지원되지 않는 파일 포맷 | 불가 |

---

## 지원 파일 포맷

업로드 가능한 파일 형식은 서버 측에서 MIME 타입으로 제한합니다.

| MIME 타입 | 파일 형식 | 확장자 |
|---|---|---|
| `application/pdf` | PDF 문서 | .pdf |
| `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | Word 문서 | .docx |
| `application/vnd.openxmlformats-officedocument.presentationml.presentation` | PowerPoint | .pptx |
| `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | Excel | .xlsx |
| `text/markdown` | Markdown | .md |
| `text/plain` | 텍스트 | .txt |

최대 파일 크기: **50MB** (`MAX_UPLOAD_SIZE_BYTES=52428800`)

---

## API별 curl 예시

### 파일 업로드

```bash
curl -X POST http://localhost:8000/api/v1/files \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@/path/to/document.pdf"
```

응답 예시 (201 Created):
```json
{
  "file_id": "123e4567-e89b-12d3-a456-426614174000",
  "filename": "document.pdf",
  "index_status": "pending",
  "created_at": "2026-04-20T10:00:00Z"
}
```

### 파일 목록 조회

로그인한 유저의 삭제되지 않은 파일 목록을 반환합니다.

```bash
curl http://localhost:8000/api/v1/files \
  -H "Authorization: Bearer <access_token>"
```

응답 예시 (200 OK):
```json
[
  {
    "file_id": "123e4567-e89b-12d3-a456-426614174000",
    "filename": "document.pdf",
    "content_type": "application/pdf",
    "size_bytes": 102400,
    "index_status": "indexed",
    "created_at": "2026-04-20T10:00:00Z"
  },
  {
    "file_id": "234f5678-e89b-12d3-a456-426614174001",
    "filename": "notes.md",
    "content_type": "text/markdown",
    "size_bytes": 2048,
    "index_status": "indexed",
    "created_at": "2026-04-20T10:05:00Z"
  }
]
```

### 파일 상세 조회

```bash
curl http://localhost:8000/api/v1/files/123e4567-e89b-12d3-a456-426614174000 \
  -H "Authorization: Bearer <access_token>"
```

응답 예시 (200 OK):
```json
{
  "file_id": "123e4567-e89b-12d3-a456-426614174000",
  "filename": "document.pdf",
  "content_type": "application/pdf",
  "size_bytes": 102400,
  "index_status": "indexed",
  "created_at": "2026-04-20T10:00:00Z",
  "minio_path": "user-auth-id/123e4567-e89b-12d3-a456-426614174000/document.pdf"
}
```

### 다운로드 URL 발급

MinIO Presigned URL(유효 시간 1시간)을 발급합니다.

```bash
curl http://localhost:8000/api/v1/files/123e4567-e89b-12d3-a456-426614174000/download \
  -H "Authorization: Bearer <access_token>"
```

응답 예시 (200 OK):
```json
{
  "download_url": "http://localhost:9000/personal-docs/user-auth-id/123e4567.../document.pdf?X-Amz-Signature=...",
  "expires_in": 3600
}
```

### 파일 삭제

MinIO에서 원본 파일을 삭제하고 DB 레코드도 완전히 삭제합니다. 연결된 `file_chunks` 레코드는 CASCADE로 자동 삭제됩니다.

```bash
curl -X DELETE http://localhost:8000/api/v1/files/123e4567-e89b-12d3-a456-426614174000 \
  -H "Authorization: Bearer <access_token>"
```

응답: 204 No Content (본문 없음)

---

## 오류 응답

| HTTP 상태 | 발생 조건 |
|---|---|
| 401 Unauthorized | 토큰 없음 또는 무효 |
| 404 Not Found | 파일이 존재하지 않거나 다른 유저의 파일 |
| 413 Request Entity Too Large | 파일이 50MB 초과 |
| 415 Unsupported Media Type | 허용되지 않는 MIME 타입 |

---

## 파일 격리 정책

모든 파일 API는 현재 로그인한 유저의 파일만 접근할 수 있습니다. `file_service.py`의 조회 함수들은 반드시 `user_id` 조건을 포함하므로 다른 유저의 파일에는 접근이 불가능합니다.

```python
# file_service.py 내 소유권 검증 예시
select(File).where(
    File.id == file_id,
    File.user_id == user_id,   # 유저 격리
    File.deleted_at.is_(None), # 소프트 삭제 필터
)
```
