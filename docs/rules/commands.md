# 전체 명령

## 개발·품질

| 명령 | 의미 |
|------|------|
| `pip install -r requirements.txt` | 의존 설치 |
| `uvicorn app.main:app --reload` | 개발 서버 (포트 8000) |
| `pytest` | 단위 테스트 전체 |
| `pytest --cov=app --cov-report=term-missing` | 커버리지 포함 테스트 |
| `pytest tests/test_<name>.py -v` | 특정 테스트 파일 |
| `pip-audit` | 보안 취약점 스캔 |
| `ruff check .` | 린트 |
| `ruff format .` | 포맷 |

## 인프라 (Docker)

| 명령 | 의미 |
|------|------|
| `docker compose up -d` | 전체 인프라 기동 |
| `docker compose down` | 컨테이너 중지 |
| `docker compose down -v` | 볼륨 초기화 |
| `docker compose logs -f` | 로그 스트리밍 |

## DB 마이그레이션 (Alembic)

| 명령 | 의미 |
|------|------|
| `alembic upgrade head` | 최신 마이그레이션 적용 |
| `alembic revision --autogenerate -m "설명"` | 마이그레이션 파일 생성 |
| `alembic downgrade -1` | 한 단계 롤백 |
| `alembic history` | 마이그레이션 이력 |

## 서비스 접속 정보

- API: `http://localhost:8000`
- API 문서: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5432`
- MinIO Console: `http://localhost:9001`
- Keycloak: `http://localhost:8080`
