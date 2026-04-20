# CLAUDE.md

## 프로젝트 타입

backend

## 기술 스택

- 언어·프레임워크: Python / FastAPI
- 패키지 매니저: pip (requirements.txt)
- 단위 테스트: pytest
- DB: PostgreSQL (일반 데이터) + pgvector (벡터 임베딩)
- 파일 스토리지: MinIO (S3 호환)
- AI/RAG: LangChain, LangGraph
- 인증: Keycloak (OAuth2 서버) + JWT 토큰 검증

## 핵심 기능

1. **유저 관리** — Keycloak JWT 기반 인증·인가
2. **파일 관리** — 유저별 파일 업로드/조회/삭제 (MinIO 저장)
3. **RAG 챗** — 유저가 등록한 파일을 LangChain+LangGraph로 검색·응답

## 아키텍처

- 테스트 폴더: `tests/`
- 환경변수: `.env` (`.env.example` 참조)

## 개발 서버

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 단위 테스트 명령

- 전체: `pytest`
- 커버리지: `pytest --cov=app --cov-report=term-missing`
- 특정 파일: `pytest tests/test_<name>.py -v`

## 보안 스캔

```bash
pip-audit
```

## 인프라 (Docker)

```bash
# 전체 기동 (PostgreSQL + pgvector + MinIO + Keycloak)
docker compose up -d

# 중지
docker compose down

# 볼륨 초기화
docker compose down -v
```

## 참조 문서

| 주제 | 문서 |
| --- | --- |
| 금지 패턴 | [docs/rules/forbidden-patterns.md](docs/rules/forbidden-patterns.md) |
| 폴더 규약 | [docs/rules/folder-conventions.md](docs/rules/folder-conventions.md) |
| 명령어 | [docs/rules/commands.md](docs/rules/commands.md) |
| 스택 특화 규율 | [docs/rules/stack-specific.md](docs/rules/stack-specific.md) |
| 에이전트 워크플로우 | [docs/rules/dev-workflow.md](docs/rules/dev-workflow.md) |
| SDD 트랙 | [docs/rules/dev-flow.md](docs/rules/dev-flow.md) |
