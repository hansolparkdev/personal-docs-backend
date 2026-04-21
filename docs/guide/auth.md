# 인증 흐름

## Keycloak 역할 설명

Keycloak은 이 시스템의 모든 인증/인가를 담당하는 OAuth2/OIDC 서버입니다.

- **Realm(`personal-docs`)**: 인증 도메인. 유저, 클라이언트, 토큰 설정이 모두 이 Realm 안에서 관리됩니다.
- **Client(`backend`)**: 백엔드 서버를 나타내는 OAuth2 클라이언트. Client Credentials 방식으로 Admin API를 호출하고, Password Grant 방식으로 유저 토큰을 발급합니다.
- **JWT Access Token**: 유저 인증 후 발급되는 토큰. 모든 보호된 API 호출 시 `Authorization: Bearer <token>` 헤더에 포함해야 합니다.
- **JWKS(JSON Web Key Set)**: Keycloak이 제공하는 공개키 목록. 서버가 JWT 서명 검증에 사용하며, 10분(600초) TTL로 인메모리 캐시합니다.

---

## JWT 검증 방식 (security.py 기반)

`app/core/security.py`의 `verify_token()` 함수가 모든 JWT 검증을 처리합니다.

### 검증 절차

1. JWT 헤더에서 `kid`(Key ID)를 추출합니다.
2. Keycloak JWKS 엔드포인트(`/protocol/openid-connect/certs`)에서 공개키 목록을 가져옵니다 (캐시 적용).
3. `kid`에 해당하는 공개키로 JWT 서명을 RS256 알고리즘으로 검증합니다.
4. JWT payload의 `azp`(authorized party) 필드가 `KEYCLOAK_CLIENT_ID`(`backend`)와 일치하는지 확인합니다.
5. 검증 실패 시 캐시를 무효화하고 1회 재시도합니다.

### JWKS 캐시 동작

- 캐시 유효 시간: `KEYCLOAK_JWKS_CACHE_TTL`(기본 600초)
- 캐시 미스 또는 `kid` 불일치 시: 캐시 무효화 후 Keycloak에서 새로 JWKS를 가져옵니다.
- 2회 연속 실패 시 HTTP 401을 반환합니다.

### get_current_user 의존성

`app/core/dependencies.py`의 `get_current_user`는 FastAPI 의존성으로, API 핸들러에 `Depends(get_current_user)`를 선언하면 자동으로 JWT를 검증하고 DB에서 해당 유저를 조회하여 주입합니다.

```python
# 핸들러에서 현재 유저를 받는 예시
from app.core.dependencies import get_current_user
from app.db.models.user import User

@router.get("/protected")
async def protected_endpoint(current_user: User = Depends(get_current_user)):
    return {"user_id": str(current_user.id)}
```

---

## id/password 회원가입 → 로그인 → /me 전체 흐름

```
[클라이언트]                    [FastAPI]                 [Keycloak]            [PostgreSQL]

  1. POST /auth/register
  {username, email, password}
        |
        +----(서비스 계정 토큰 요청)-----------------> Client Credentials grant
        |                                            <-- access_token (admin)
        |
        +----(유저 생성)----------------------------> Admin API POST /users
        |                                            <-- 201 Created
        |
        +----(토큰 발급)----------------------------> Password grant
        |                                            <-- access_token, refresh_token
        |
        +----(DB upsert)-------------------------------------------------> users 테이블에 저장
        |
        <-- 201 UserResponse (user_id, username, email ...)


  2. POST /auth/login
  {username, password}
        |
        +----(토큰 발급)----------------------------> Password grant
        |                                            <-- access_token, refresh_token
        |
        +----(DB last_login_at 갱신)----------------------------> upsert_user()
        |
        <-- 200 TokenResponse (access_token, refresh_token, expires_in)


  3. GET /auth/me
  Authorization: Bearer <access_token>
        |
        +----(JWT 검증)---------verify_token()---------JWKS 공개키로 서명 검증
        |
        +----(유저 조회)-------------------------------------------------> users.auth_id = JWT.sub
        |
        <-- 200 UserResponse
```

---

## SSO 콜백 흐름

프런트엔드에서 Keycloak Authorization Code Flow를 사용하는 경우의 흐름입니다.

```
[브라우저]                  [프런트엔드]            [FastAPI]               [Keycloak]

  1. 유저가 "소셜 로그인" 클릭
        |
        +---> Keycloak 로그인 페이지로 리다이렉트
              (response_type=code, client_id=backend, redirect_uri=...)
        |
        <--- 유저 로그인 완료 → 프런트엔드로 code 파라미터와 함께 리다이렉트

  2. GET /auth/callback?code=...&redirect_uri=...
        |
        +----(Authorization Code 교환)-----------> POST /token (grant_type=authorization_code)
        |                                          <-- access_token, refresh_token
        |
        +----(DB upsert)---------------------------------> users 테이블
        |
        <-- 200 TokenResponse
```

---

## API별 curl 예시

### 회원가입

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123",
    "name": "테스트 유저"
  }'
```

응답 예시 (201 Created):
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "testuser",
  "email": "test@example.com",
  "name": "테스트 유저",
  "created_at": "2026-04-20T10:00:00Z",
  "last_login_at": "2026-04-20T10:00:00Z"
}
```

### 로그인

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "password123"
  }'
```

응답 예시 (200 OK):
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 300
}
```

### 토큰 갱신

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

응답 예시 (200 OK):
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 300
}
```

### 현재 유저 정보 조회

```bash
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
```

응답 예시 (200 OK):
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "testuser",
  "email": "test@example.com",
  "name": "테스트 유저",
  "created_at": "2026-04-20T10:00:00Z",
  "last_login_at": "2026-04-20T10:05:00Z"
}
```

### SSO 콜백

```bash
curl "http://localhost:8000/api/v1/auth/callback?code=AUTH_CODE_HERE&redirect_uri=http://localhost:3000/callback"
```

---

## 오류 응답

| HTTP 상태 | 발생 조건 |
|---|---|
| 401 Unauthorized | 토큰 누락, 서명 불일치, 만료, 잘못된 클라이언트 |
| 404 Not Found | JWT는 유효하나 DB에 해당 유저가 없음 |
| 409 Conflict | 회원가입 시 이미 존재하는 username 또는 email |
| 502 Bad Gateway | Keycloak 서버가 응답하지 않음 |
