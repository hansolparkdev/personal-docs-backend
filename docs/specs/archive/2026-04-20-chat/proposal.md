## Why

업로드·색인된 개인 문서가 저장소에만 존재하고 실제로 활용되지 않는 문제를 해결한다. 사용자가 자연어로 질문하면 자신의 색인 완료 문서만을 근거로 스트리밍 답변과 출처를 받을 수 있도록, RAG 인프라를 실제 사용자 가치로 연결하는 대화 인터페이스를 추가한다.

## What Changes

- `chat_sessions` 테이블 신설: JWT sub 기준 소유권 격리, 첫 메시지 앞 20자 자동 제목 생성
- `chat_messages` 테이블 신설: role(user/assistant), content, sources(JSONB) 저장, session_id FK CASCADE
- `app/api/v1/chat.py` 신설: 세션 CRUD + 메시지 SSE 스트리밍 엔드포인트 5개
- `app/services/chat_service.py` 신설: 세션·메시지 비즈니스 로직
- `app/services/rag_service.py` 신설: LangGraph 기반 RAG 파이프라인 (pgvector 검색, LLM 스트리밍)
- `app/db/models/chat.py` 신설: ChatSession, ChatMessage ORM 모델
- `app/schemas/chat.py` 신설: 요청·응답 Pydantic 스키마
- Alembic 마이그레이션 추가

## Capabilities

### New Capabilities

- `chat-session`: 세션 생성·목록 조회(최대 50개 최신순)·단건 조회(메시지 포함)·삭제. JWT sub 기준 소유권 격리. 타인 세션 접근 → 404.
- `chat-message`: 특정 세션에 사용자 메시지 전송 → LangGraph RAG 파이프라인 실행 → SSE 스트리밍(token / sources / done 이벤트). 색인 청크 없음 → "참고할 문서가 없습니다" 스트리밍 응답. 스트리밍 중단 시 부분 답변 폐기.

### Modified Capabilities

없음. 기존 auth-*, file-* capability는 변경 없음.

## Impact

- 신규 파일
  - `app/db/models/chat.py`
  - `app/services/chat_service.py`
  - `app/services/rag_service.py`
  - `app/api/v1/chat.py`
  - `app/schemas/chat.py`
  - `alembic/versions/<revision>_add_chat_tables.py`
- 수정 파일
  - `app/api/v1/router.py` — chat 라우터 include
  - `app/db/models/__init__.py` — ChatSession, ChatMessage import (Alembic autogenerate 인식용)

## Meta

- feature: chat
- type: backend
- package: backend

프리로드: folder-conventions.md · dev-flow.md · forbidden-patterns.md
