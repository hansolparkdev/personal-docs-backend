# 주요 파이썬 코드 사용법

이 문서는 백엔드의 주요 서비스 모듈과 유틸리티를 직접 사용하는 방법을 설명합니다. 새 기능을 개발하거나 기존 코드를 이해할 때 참고하세요.

---

## file_parser.py — MarkItDown 래퍼 사용법

`app/utils/file_parser.py`는 다양한 파일 포맷을 Markdown 텍스트로 변환하는 유틸리티입니다.

### 함수 시그니처

```python
def parse_to_markdown(content: bytes, filename: str) -> str:
    """
    파일 바이트를 Markdown 텍스트로 변환합니다.

    Args:
        content: 파일 원본 바이트
        filename: 원본 파일명 (확장자로 포맷 판별)

    Returns:
        변환된 Markdown 문자열

    Raises:
        UnsupportedFormatError: 지원하지 않는 포맷이거나 변환 실패 시
    """
```

### 사용 예시

```python
from app.utils.file_parser import UnsupportedFormatError, parse_to_markdown

# 파일 바이트 읽기
with open("document.pdf", "rb") as f:
    content = f.read()

# Markdown으로 변환
try:
    markdown_text = parse_to_markdown(content, "document.pdf")
    print(markdown_text[:500])  # 앞 500자 출력
except UnsupportedFormatError as e:
    print(f"변환 실패: {e}")
```

### 동작 방식

1. 파일명의 확장자를 추출합니다 (예: `.pdf`, `.docx`).
2. 임시 파일로 저장한 뒤 MarkItDown 라이브러리로 변환합니다.
3. 변환 완료 후 임시 파일을 삭제합니다.
4. 변환 실패 또는 지원하지 않는 포맷이면 `UnsupportedFormatError`를 발생시킵니다.

---

## file_service.py — 주요 함수 설명

`app/services/file_service.py`는 파일 업로드, 조회, 삭제, 색인 처리를 담당합니다. 모든 함수는 비동기(`async`)입니다.

### upload_file — 파일 업로드

MinIO에 파일을 저장하고 DB에 레코드를 생성합니다.

```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.file_service import upload_file

async def example(db: AsyncSession):
    db_file = await upload_file(
        db=db,
        user_id="keycloak-sub-uuid",   # JWT payload의 sub 값
        filename="report.pdf",
        content_type="application/pdf",
        size_bytes=102400,
        content=b"...",                 # 파일 바이트
    )
    print(db_file.id)           # UUID
    print(db_file.minio_path)   # "{user_id}/{file_id}/report.pdf"
    print(db_file.index_status) # IndexStatus.pending
```

### index_file — 파일 색인 (백그라운드)

파일을 파싱하고 임베딩을 생성하여 pgvector에 저장합니다. 일반적으로 FastAPI `BackgroundTasks`로 호출합니다.

```python
import uuid
from app.services.file_service import index_file

# API 핸들러에서 백그라운드로 실행
background_tasks.add_task(index_file, db, file_uuid)

# 또는 직접 호출 (테스트/스크립트)
await index_file(db, uuid.UUID("123e4567-e89b-12d3-a456-426614174000"))
```

### list_files — 파일 목록 조회

```python
from app.services.file_service import list_files

files = await list_files(db=db, user_id="keycloak-sub-uuid")
for f in files:
    print(f.filename, f.index_status)
```

### get_file — 단건 조회 (소유권 확인 포함)

```python
import uuid
from app.services.file_service import get_file

db_file = await get_file(
    db=db,
    user_id="keycloak-sub-uuid",
    file_id=uuid.UUID("123e4567-e89b-12d3-a456-426614174000"),
)
if db_file is None:
    print("파일 없음 또는 접근 권한 없음")
```

### delete_file — 파일 삭제

MinIO에서 먼저 삭제 후 DB 레코드를 삭제합니다.

