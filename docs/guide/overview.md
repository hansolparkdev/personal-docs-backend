# 시스템 전체 구조

## 시스템 개요

Personal Docs Backend는 사용자가 개인 문서(PDF, Word, PowerPoint, Excel, Markdown, 텍스트)를 업로드하고, 업로드된 문서를 기반으로 AI와 대화할 수 있는 RAG(Retrieval-Augmented Generation) 챗봇 백엔드입니다. Keycloak을 통한 인증, MinIO를 통한 파일 저장, pgvector를 통한 벡터 임베딩 검색, LangChain+OpenAI를 통한 LLM 응답 생성을 제공하며, FastAPI 기반 REST API로 모든 기능을 노출합니다.

---

## 기술 스택

| 역할 | 기술 | 버전 |
|---|---|---|
| 웹 프레임워크 | FastAPI | 0.115.5 |
| WSGI/ASGI 서버 | Uvicorn | 0.32.1 |
| 언어 | Python | 3.11+ |
| 데이터베이스 ORM | SQLAlchemy (asyncio) | 2.0.36 |
| DB 드라이버 | asyncpg | 0.30.0 |
| DB 마이그레이션 | Alembic | 1.14.0 |
| 벡터 DB 확장 | pgvector | 0.2.x |
| 파일 스토리지 | MinIO (S3 호환) | 7.2.11 |
| 인증 서버 | Keycloak | 26.0 |
| JWT 검증 | python-jose | 3.3.0 |
| HTTP 클라이언트 | httpx | 0.27.2 |
| LLM 연동 | LangChain, LangChain-OpenAI | 0.3.9 / 0.2.11 |
| 그래프 오케스트레이션 | LangGraph | 0.2.56 |
| LLM 모델 | OpenAI GPT-4o-mini | - |
| 임베딩 모델 | OpenAI text-embedding-3-small | - |
| 파일 파싱 | MarkItDown | 0.1.1 |
| 설정 관리 | pydantic-settings | 2.6.1 |
| 테스트 | pytest + pytest-asyncio | 8.3.4 |
| 린터/포매터 | ruff | 0.8.3 |

---

## 전체 아키텍처 다이어그램

```
클라이언트 (웹/앱/curl)
        |
        | HTTP/SSE
        v
+------------------------+
|     FastAPI 서버        |
|   (app/main.py)        |
|                        |
|  /api/v1/auth          |
|  /api/v1/files         |
|  /api/v1/chats         |
+------------------------+
        |
   +----+----+----------+
   |         |          |
   v         v          v
+-------+ +------+ +----------+
|Keycloak| |MinIO | |PostgreSQL|
|(인증)  | |(파일)| |+pgvector |
+-------+ +------+ | (DB+벡터)|
                    +----------+

파일 업로드 후 백그라운드 처리 흐름:
MinIO 저장 → MarkItDown 파싱 → 청크 분할
           → OpenAI Embeddings → pgvector 저장

챗 응답 흐름:
질문 → OpenAI Embeddings → pgvector 유사도 검색(K=5)
     → 컨텍스트 구성 → OpenAI LLM → SSE 스트리밍 응답
```

---

## 폴더 구조 설명

```
backend/
├── app/
│   ├── main.py                  # FastAPI 앱 진입점, OpenAPI 설정
│   ├── api/
│   │   └── v1/
│   │       ├── router.py        # /api/v1 라우터 통합
│   │       ├── auth.py          # 인증 관련 엔드포인트
│   │       ├── files.py         # 파일 관리 엔드포인트
│   │       └── chat.py          # 챗 엔드포인트
│   ├── core/
│   │   ├── config.py            # 환경변수 설정 (pydantic-settings)
│   │   ├── security.py          # JWT 검증 로직 (JWKS 기반)
│   │   └── dependencies.py      # FastAPI 의존성 (get_current_user 등)
│   ├── db/
│   │   ├── base.py              # DB 엔진, 세션, Base 클래스
│   │   └── models/
│   │       ├── user.py          # users 테이블
│   │       ├── file.py          # files 테이블 (IndexStatus 포함)
│   │       ├── file_chunk.py    # file_chunks 테이블 (pgvector)
│   │       └── chat.py          # chat_sessions, chat_messages 테이블
│   ├── schemas/
│   │   ├── auth.py              # 인증 요청/응답 Pydantic 스키마
│   │   ├── file.py              # 파일 요청/응답 Pydantic 스키마
│   │   └── chat.py              # 챗 요청/응답 Pydantic 스키마
│   ├── services/
│   │   ├── keycloak_service.py  # Keycloak API 호출 (JWKS, 토큰 발급 등)
│   │   ├── user_service.py      # 유저 DB CRUD
│   │   ├── file_service.py      # 파일 업로드/삭제/인덱싱
│   │   ├── rag_service.py       # RAG 파이프라인 + SSE 스트리밍
│   │   └── chat_service.py      # 챗 세션/메시지 DB CRUD
│   └── utils/
│       └── file_parser.py       # MarkItDown 래퍼 (파일→마크다운 변환)
├── alembic/
│   ├── env.py                   # Alembic 비동기 마이그레이션 환경 설정
│   └── versions/                # 마이그레이션 파일 디렉터리
├── tests/                       # pytest 테스트 코드
├── docker-compose.yml           # PostgreSQL+pgvector, MinIO, Keycloak 정의
├── requirements.txt             # Python 의존성
├── .env.example                 # 환경변수 샘플
└── CLAUDE.md                    # 프로젝트 규칙 문서
```

---

## 주요 데이터 흐름 요약

1. **인증**: 클라이언트가 Keycloak에서 발급받은 JWT(Bearer Token)를 Authorization 헤더에 포함하여 API를 호출합니다.
2. **파일 관리**: 파일 업로드 시 MinIO에 저장 후, 백그라운드에서 MarkItDown으로 파싱 → 청크 분할 → OpenAI 임베딩 → pgvector 저장이 이루어집니다.
3. **RAG 챗**: 사용자 질문을 임베딩하여 pgvector에서 유사 청크(K=5)를 검색하고, 대화 히스토리와 컨텍스트를 합쳐 LLM에 전달한 뒤 SSE(Server-Sent Events) 스트리밍으로 응답합니다.
