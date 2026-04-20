# Personal Docs Backend

유저별 파일 관리 및 RAG 기반 문서 검색 챗 API.

## 기술 스택

- **Framework**: FastAPI (Python)
- **DB**: PostgreSQL + pgvector (벡터 검색)
- **File Storage**: MinIO (S3 호환)
- **Auth**: Keycloak (OAuth2 + JWT)
- **AI/RAG**: LangChain, LangGraph

## 주요 기능

- 유저 인증 (Keycloak JWT)
- 유저별 파일 업로드 / 조회 / 삭제 (MinIO)
- 등록된 파일 기반 RAG 챗 (LangChain + LangGraph + pgvector)

## 시작하기

### 1. 환경변수 설정

```bash
cp .env.example .env
# .env 파일에서 OPENAI_API_KEY 등 실제 값 입력
```

### 2. 인프라 기동

```bash
docker compose up -d
```

| 서비스 | 주소 |
|--------|------|
| PostgreSQL | localhost:5432 |
| MinIO Console | http://localhost:9001 |
| Keycloak | http://localhost:8080 |

### 3. 패키지 설치

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. DB 마이그레이션

```bash
alembic upgrade head
```

### 5. 개발 서버 실행

```bash
uvicorn app.main:app --reload
```

API 문서: http://localhost:8000/docs

## 테스트

```bash
pytest
pytest --cov=app --cov-report=term-missing
```

## 프로젝트 구조

```
app/
├── main.py
├── core/          # 설정, JWT 검증
├── api/v1/        # 라우터 (auth, files, chat)
├── db/            # SQLAlchemy 모델, 세션
├── services/      # 비즈니스 로직 (file, rag, user)
└── schemas/       # Pydantic 스키마
tests/
alembic/           # DB 마이그레이션
docker-compose.yml
```