```python
from app.services.file_service import delete_file

deleted = await delete_file(
    db=db,
    user_id="keycloak-sub-uuid",
    file_id=uuid.UUID("123e4567-..."),
)
print("삭제 성공" if deleted else "파일 없음")
```

### get_download_url — Presigned URL 발급

```python
from app.services.file_service import get_download_url

url = await get_download_url(
    db=db,
    user_id="keycloak-sub-uuid",
    file_id=uuid.UUID("123e4567-..."),
)
# url: MinIO Presigned URL (1시간 유효)
```

---

## rag_service.py — stream_rag_response 사용법

`app/services/rag_service.py`의 `stream_rag_response`는 비동기 제너레이터로, SSE 이벤트 문자열을 순차적으로 yield합니다.

### 함수 시그니처

```python
async def stream_rag_response(
    db: AsyncSession,
    session_id: uuid.UUID,
    user_id: str,
    query: str,
) -> AsyncGenerator[str, None]:
    """SSE 이벤트를 순서대로 yield합니다: token* → sources → done (또는 error)"""
```

### FastAPI StreamingResponse와 함께 사용

```python
from fastapi.responses import StreamingResponse
from app.services.rag_service import stream_rag_response

@router.post("/{session_id}/messages")
async def send_message(session_id: uuid.UUID, body: SendMessageRequest, ...):
    return StreamingResponse(
        stream_rag_response(db, session_id, current_user.auth_id, body.content),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

### 직접 이터레이션 (테스트/스크립트)

```python
from app.services.rag_service import stream_rag_response

async def run_rag():
    async for event in stream_rag_response(db, session_id, user_id, "질문 내용"):
        print(event, end="")
        # 예시 출력:
        # event: token
        # data: {"text": "안녕"}
        #
        # event: done
        # data: {}
        #
```

---

## chat_service.py — 세션/메시지 CRUD

`app/services/chat_service.py`는 챗 세션과 메시지의 DB CRUD를 담당합니다.

### 세션 생성

```python
from app.services.chat_service import create_session

session = await create_session(db, user_id="keycloak-sub-uuid")
print(session.id)     # UUID
print(session.title)  # None (첫 메시지 전송 시 자동 설정)
```

### 세션 목록 조회

```python
from app.services.chat_service import list_sessions

sessions = await list_sessions(db, user_id="keycloak-sub-uuid", limit=50)
# updated_at 내림차순 정렬
```

### 세션 단건 조회

```python
from app.services.chat_service import get_session, get_session_with_messages

# 메시지 없이 세션만
session = await get_session(db, session_id=uuid_obj, user_id="keycloak-sub-uuid")

# 메시지 포함 (N+1 쿼리 방지: selectinload 사용)
session = await get_session_with_messages(db, session_id=uuid_obj, user_id="keycloak-sub-uuid")
if session:
    for msg in session.messages:
        print(f"[{msg.role}] {msg.content}")
```

### 세션 제목 설정

```python
from app.services.chat_service import set_session_title

await set_session_title(db, session_id=uuid_obj, title="새 제목")
```

### 메시지 저장

```python
from app.services.chat_service import save_user_message, save_assistant_message

# 유저 메시지 저장
user_msg = await save_user_message(
    db, session_id=uuid_obj, user_id="keycloak-sub-uuid", content="질문 내용"
)

# 어시스턴트 메시지 저장 (sources 포함)
assistant_msg = await save_assistant_message(
    db,
    session_id=uuid_obj,
    user_id="keycloak-sub-uuid",
    content="답변 내용",
    sources=[{"file_id": "...", "filename": "", "chunk_index": 0}],
)
```

### 최근 메시지 조회

```python
from app.services.chat_service import get_recent_messages

# 최근 20개를 시간 오름차순으로 반환 (내부적으로 역정렬 후 reversed)
messages = await get_recent_messages(db, session_id=uuid_obj, limit=20)
for msg in messages:
    print(f"[{msg.role}] {msg.content}")
