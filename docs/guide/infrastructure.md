# 인프라 설정

## Docker Compose 서비스 구성

`docker-compose.yml`은 개발 환경에 필요한 세 가지 서비스를 정의합니다.

### 전체 기동 / 종료

```bash
# 서비스 전체 기동 (백그라운드)
docker compose up -d

# 서비스 중지 (볼륨 유지)
docker compose down

# 서비스 중지 + 볼륨 초기화 (데이터 완전 삭제)
docker compose down -v
```

---

## 서비스별 설명

### 1. PostgreSQL + pgvector

일반 관계형 데이터(유저, 파일 메타데이터, 챗 세션/메시지)와 벡터 임베딩(file_chunks.embedding)을 모두 저장합니다. `pgvector/pgvector:pg17` 이미지는 PostgreSQL 17에 pgvector 확장이 포함된 이미지입니다.

| 항목 | 값 |
|---|---|
| 이미지 | pgvector/pgvector:pg17 |
| 호스트 포트 | 5432 |
| DB 이름 | personal_docs |
| 사용자 | postgres |
| 비밀번호 | postgres |
| 데이터 볼륨 | postgres_data |
| 헬스체크 | pg_isready -U postgres |

```bash
# psql로 직접 접속 (Docker 내부)
docker compose exec postgres psql -U postgres -d personal_docs

# 로컬 psql 클라이언트로 접속
psql postgresql://postgres:postgres@localhost:5432/personal_docs
```

### 2. MinIO

파일 원본 바이너리를 저장하는 S3 호환 오브젝트 스토리지입니다. 파일은 `{user_id}/{file_id}/{filename}` 경로로 저장됩니다.

| 항목 | 값 |
|---|---|
| 이미지 | minio/minio:latest |
| API 포트 | 9000 |
| 웹 콘솔 포트 | 9001 |
| 루트 사용자 | minioadmin |
| 루트 비밀번호 | minioadmin |
| 기본 버킷 | personal-docs (앱 시작 시 자동 생성) |
| 데이터 볼륨 | minio_data |

```bash
# 웹 콘솔 접속
# 브라우저에서 http://localhost:9001 열기
# ID: minioadmin / PW: minioadmin
```

### 3. Keycloak

인증 및 인가를 담당하는 OAuth2/OIDC 서버입니다. `start-dev` 모드로 기동되며, 개발 환경 전용입니다(운영 환경에서는 `start` 명령 및 추가 설정 필요).

| 항목 | 값 |
|---|---|
| 이미지 | quay.io/keycloak/keycloak:26.0 |
| 호스트 포트 | 8080 |
| 관리자 ID | admin |
| 관리자 비밀번호 | admin |
| 데이터 볼륨 | keycloak_data |

```bash
# 관리자 콘솔 접속
# 브라우저에서 http://localhost:8080 열기
# ID: admin / PW: admin
```

#### Keycloak 초기 설정 절차

Keycloak을 처음 기동한 후 다음 설정을 수행해야 합니다.

1. 관리자 콘솔(http://localhost:8080)에 접속합니다.
2. 좌측 상단 드롭다운에서 "Create realm"을 클릭합니다.
3. Realm 이름을 `personal-docs`로 입력하고 저장합니다.
4. Clients 메뉴로 이동하여 "Create client"를 클릭합니다.
5. Client ID를 `backend`로 입력하고, Client authentication을 활성화합니다.
6. Service accounts roles 탭에서 `manage-users` 권한을 부여합니다.
7. Credentials 탭에서 Client secret을 복사하여 `.env`의 `KEYCLOAK_CLIENT_SECRET`에 설정합니다.

---

## 환경변수 설명

`.env.example`을 복사하여 `.env`를 생성합니다.

```bash
cp .env.example .env
```

| 환경변수 | 기본값 | 설명 |
|---|---|---|
| `APP_ENV` | development | 실행 환경 (development / production) |
| `SECRET_KEY` | change-me | 앱 내부 서명용 시크릿 키 (운영 시 반드시 변경) |
| `DATABASE_URL` | postgresql+asyncpg://postgres:postgres@localhost:5432/personal_docs | SQLAlchemy 비동기 DB 연결 URL |
| `MINIO_ENDPOINT` | localhost:9000 | MinIO API 엔드포인트 (호스트:포트) |
| `MINIO_ACCESS_KEY` | minioadmin | MinIO 접근 키 |
| `MINIO_SECRET_KEY` | minioadmin | MinIO 시크릿 키 |
| `MINIO_BUCKET` | personal-docs | 파일을 저장할 버킷 이름 |
| `MINIO_SECURE` | false | HTTPS 사용 여부 (운영 시 true) |
| `KEYCLOAK_URL` | http://localhost:8080 | Keycloak 서버 URL |
| `KEYCLOAK_REALM` | personal-docs | Keycloak Realm 이름 |
| `KEYCLOAK_CLIENT_ID` | backend | Keycloak Client ID |
| `KEYCLOAK_CLIENT_SECRET` | (빈값) | Keycloak Client Secret (필수 입력) |
| `KEYCLOAK_JWKS_CACHE_TTL` | 600 | JWKS 공개키 캐시 유효 시간(초) |
| `KEYCLOAK_ADMIN_CLIENT_ID` | backend | Keycloak Admin API 사용 Client ID |
| `OPENAI_API_KEY` | (빈값) | OpenAI API 키 (필수 입력) |
| `OPENAI_MODEL` | gpt-4o-mini | 챗 응답에 사용할 OpenAI 모델 |
| `EMBEDDING_MODEL` | text-embedding-3-small | 임베딩에 사용할 OpenAI 모델 |

---

## Alembic 마이그레이션 사용법

이 프로젝트는 Alembic으로 DB 스키마를 관리합니다. `alembic/env.py`가 비동기 엔진을 사용하도록 설정되어 있으므로 asyncpg 드라이버가 필요합니다.

### 기본 명령어

```bash
# 현재 마이그레이션 상태 확인
alembic current

# 마이그레이션 히스토리 확인
alembic history

# 최신 버전으로 마이그레이션 적용
alembic upgrade head

# 특정 버전으로 올리기
alembic upgrade <revision>

# 한 단계 롤백
alembic downgrade -1

# 특정 버전으로 롤백
alembic downgrade <revision>
```

### 새 마이그레이션 파일 생성

모델 파일(app/db/models/)을 수정한 후 자동으로 마이그레이션 파일을 생성합니다.

```bash
# 자동 생성 (모델 변경사항 감지)
alembic revision --autogenerate -m "설명 메시지"

# 빈 마이그레이션 파일 생성 (수동 작성)
alembic revision -m "설명 메시지"
```

### 최초 DB 초기화 순서

```bash
# 1. Docker Compose로 PostgreSQL 기동
docker compose up -d postgres

# 2. DB가 준비될 때까지 대기 (헬스체크 통과 후)

# 3. 마이그레이션 적용
alembic upgrade head
```

### 주의사항

- `alembic/env.py`는 `.env` 파일의 `DATABASE_URL`을 자동으로 읽습니다.
- 자동 생성(`--autogenerate`) 시에는 반드시 생성된 파일을 검토한 후 적용하세요.
- pgvector 타입(`Vector(1536)`) 컬럼은 자동 감지되지 않을 수 있으므로, `file_chunks` 테이블 생성 마이그레이션에서 수동으로 확인이 필요합니다.
