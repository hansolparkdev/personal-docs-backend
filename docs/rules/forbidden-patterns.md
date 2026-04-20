# 금지 패턴

## 보안

- JWT 검증 없이 엔드포인트 노출 금지 — 모든 보호 라우트에 `Depends(get_current_user)` 필수
- 다른 유저의 파일/데이터 접근 금지 — 쿼리 시 항상 `user_id` 필터 포함
- `.env` 파일 커밋 금지 — `.env.example`만 커밋
- MinIO presigned URL 없이 파일 직접 노출 금지
- SQL 문자열 직접 조합 금지 — SQLAlchemy ORM / 파라미터 바인딩 사용

## FastAPI / 비즈니스 로직

- 라우터에 비즈니스 로직 직접 작성 금지 — `service` 레이어로 분리
- `async def` 없이 DB I/O 호출 금지 — 비동기 세션(`AsyncSession`) 사용
- 전역 `db` 객체 직접 사용 금지 — `Depends(get_db)` 의존성 주입
- `print()` 디버그 출력 금지 — `logging` 모듈 사용

## LangChain / RAG

- 전체 문서를 단일 프롬프트에 삽입 금지 — 반드시 청크+벡터 검색 거쳐야 함
- 유저 간 벡터 스토어 공유 금지 — 검색 시 `user_id` 메타데이터 필터 필수
- LLM 응답을 검증 없이 그대로 반환 금지 — 에러 처리 및 fallback 포함

## MinIO

- 버킷 이름에 유저 식별자 미포함 금지 — 경로 구조: `{user_id}/{file_id}/{filename}`
- 파일 업로드 전 타입·크기 검증 생략 금지

## 개발 프로세스

- `--no-verify` 우회 금지
- 테스트 없이 서비스 레이어 변경 금지
- 마이그레이션 없이 모델 변경 금지 — `alembic revision --autogenerate` 필수
