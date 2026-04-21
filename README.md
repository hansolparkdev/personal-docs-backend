# Personal Docs Backend

유저별 파일 관리 및 RAG 기반 문서 검색 챗 API.

## 기술 스택

- **Framework**: FastAPI (Python 3.11+)
- **DB**: PostgreSQL + pgvector (벡터 검색)
- **File Storage**: MinIO (S3 호환)
- **Auth**: Keycloak (OAuth2 + JWT)
- **AI/RAG**: LangChain, LangGraph, OpenAI
- **파일 파싱**: MarkItDown (PDF, DOCX, PPTX, XLSX, MD, TXT)

## 주요 기능

- 유저 인증 (Keycloak JWT — id/password 및 SSO)
- 유저별 파일 업로드 / 조회 / 삭제 (MinIO 저장 + pgvector 임베딩 색인)
- 등록된 파일 기반 RAG 챗 (SSE 스트리밍 응답)

## 실행 방법

### 사전 요구사항

- Python 3.11+
- Docker Desktop

### 1. 환경변수 설정

```bash
cp .env.example .env
```

`.env` 파일에서 아래 값 입력:

```
OPENAI_API_KEY=sk-...           # OpenAI API 키
KEYCLOAK_CLIENT_SECRET=...      # Keycloak client secret
```

### 2. 인프라 기동

```bash
docker compose up -d
```

| 서비스 | 주소 | 기본 계정 |
|--------|------|-----------|
| PostgreSQL | localhost:5432 | postgres / postgres |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin |
| Keycloak | http://localhost:8080 | admin / admin |

### 3. Keycloak 설정 (최초 1회)

1. http://localhost:8080 접속 → admin/admin 로그인
2. Realm 생성: `personal-docs`
3. Client 생성: `backend` (Client authentication ON)
4. Credentials 탭 → Client secret 복사 → `.env`의 `KEYCLOAK_CLIENT_SECRET`에 입력
5. Authentication → Required Actions → `Verify Profile` 비활성화

### 4. Python 환경 및 패키지 설치

```bash
python3.11 -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 5. DB 마이그레이션

```bash
alembic upgrade head
```

### 6. 개발 서버 실행

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API 문서 (Swagger): http://localhost:8000/docs

Swagger에서 `Authorize` 버튼 클릭 후 Bearer 토큰 입력하면 모든 API 테스트 가능.

## 토큰 발급 (테스트용)

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "유저명", "password": "비밀번호"}'
```

## 테스트

```bash
# 전체 테스트
pytest

# 커버리지 포함
pytest --cov=app --cov-report=term-missing
```

## 프로젝트 구조

```
app/
├── main.py                # FastAPI 앱 진입점 + Swagger BearerAuth 설정
├── core/
│   ├── config.py          # 환경변수 설정
│   ├── security.py        # JWT 검증 (JWKS 캐싱)
│   └── dependencies.py    # get_current_user 의존성
├── api/v1/
│   ├── auth.py            # 회원가입, 로그인, SSO 콜백, 토큰 갱신, /me
│   ├── files.py           # 파일 업로드/조회/삭제/다운로드
│   └── chat.py            # 세션 CRUD + SSE 스트리밍 챗
├── db/
│   ├── base.py            # AsyncSession, Base
│   └── models/            # User, File, FileChunk, ChatSession, ChatMessage
├── services/
│   ├── keycloak_service.py  # Keycloak Admin API 연동
│   ├── user_service.py      # 유저 DB CRUD
│   ├── file_service.py      # MinIO + 임베딩 색인
│   ├── rag_service.py       # RAG 파이프라인 + SSE 스트리밍
│   └── chat_service.py      # 세션/메시지 CRUD
├── schemas/               # Pydantic 요청/응답 스키마
└── utils/
    └── file_parser.py     # MarkItDown 래퍼
tests/
alembic/                   # DB 마이그레이션
docker-compose.yml
```

## 상세 문서

| 문서 | 내용 |
|------|------|
| [전체 구조](docs/guide/overview.md) | 아키텍처, 기술 스택, 폴더 구조 |
| [인프라 설정](docs/guide/infrastructure.md) | Docker, 환경변수, Alembic |
| [인증 흐름](docs/guide/auth.md) | Keycloak JWT, curl 예시 |
| [파일 관리](docs/guide/file-management.md) | 업로드→색인 흐름, API 예시 |
| [RAG 파이프라인](docs/guide/rag.md) | RAG 동작 방식, LangGraph, SSE |
| [챗 API](docs/guide/chat.md) | 세션/메시지 API, SSE 클라이언트 예시 |
| [Python 코드 사용법](docs/guide/python-usage.md) | 서비스 함수 코드 예시 |
