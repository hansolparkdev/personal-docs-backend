# API 정의서

> 작성일: 2026-04-20  
> 대상: 프론트엔드 개발자  
> 버전: v1

---

## 목차

1. [공통 사항](#공통-사항)
2. [인증 (Auth)](#1-인증-auth)
   - [POST /api/v1/auth/register — 회원가입](#post-apiv1authregister--회원가입)
   - [POST /api/v1/auth/login — 로그인](#post-apiv1authlogin--로그인)
   - [POST /api/v1/auth/refresh — 토큰 갱신](#post-apiv1authrefresh--토큰-갱신)
   - [GET /api/v1/auth/callback — SSO 콜백](#get-apiv1authcallback--sso-콜백)
   - [GET /api/v1/auth/me — 내 정보 조회](#get-apiv1authme--내-정보-조회)
3. [파일 관리 (Files)](#2-파일-관리-files)
   - [POST /api/v1/files — 파일 업로드](#post-apiv1files--파일-업로드)
   - [GET /api/v1/files — 파일 목록](#get-apiv1files--파일-목록)
   - [GET /api/v1/files/{file_id} — 파일 단건 조회](#get-apiv1filesfile_id--파일-단건-조회)
   - [DELETE /api/v1/files/{file_id} — 파일 삭제](#delete-apiv1filesfile_id--파일-삭제)
   - [GET /api/v1/files/{file_id}/download — 다운로드 URL](#get-apiv1filesfile_iddownload--다운로드-url)
4. [챗 (Chat)](#3-챗-chat)
   - [POST /api/v1/chats — 세션 생성](#post-apiv1chats--세션-생성)
   - [GET /api/v1/chats — 세션 목록](#get-apiv1chats--세션-목록)
   - [GET /api/v1/chats/{session_id} — 세션 단건 조회](#get-apiv1chatssession_id--세션-단건-조회)
   - [DELETE /api/v1/chats/{session_id} — 세션 삭제](#delete-apiv1chatssession_id--세션-삭제)
   - [POST /api/v1/chats/{session_id}/messages — 메시지 전송 (SSE)](#post-apiv1chatssession_idmessages--메시지-전송-sse)
5. [부록](#부록)
   - [index_status 상태 정의](#index_status-상태-정의)
   - [SSE 이벤트 형식](#sse-이벤트-형식)
   - [파일 지원 포맷](#파일-지원-포맷)

---

## 공통 사항

### Base URL

```
http://localhost:8000
```

### 인증 방식

인증이 필요한 API는 요청 헤더에 Keycloak에서 발급된 JWT Access Token을 포함해야 합니다.

```
Authorization: Bearer <access_token>
```

- 로그인(`POST /api/v1/auth/login`) 또는 회원가입(`POST /api/v1/auth/register`) 응답의 `access_token` 값을 사용합니다.
- Access Token 만료 시 `POST /api/v1/auth/refresh`로 갱신합니다.

### 공통 에러 코드

| 상태 코드 | 설명 |
|-----------|------|
| `400 Bad Request` | 잘못된 요청 파라미터 (SSO 코드 오류 등) |
| `401 Unauthorized` | 인증 실패 (잘못된 자격증명, 만료된 토큰) |
| `404 Not Found` | 요청한 리소스가 존재하지 않거나 접근 권한 없음 |
| `409 Conflict` | 이미 존재하는 리소스 (중복 이메일/사용자명) |
| `413 Request Entity Too Large` | 파일 크기 초과 (최대 50MB) |
| `415 Unsupported Media Type` | 지원하지 않는 파일 형식 |
| `422 Unprocessable Entity` | 요청 바디 유효성 검사 실패 |
| `500 Internal Server Error` | 서버 내부 오류 |
| `502 Bad Gateway` | Keycloak 서버 연결 실패 |

에러 응답 공통 형식:

```json
{
  "detail": "에러 메시지"
}
```

### Content-Type

| 요청 유형 | Content-Type |
|-----------|--------------|
| 일반 JSON 요청 | `application/json` |
| 파일 업로드 | `multipart/form-data` |
| SSE 응답 스트림 | `text/event-stream` |

---

## 1. 인증 (Auth)

### POST /api/v1/auth/register — 회원가입

**설명**: Keycloak에 새 사용자를 생성하고 DB에 등록합니다.  
**인증 필요**: 불필요

**요청**

- Headers

  | 헤더 | 값 |
  |------|-----|
  | `Content-Type` | `application/json` |

- Body

  | 필드명 | 타입 | 필수 | 설명 |
  |--------|------|------|------|
  | `username` | string | Y | 사용자 아이디 (3~50자) |
  | `email` | string | Y | 이메일 주소 (유효한 이메일 형식) |
  | `password` | string | Y | 비밀번호 (최소 8자) |
  | `name` | string | N | 표시 이름 |

**응답**

- 성공 `201 Created`

  ```json
  {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "hansol",
    "email": "hansol@example.com",
    "name": "박한솔",
    "created_at": "2026-04-20T10:00:00Z",
    "last_login_at": "2026-04-20T10:00:00Z"
  }
  ```

- 실패 케이스

  | 상태 코드 | 원인 |
  |-----------|------|
  | `409 Conflict` | 동일한 username 또는 email이 이미 Keycloak에 존재함 |
  | `422 Unprocessable Entity` | 필드 유효성 검사 실패 (username 길이 미달, 이메일 형식 오류, 비밀번호 8자 미만 등) |
  | `502 Bad Gateway` | Keycloak 서버 연결 실패 |

**예시**

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "hansol",
    "email": "hansol@example.com",
    "password": "secure1234",
    "name": "박한솔"
  }'
```

---

### POST /api/v1/auth/login — 로그인

**설명**: 사용자명/비밀번호로 Keycloak 인증 후 JWT 토큰을 발급합니다.  
**인증 필요**: 불필요

**요청**

- Headers

  | 헤더 | 값 |
  |------|-----|
  | `Content-Type` | `application/json` |

- Body

  | 필드명 | 타입 | 필수 | 설명 |
  |--------|------|------|------|
  | `username` | string | Y | 사용자 아이디 |
  | `password` | string | Y | 비밀번호 |

**응답**

- 성공 `200 OK`

  ```json
  {
    "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 300
  }
  ```

  | 필드명 | 타입 | 설명 |
  |--------|------|------|
  | `access_token` | string | API 호출 시 사용하는 JWT Access Token |
  | `refresh_token` | string | Access Token 갱신용 토큰 |
  | `token_type` | string | 토큰 타입 (항상 `"Bearer"`) |
  | `expires_in` | integer | Access Token 유효 시간 (초 단위, 기본 300초) |

- 실패 케이스

  | 상태 코드 | 원인 |
  |-----------|------|
  | `401 Unauthorized` | username 또는 password가 올바르지 않음 |
  | `422 Unprocessable Entity` | 필수 필드 누락 |
  | `502 Bad Gateway` | Keycloak 서버 연결 실패 |

**예시**

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "hansol",
    "password": "secure1234"
  }'
```

---

### POST /api/v1/auth/refresh — 토큰 갱신

**설명**: Refresh Token으로 만료된 Access Token을 갱신합니다.  
**인증 필요**: 불필요 (Refresh Token 사용)

**요청**

- Headers

  | 헤더 | 값 |
  |------|-----|
  | `Content-Type` | `application/json` |

- Body

  | 필드명 | 타입 | 필수 | 설명 |
  |--------|------|------|------|
  | `refresh_token` | string | Y | 로그인 시 발급받은 Refresh Token |

**응답**

- 성공 `200 OK`

  ```json
  {
    "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 300
  }
  ```

- 실패 케이스

  | 상태 코드 | 원인 |
  |-----------|------|
  | `401 Unauthorized` | Refresh Token이 만료되었거나 유효하지 않음 |
  | `422 Unprocessable Entity` | `refresh_token` 필드 누락 |
  | `502 Bad Gateway` | Keycloak 서버 연결 실패 |

**예시**

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

---

### GET /api/v1/auth/callback — SSO 콜백

**설명**: Keycloak SSO 로그인 후 Authorization Code를 Access Token으로 교환합니다. Keycloak이 직접 리다이렉트하는 엔드포인트이며, 일반적으로 프론트엔드가 직접 호출하지 않습니다.  
**인증 필요**: 불필요

**요청**

- Query Parameters

  | 파라미터 | 타입 | 필수 | 설명 |
  |----------|------|------|------|
  | `code` | string | Y | Keycloak이 전달한 Authorization Code |
  | `redirect_uri` | string | Y | 인증 요청 시 사용한 Redirect URI (URL 인코딩 필요) |

**응답**

- 성공 `200 OK`

  ```json
  {
    "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 300
  }
  ```

- 실패 케이스

  | 상태 코드 | 원인 |
  |-----------|------|
  | `400 Bad Request` | Authorization Code가 유효하지 않거나 만료됨 |
  | `422 Unprocessable Entity` | 필수 쿼리 파라미터 누락 |
  | `502 Bad Gateway` | Keycloak 서버 연결 실패 |

**예시**

```bash
curl "http://localhost:8000/api/v1/auth/callback?code=abc123&redirect_uri=http%3A%2F%2Flocalhost%3A3000%2Fcallback"
```

---

### GET /api/v1/auth/me — 내 정보 조회

**설명**: 현재 인증된 사용자의 정보를 반환합니다.  
**인증 필요**: 필요

**요청**

- Headers

  | 헤더 | 값 |
  |------|-----|
  | `Authorization` | `Bearer <access_token>` |

**응답**

- 성공 `200 OK`

  ```json
  {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "hansol",
    "email": "hansol@example.com",
    "name": "박한솔",
    "created_at": "2026-04-20T10:00:00Z",
    "last_login_at": "2026-04-20T11:30:00Z"
  }
  ```

  | 필드명 | 타입 | 설명 |
  |--------|------|------|
  | `user_id` | string (UUID) | 시스템 내부 사용자 ID |
  | `username` | string | 사용자 아이디 |
  | `email` | string | 이메일 주소 |
  | `name` | string \| null | 표시 이름 |
  | `created_at` | string (ISO 8601) | 계정 생성 일시 |
  | `last_login_at` | string (ISO 8601) \| null | 마지막 로그인 일시 |

- 실패 케이스

  | 상태 코드 | 원인 |
  |-----------|------|
  | `401 Unauthorized` | Authorization 헤더 누락 또는 토큰 만료/유효하지 않음 |

**예시**

```bash
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

## 2. 파일 관리 (Files)

### POST /api/v1/files — 파일 업로드

**설명**: 파일을 업로드합니다. 업로드 직후 백그라운드에서 벡터 인덱싱이 시작됩니다.  
**인증 필요**: 필요

**제한 사항**
- 최대 파일 크기: **50MB**
- 지원 파일 형식: [파일 지원 포맷](#파일-지원-포맷) 참조

**요청**

- Headers

  | 헤더 | 값 |
  |------|-----|
  | `Authorization` | `Bearer <access_token>` |
  | `Content-Type` | `multipart/form-data` |

- Body (multipart/form-data)

  | 필드명 | 타입 | 필수 | 설명 |
  |--------|------|------|------|
  | `file` | file | Y | 업로드할 파일 |

**응답**

- 성공 `201 Created`

  ```json
  {
    "file_id": "7f3c9a1b-2e4d-4f8a-b3c5-1d2e3f4a5b6c",
    "filename": "report.pdf",
    "index_status": "pending",
    "created_at": "2026-04-20T10:00:00Z"
  }
  ```

  | 필드명 | 타입 | 설명 |
  |--------|------|------|
  | `file_id` | string (UUID) | 파일 고유 ID |
  | `filename` | string | 원본 파일명 |
  | `index_status` | string | 벡터 인덱싱 상태 (초기값: `"pending"`) |
  | `created_at` | string (ISO 8601) | 업로드 일시 |

- 실패 케이스

  | 상태 코드 | 원인 |
  |-----------|------|
  | `401 Unauthorized` | 인증 토큰 없음 또는 유효하지 않음 |
  | `413 Request Entity Too Large` | 파일 크기가 50MB 초과 |
  | `415 Unsupported Media Type` | 지원하지 않는 파일 형식 |
  | `422 Unprocessable Entity` | `file` 필드 누락 |
  | `500 Internal Server Error` | MinIO 업로드 실패 등 서버 오류 |

**예시**

```bash
curl -X POST http://localhost:8000/api/v1/files \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -F "file=@/path/to/report.pdf"
```

```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const response = await fetch('http://localhost:8000/api/v1/files', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
  },
  body: formData,
});
```

---

### GET /api/v1/files — 파일 목록

**설명**: 현재 인증된 사용자가 업로드한 파일 목록을 반환합니다 (삭제된 파일 제외).  
**인증 필요**: 필요

**요청**

- Headers

  | 헤더 | 값 |
  |------|-----|
  | `Authorization` | `Bearer <access_token>` |

**응답**

- 성공 `200 OK`

  ```json
  [
    {
      "file_id": "7f3c9a1b-2e4d-4f8a-b3c5-1d2e3f4a5b6c",
      "filename": "report.pdf",
      "content_type": "application/pdf",
      "size_bytes": 204800,
      "index_status": "indexed",
      "created_at": "2026-04-20T10:00:00Z"
    },
    {
      "file_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "filename": "notes.txt",
      "content_type": "text/plain",
      "size_bytes": 1024,
      "index_status": "pending",
      "created_at": "2026-04-20T11:00:00Z"
    }
  ]
  ```

  각 항목 필드:

  | 필드명 | 타입 | 설명 |
  |--------|------|------|
  | `file_id` | string (UUID) | 파일 고유 ID |
  | `filename` | string | 원본 파일명 |
  | `content_type` | string | MIME 타입 |
  | `size_bytes` | integer | 파일 크기 (바이트) |
  | `index_status` | string | 벡터 인덱싱 상태 |
  | `created_at` | string (ISO 8601) | 업로드 일시 |

- 실패 케이스

  | 상태 코드 | 원인 |
  |-----------|------|
  | `401 Unauthorized` | 인증 토큰 없음 또는 유효하지 않음 |

**예시**

```bash
curl http://localhost:8000/api/v1/files \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### GET /api/v1/files/{file_id} — 파일 단건 조회

**설명**: 특정 파일의 상세 정보를 반환합니다. 다른 사용자의 파일은 조회할 수 없습니다.  
**인증 필요**: 필요

**요청**

- Headers

  | 헤더 | 값 |
  |------|-----|
  | `Authorization` | `Bearer <access_token>` |

- Path Parameters

  | 파라미터 | 타입 | 필수 | 설명 |
  |----------|------|------|------|
  | `file_id` | string (UUID) | Y | 조회할 파일의 ID |

**응답**

- 성공 `200 OK`

  ```json
  {
    "file_id": "7f3c9a1b-2e4d-4f8a-b3c5-1d2e3f4a5b6c",
    "filename": "report.pdf",
    "content_type": "application/pdf",
    "size_bytes": 204800,
    "index_status": "indexed",
    "created_at": "2026-04-20T10:00:00Z",
    "minio_path": "users/abc123/7f3c9a1b-2e4d-4f8a-b3c5-1d2e3f4a5b6c/report.pdf"
  }
  ```

  | 필드명 | 타입 | 설명 |
  |--------|------|------|
  | `file_id` | string (UUID) | 파일 고유 ID |
  | `filename` | string | 원본 파일명 |
  | `content_type` | string | MIME 타입 |
  | `size_bytes` | integer | 파일 크기 (바이트) |
  | `index_status` | string | 벡터 인덱싱 상태 |
  | `created_at` | string (ISO 8601) | 업로드 일시 |
  | `minio_path` | string | MinIO 내부 저장 경로 |

- 실패 케이스

  | 상태 코드 | 원인 |
  |-----------|------|
  | `401 Unauthorized` | 인증 토큰 없음 또는 유효하지 않음 |
  | `404 Not Found` | 파일이 존재하지 않거나 본인 소유가 아님 |

**예시**

```bash
curl http://localhost:8000/api/v1/files/7f3c9a1b-2e4d-4f8a-b3c5-1d2e3f4a5b6c \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### DELETE /api/v1/files/{file_id} — 파일 삭제

**설명**: 파일을 MinIO 스토리지와 DB에서 삭제합니다. 다른 사용자의 파일은 삭제할 수 없습니다.  
**인증 필요**: 필요

**요청**

- Headers

  | 헤더 | 값 |
  |------|-----|
  | `Authorization` | `Bearer <access_token>` |

- Path Parameters

  | 파라미터 | 타입 | 필수 | 설명 |
  |----------|------|------|------|
  | `file_id` | string (UUID) | Y | 삭제할 파일의 ID |

**응답**

- 성공 `204 No Content` — 응답 바디 없음

- 실패 케이스

  | 상태 코드 | 원인 |
  |-----------|------|
  | `401 Unauthorized` | 인증 토큰 없음 또는 유효하지 않음 |
  | `404 Not Found` | 파일이 존재하지 않거나 본인 소유가 아님 |

**예시**

```bash
curl -X DELETE http://localhost:8000/api/v1/files/7f3c9a1b-2e4d-4f8a-b3c5-1d2e3f4a5b6c \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### GET /api/v1/files/{file_id}/download — 다운로드 URL

**설명**: 파일을 다운로드할 수 있는 서명된 임시 URL을 반환합니다. URL의 유효 시간은 **1시간(3600초)**입니다.  
**인증 필요**: 필요

**요청**

- Headers

  | 헤더 | 값 |
  |------|-----|
  | `Authorization` | `Bearer <access_token>` |

- Path Parameters

  | 파라미터 | 타입 | 필수 | 설명 |
  |----------|------|------|------|
  | `file_id` | string (UUID) | Y | 다운로드할 파일의 ID |

**응답**

- 성공 `200 OK`

  ```json
  {
    "download_url": "http://minio:9000/personal-docs/users/abc123/.../report.pdf?X-Amz-Signature=...",
    "expires_in": 3600
  }
  ```

  | 필드명 | 타입 | 설명 |
  |--------|------|------|
  | `download_url` | string | MinIO Presigned URL |
  | `expires_in` | integer | URL 유효 시간 (초 단위, 항상 `3600`) |

- 실패 케이스

  | 상태 코드 | 원인 |
  |-----------|------|
  | `401 Unauthorized` | 인증 토큰 없음 또는 유효하지 않음 |
  | `404 Not Found` | 파일이 존재하지 않거나 본인 소유가 아님 |

**예시**

```bash
curl http://localhost:8000/api/v1/files/7f3c9a1b-2e4d-4f8a-b3c5-1d2e3f4a5b6c/download \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

## 3. 챗 (Chat)

### POST /api/v1/chats — 세션 생성

**설명**: 새 채팅 세션을 생성합니다. 메시지 전송 전에 반드시 세션을 먼저 생성해야 합니다.  
**인증 필요**: 필요

**요청**

- Headers

  | 헤더 | 값 |
  |------|-----|
  | `Authorization` | `Bearer <access_token>` |

- Body: 없음

**응답**

- 성공 `201 Created`

  ```json
  {
    "id": "d4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f90",
    "title": null,
    "created_at": "2026-04-20T10:00:00Z",
    "updated_at": "2026-04-20T10:00:00Z"
  }
  ```

  | 필드명 | 타입 | 설명 |
  |--------|------|------|
  | `id` | string (UUID) | 세션 고유 ID |
  | `title` | string \| null | 세션 제목 (초기값: `null`) |
  | `created_at` | string (ISO 8601) | 세션 생성 일시 |
  | `updated_at` | string (ISO 8601) | 세션 마지막 수정 일시 |

- 실패 케이스

  | 상태 코드 | 원인 |
  |-----------|------|
  | `401 Unauthorized` | 인증 토큰 없음 또는 유효하지 않음 |

**예시**

```bash
curl -X POST http://localhost:8000/api/v1/chats \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### GET /api/v1/chats — 세션 목록

**설명**: 현재 인증된 사용자의 채팅 세션 목록을 반환합니다.  
**인증 필요**: 필요

**요청**

- Headers

  | 헤더 | 값 |
  |------|-----|
  | `Authorization` | `Bearer <access_token>` |

**응답**

- 성공 `200 OK`

  ```json
  [
    {
      "id": "d4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f90",
      "title": "PDF 요약 질문",
      "created_at": "2026-04-20T10:00:00Z",
      "updated_at": "2026-04-20T10:30:00Z"
    },
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "title": null,
      "created_at": "2026-04-20T11:00:00Z",
      "updated_at": "2026-04-20T11:00:00Z"
    }
  ]
  ```

- 실패 케이스

  | 상태 코드 | 원인 |
  |-----------|------|
  | `401 Unauthorized` | 인증 토큰 없음 또는 유효하지 않음 |

**예시**

```bash
curl http://localhost:8000/api/v1/chats \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### GET /api/v1/chats/{session_id} — 세션 단건 조회

**설명**: 특정 채팅 세션과 해당 세션의 전체 메시지 목록을 반환합니다.  
**인증 필요**: 필요

**요청**

- Headers

  | 헤더 | 값 |
  |------|-----|
  | `Authorization` | `Bearer <access_token>` |

- Path Parameters

  | 파라미터 | 타입 | 필수 | 설명 |
  |----------|------|------|------|
  | `session_id` | string (UUID) | Y | 조회할 세션 ID |

**응답**

- 성공 `200 OK`

  ```json
  {
    "id": "d4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f90",
    "title": "PDF 요약 질문",
    "created_at": "2026-04-20T10:00:00Z",
    "updated_at": "2026-04-20T10:30:00Z",
    "messages": [
      {
        "id": "11111111-2222-3333-4444-555555555555",
        "session_id": "d4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f90",
        "role": "user",
        "content": "이 PDF의 핵심 내용을 요약해줘",
        "sources": null,
        "created_at": "2026-04-20T10:10:00Z"
      },
      {
        "id": "66666666-7777-8888-9999-000000000000",
        "session_id": "d4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f90",
        "role": "assistant",
        "content": "해당 PDF의 핵심 내용은 다음과 같습니다...",
        "sources": [
          {
            "file_id": "7f3c9a1b-2e4d-4f8a-b3c5-1d2e3f4a5b6c",
            "filename": "report.pdf",
            "page": 3
          }
        ],
        "created_at": "2026-04-20T10:10:05Z"
      }
    ]
  }
  ```

  메시지 필드:

  | 필드명 | 타입 | 설명 |
  |--------|------|------|
  | `id` | string (UUID) | 메시지 고유 ID |
  | `session_id` | string (UUID) | 속한 세션 ID |
  | `role` | string | 발신자 역할 (`"user"` 또는 `"assistant"`) |
  | `content` | string | 메시지 내용 |
  | `sources` | array \| null | 답변 생성에 참조된 문서 출처 목록 (사용자 메시지는 `null`) |
  | `created_at` | string (ISO 8601) | 메시지 생성 일시 |

- 실패 케이스

  | 상태 코드 | 원인 |
  |-----------|------|
  | `401 Unauthorized` | 인증 토큰 없음 또는 유효하지 않음 |
  | `404 Not Found` | 세션이 존재하지 않거나 본인 소유가 아님 |

**예시**

```bash
curl http://localhost:8000/api/v1/chats/d4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f90 \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### DELETE /api/v1/chats/{session_id} — 세션 삭제

**설명**: 채팅 세션과 해당 세션의 모든 메시지를 삭제합니다.  
**인증 필요**: 필요

**요청**

- Headers

  | 헤더 | 값 |
  |------|-----|
  | `Authorization` | `Bearer <access_token>` |

- Path Parameters

  | 파라미터 | 타입 | 필수 | 설명 |
  |----------|------|------|------|
  | `session_id` | string (UUID) | Y | 삭제할 세션 ID |

**응답**

- 성공 `204 No Content` — 응답 바디 없음

- 실패 케이스

  | 상태 코드 | 원인 |
  |-----------|------|
  | `401 Unauthorized` | 인증 토큰 없음 또는 유효하지 않음 |
  | `404 Not Found` | 세션이 존재하지 않거나 본인 소유가 아님 |

**예시**

```bash
curl -X DELETE http://localhost:8000/api/v1/chats/d4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f90 \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### POST /api/v1/chats/{session_id}/messages — 메시지 전송 (SSE)

**설명**: 메시지를 전송하고 RAG 기반 AI 답변을 Server-Sent Events(SSE) 스트림으로 수신합니다. 응답은 텍스트 청크 단위로 순차 전달됩니다.  
**인증 필요**: 필요

**요청**

- Headers

  | 헤더 | 값 |
  |------|-----|
  | `Authorization` | `Bearer <access_token>` |
  | `Content-Type` | `application/json` |
  | `Accept` | `text/event-stream` |

- Path Parameters

  | 파라미터 | 타입 | 필수 | 설명 |
  |----------|------|------|------|
  | `session_id` | string (UUID) | Y | 메시지를 전송할 세션 ID |

- Body

  | 필드명 | 타입 | 필수 | 설명 |
  |--------|------|------|------|
  | `content` | string | Y | 사용자 메시지 내용 |

**응답**

- 성공 `200 OK` — `text/event-stream`

  응답 헤더:
  ```
  Content-Type: text/event-stream
  Cache-Control: no-cache
  X-Accel-Buffering: no
  ```

  SSE 이벤트 스트림 예시:
  ```
  data: {"type": "token", "content": "해당"}

  data: {"type": "token", "content": " PDF의"}

  data: {"type": "token", "content": " 핵심"}

  data: {"type": "sources", "content": [{"file_id": "7f3c9a1b-...", "filename": "report.pdf", "page": 3}]}

  data: {"type": "done", "content": ""}
  ```

  자세한 SSE 이벤트 형식은 [SSE 이벤트 형식](#sse-이벤트-형식) 참조

- 실패 케이스

  | 상태 코드 | 원인 |
  |-----------|------|
  | `401 Unauthorized` | 인증 토큰 없음 또는 유효하지 않음 |
  | `404 Not Found` | 세션이 존재하지 않거나 본인 소유가 아님 |
  | `422 Unprocessable Entity` | `content` 필드 누락 |
  | `500 Internal Server Error` | RAG 처리 중 오류 |

**예시**

```bash
curl -X POST http://localhost:8000/api/v1/chats/d4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f90/messages \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  --no-buffer \
  -d '{"content": "이 PDF의 핵심 내용을 요약해줘"}'
```

```javascript
const response = await fetch(
  `http://localhost:8000/api/v1/chats/${sessionId}/messages`,
  {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ content: '이 PDF의 핵심 내용을 요약해줘' }),
  }
);

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');

  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const event = JSON.parse(line.slice(6));
      if (event.type === 'token') {
        // 텍스트 청크를 UI에 이어 붙임
        appendToChat(event.content);
      } else if (event.type === 'sources') {
        // 출처 정보 표시
        showSources(event.content);
      } else if (event.type === 'done') {
        // 스트림 종료
        break;
      }
    }
  }
}
```

---

## 부록

### index_status 상태 정의

파일 업로드 후 RAG 검색을 위한 벡터 인덱싱 상태를 나타냅니다.

| 값 | 설명 | UI 처리 권장 사항 |
|----|------|-------------------|
| `pending` | 인덱싱 대기 중 (업로드 직후 초기 상태) | 로딩 스피너 또는 "처리 중" 표시 |
| `indexing` | 벡터 임베딩 생성 중 | 진행 중 표시 |
| `indexed` | 인덱싱 완료 — RAG 검색에 사용 가능 | "사용 가능" 표시 |
| `failed` | 인덱싱 실패 | 에러 표시, 재시도 안내 |
| `unsupported` | 지원하지 않는 파일 형식으로 인덱싱 불가 | "RAG 미지원" 표시 |

> **참고**: 파일 업로드 직후 `index_status`는 `"pending"`입니다. 인덱싱은 백그라운드에서 비동기로 처리되므로, 상태 확인이 필요한 경우 `GET /api/v1/files/{file_id}`를 주기적으로 폴링하세요.

---

### SSE 이벤트 형식

메시지 전송(`POST /api/v1/chats/{session_id}/messages`) API는 Server-Sent Events 방식으로 응답을 스트리밍합니다.

#### 기본 형식

각 이벤트는 다음과 같은 형식으로 전달됩니다:

```
data: <JSON 문자열>\n\n
```

JSON 페이로드 구조:

```json
{
  "type": "<이벤트 타입>",
  "content": "<이벤트 내용>"
}
```

#### 이벤트 타입

| `type` | `content` 타입 | 설명 |
|--------|----------------|------|
| `token` | string | AI 응답 텍스트 청크. 순서대로 이어 붙이면 전체 응답이 됩니다. |
| `sources` | array | 답변 생성에 참조된 문서 출처 목록 |
| `done` | string (빈 문자열) | 스트림 종료 신호. 수신 후 연결을 닫아야 합니다. |
| `error` | string | 스트리밍 중 오류 발생 시 에러 메시지 |

#### sources 이벤트 내용 구조

```json
[
  {
    "file_id": "7f3c9a1b-2e4d-4f8a-b3c5-1d2e3f4a5b6c",
    "filename": "report.pdf",
    "page": 3
  }
]
```

> sources 내 각 필드는 RAG 검색 결과에 따라 달라질 수 있으며, 출처가 없는 경우 빈 배열(`[]`)이 전달됩니다.

#### 전체 스트림 예시

```
data: {"type": "token", "content": "해당 보고서의"}

data: {"type": "token", "content": " 핵심 내용은"}

data: {"type": "token", "content": " 다음과 같습니다."}

data: {"type": "sources", "content": [{"file_id": "7f3c9a1b-...", "filename": "report.pdf", "page": 3}]}

data: {"type": "done", "content": ""}
```

#### EventSource vs fetch 선택 가이드

| 방식 | 장점 | 단점 | 권장 상황 |
|------|------|------|-----------|
| `EventSource` | 브라우저 내장, 자동 재연결 | POST 요청 불가, 헤더 추가 불가 | 사용 불가 (인증 헤더 필요) |
| `fetch + ReadableStream` | POST 가능, 헤더 설정 가능 | 직접 파싱 필요 | **이 API에서 권장** |

---

### 파일 지원 포맷

RAG 인덱싱 및 업로드가 지원되는 파일 형식입니다.

| 확장자 | MIME 타입 | 설명 |
|--------|-----------|------|
| `.pdf` | `application/pdf` | PDF 문서 |
| `.txt` | `text/plain` | 일반 텍스트 |
| `.md` | `text/markdown` | 마크다운 문서 |
| `.docx` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | Word 문서 |

> **파일 크기 제한**: 최대 **50MB** (52,428,800 bytes)  
> 지원하지 않는 형식으로 업로드하면 `415 Unsupported Media Type` 오류가 반환됩니다.
