# 폴더 규칙

## 프로젝트 구조

```
backend/
├── app/
│   ├── main.py              # FastAPI 앱 진입점
│   ├── core/
│   │   ├── config.py        # 환경변수 설정 (pydantic-settings)
│   │   ├── security.py      # JWT 검증, Keycloak 연동
│   │   └── dependencies.py  # 공통 Depends (get_db, get_current_user 등)
│   ├── db/
│   │   ├── base.py          # SQLAlchemy Base, engine, session
│   │   └── models/          # ORM 모델 (pgvector 포함)
│   ├── api/
│   │   └── v1/
│   │       ├── router.py    # v1 라우터 집합
│   │       ├── auth.py      # 인증 관련 엔드포인트
│   │       ├── files.py     # 파일 업로드/조회/삭제
│   │       └── chat.py      # RAG 챗 엔드포인트
│   ├── services/
│   │   ├── file_service.py  # 파일 관리 비즈니스 로직 (MinIO 연동)
│   │   ├── rag_service.py   # RAG 파이프라인 (LangChain/LangGraph)
│   │   └── user_service.py  # 유저 관련 로직
│   ├── schemas/             # Pydantic 요청/응답 스키마
│   └── utils/               # 공통 유틸
├── tests/
│   ├── conftest.py          # pytest fixture (TestClient, DB 등)
│   ├── test_auth.py
│   ├── test_files.py
│   └── test_chat.py
├── alembic/                 # DB 마이그레이션
│   ├── env.py
│   └── versions/
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── alembic.ini
```

## 파일명 규칙

| 유형 | 규칙 |
|------|------|
| 모듈 파일 | `snake_case.py` |
| 테스트 파일 | `test_<대상>.py` |
| 라우터 파일 | 도메인명 단수 (`file.py` 아닌 `files.py`) |

## 레이어 규칙

- `api/` — HTTP 진입/응답만. 비즈니스 로직 금지
- `services/` — 비즈니스 로직. DB·MinIO·LangChain 호출
- `db/models/` — ORM 모델 정의만. 로직 금지
- `schemas/` — Pydantic 입출력 스키마. 모델과 1:1 대응하지 않아도 됨

## MinIO 경로 구조

```
{bucket-name}/
└── {user_id}/
    └── {file_id}/
        └── {original_filename}
```
