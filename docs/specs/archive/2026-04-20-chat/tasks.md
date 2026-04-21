## 1. DB 모델 및 마이그레이션

- [ ] 1.1 ChatSession, ChatMessage ORM 모델 작성
  - 수정 파일: `app/db/models/chat.py`
- [ ] 1.2 models __init__에 신규 모델 import 추가 (Alembic autogenerate 인식)
  - 수정 파일: `app/db/models/__init__.py`
- [ ] 1.3 Alembic 마이그레이션 생성 (`chat_sessions`, `chat_messages` 테이블, CASCADE FK, 인덱스)
  - 수정 파일: `alembic/versions/<revision>_add_chat_tables.py`

## 2. Pydantic 스키마

- [ ] 2.1 요청·응답 스키마 작성
  - `ChatSessionCreate` (body 없음)
  - `ChatSessionResponse` (id, title, created_at, updated_at)
  - `ChatSessionDetailResponse` (세션 + messages 리스트)
  - `ChatMessageResponse` (id, session_id, role, content, sources, created_at)
  - `SendMessageRequest` (content: str)
  - 수정 파일: `app/schemas/chat.py`

## 3. 서비스 레이어

- [ ] 3.1 세션 CRUD 서비스 구현
  - `create_session(db, user_id) -> ChatSession`
  - `list_sessions(db, user_id, limit=50) -> list[ChatSession]`
  - `get_session(db, session_id, user_id) -> ChatSession | None`
  - `delete_session(db, session_id, user_id) -> bool`
  - `set_session_title(db, session_id, title) -> None` (첫 메시지 앞 20자)
  - 수정 파일: `app/services/chat_service.py`
- [ ] 3.2 메시지 저장 서비스 구현
  - `save_user_message(db, session_id, user_id, content) -> ChatMessage`
  - `save_assistant_message(db, session_id, user_id, content, sources) -> ChatMessage`
  - `get_recent_messages(db, session_id, limit=20) -> list[ChatMessage]` (최근 10턴 = 20개)
  - 수정 파일: `app/services/chat_service.py`

## 4. RAG 파이프라인

- [ ] 4.1 LangGraph StateGraph 정의
  - State: `{ messages, user_id, query, chunks, answer_tokens, sources }`
  - 노드: `load_history` → `retrieve` → `generate`
  - 수정 파일: `app/services/rag_service.py`
- [ ] 4.2 `load_history` 노드: `get_recent_messages`로 최근 10턴 로드, LangChain `HumanMessage`/`AIMessage` 변환
  - 수정 파일: `app/services/rag_service.py`
- [ ] 4.3 `retrieve` 노드: `get_indexed_chunks(db, user_id)` 호출 → pgvector similarity search K=5, user_id 필터 필수
  - 수정 파일: `app/services/rag_service.py`
- [ ] 4.4 `generate` 노드: 컨텍스트 + 히스토리 → OpenAI ChatModel 스트리밍, 색인 청크 없을 시 fallback 메시지
  - 수정 파일: `app/services/rag_service.py`
- [ ] 4.5 스트리밍 제너레이터 함수 구현: token 이벤트 순차 yield → sources 이벤트 yield → done 이벤트 yield → DB 저장
  - 수정 파일: `app/services/rag_service.py`

## 5. API 라우터

- [ ] 5.1 chat 라우터 5개 엔드포인트 구현
  - `POST /api/v1/chats` — 세션 생성
  - `GET /api/v1/chats` — 세션 목록 (최대 50개, 최신순)
  - `GET /api/v1/chats/{session_id}` — 세션 단건 (메시지 포함)
  - `DELETE /api/v1/chats/{session_id}` — 세션 삭제
  - `POST /api/v1/chats/{session_id}/messages` — 메시지 전송 + SSE 스트리밍
  - 모든 엔드포인트에 `Depends(get_current_user)` 적용
  - 수정 파일: `app/api/v1/chat.py`
- [ ] 5.2 v1 라우터에 chat 라우터 include
  - 수정 파일: `app/api/v1/router.py`