```

---

## keycloak_service.py — Keycloak API 호출

`app/services/keycloak_service.py`는 Keycloak과의 모든 HTTP 통신을 담당합니다.

### 서비스 계정 토큰 발급 (Admin API용)

```python
from app.services.keycloak_service import get_service_account_token

# Client Credentials grant로 Admin API 접근 토큰 발급
admin_token = await get_service_account_token()
```

### 유저 생성 (Admin API)

```python
from app.services.keycloak_service import (
    create_keycloak_user,
    get_service_account_token,
    ConflictError,
)

try:
    token = await get_service_account_token()
    await create_keycloak_user(
        token=token,
        username="newuser",
        email="newuser@example.com",
        password="securepassword123",
        name="새 유저",
    )
except ConflictError:
    print("이미 존재하는 username 또는 email")
```

### 비밀번호 로그인 (Password Grant)

```python
from app.services.keycloak_service import password_grant, UnauthorizedError

try:
    token_data = await password_grant("username", "password")
    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]
    expires_in = token_data["expires_in"]
except UnauthorizedError:
    print("잘못된 인증 정보")
```

### 토큰 갱신 (Refresh Grant)

```python
from app.services.keycloak_service import refresh_grant

token_data = await refresh_grant(refresh_token="기존_refresh_token")
new_access_token = token_data["access_token"]
```

### Authorization Code 교환 (SSO 콜백)

```python
from app.services.keycloak_service import exchange_code, InvalidCodeError

try:
    token_data = await exchange_code(
        code="authorization_code",
        redirect_uri="http://localhost:3000/callback",
    )
except InvalidCodeError:
    print("잘못된 또는 만료된 코드")
```

### JWKS 관련

```python
from app.services.keycloak_service import get_jwks, invalidate_jwks_cache

# 공개키 목록 가져오기 (캐시 적용)
keys = await get_jwks()
# keys: {"kid1": {...}, "kid2": {...}}

# 캐시 강제 무효화 (JWT 검증 실패 시 재시도용)
invalidate_jwks_cache()
```

### 예외 클래스

| 예외 | 발생 조건 |
|---|---|
| `ConflictError` | 유저 생성 시 409 Conflict (중복 username/email) |
| `UnauthorizedError` | 비밀번호/토큰 오류 (401) |
| `KeycloakUnavailableError` | Keycloak 서버 응답 없음 (5xx) |
| `InvalidCodeError` | Authorization Code가 유효하지 않음 (400/401) |

---

## get_current_user 의존성 사용 방법

`app/core/dependencies.py`의 `get_current_user`는 FastAPI Dependency Injection을 통해 현재 인증된 유저를 주입합니다.

### 기본 사용

```python
from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user
from app.db.models.user import User

router = APIRouter()

@router.get("/my-resource")
async def get_my_resource(current_user: User = Depends(get_current_user)):
    # current_user는 DB에서 조회된 User 모델 인스턴스
    user_id = current_user.auth_id  # Keycloak JWT의 sub 값
    db_uuid = current_user.id       # PostgreSQL의 UUID PK
    username = current_user.username
    email = current_user.email
    return {"user_id": str(db_uuid), "username": username}
```

### Annotated 방식 (타입 힌트 활용)

```python
from typing import Annotated
from fastapi import Depends
from app.core.dependencies import get_current_user
from app.db.models.user import User

CurrentUser = Annotated[User, Depends(get_current_user)]

@router.get("/my-resource")
async def get_my_resource(current_user: CurrentUser):
    return {"username": current_user.username}
```

### 동작 흐름

1. `Authorization: Bearer <token>` 헤더에서 토큰 추출
2. `verify_token(token)` 호출 → JWKS로 서명 검증
3. JWT payload의 `sub` 값을 `auth_id`로 사용
4. DB에서 `users.auth_id = sub`인 유저 조회
5. 유저가 없으면 `HTTP 404` 반환
6. 유저 객체를 핸들러에 주입

### DB 세션 함께 사용

```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import get_db

@router.post("/resource")
async def create_resource(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_id = current_user.auth_id
    # db와 current_user 모두 사용 가능
```
