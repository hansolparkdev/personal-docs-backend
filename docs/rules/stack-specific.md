# 스택 특화 규율

> 범용 워크플로우 규율은 `dev-workflow.md`. 이 파일은 스택별 추가 규율.

## FastAPI + SQLAlchemy (AsyncSession)

개발 에이전트 착수 전 필수:
- `app/db/models/` Read — 필드명·relation 확인

규율:
- 서비스 메서드 작성 전 모델에서 필드명 확인
- 비동기 세션 사용: `async with AsyncSession() as session`
- `session.commit()` 후 반드시 `session.refresh(obj)` 호출
- `Depends(get_db)` 외 방식으로 세션 직접 생성 금지

## Keycloak JWT 인증

- 모든 보호 라우트: `current_user: dict = Depends(get_current_user)` 필수
- `get_current_user`는 Keycloak 공개키로 JWT 서명 검증
- 토큰에서 `sub` (user_id) 추출 — DB의 `user_id`와 매핑
- 권한 검증은 JWT `roles` 클레임 기반

## MinIO

개발 에이전트 착수 전 필수:
- `app/services/file_service.py` Read

규율:
- 업로드: `put_object` 사용, Content-Type 명시
- 다운로드 URL: presigned URL 발급 (유효기간 명시)
- 삭제: 논리 삭제(DB 플래그) 후 실제 MinIO 삭제
- 버킷 미존재 시 자동 생성 로직 포함

## LangChain / LangGraph RAG

개발 에이전트 착수 전 필수:
- `app/services/rag_service.py` Read

규율:
- 문서 청크: `RecursiveCharacterTextSplitter` 사용 (chunk_size=1000, overlap=200)
- 임베딩: pgvector에 저장, 메타데이터에 `user_id`·`file_id` 포함
- 검색 시 반드시 `filter={"user_id": current_user_id}` 적용
- LangGraph 상태는 `TypedDict` 기반으로 명시적 정의
- 스트리밍 응답: `StreamingResponse` + `async for chunk in chain.astream()`

## pytest

- DB 의존 테스트: `conftest.py`의 `db_session` fixture 사용 (트랜잭션 롤백)
- MinIO 의존 테스트: `moto` 또는 실제 테스트 버킷 사용
- LangChain 의존 테스트: LLM 호출은 mock, 청크·검색 로직만 실제 테스트

## Alembic

- 모델 변경 시 반드시 `alembic revision --autogenerate -m "설명"` 실행
- 마이그레이션 파일 커밋 전 `alembic upgrade head` 로컬 검증
- pgvector 확장: 첫 마이그레이션에 `CREATE EXTENSION IF NOT EXISTS vector` 포함
