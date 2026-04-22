"""Tests for chat endpoints and services (app/api/v1/chat.py, app/services/chat_service.py)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.chat import ChatMessage, ChatSession
from app.db.models.user import User
from app.main import app

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

USER_ID = "user-chat-111"
OTHER_USER_ID = "user-chat-999"
SESSION_ID = uuid.uuid4()
MSG_ID = uuid.uuid4()

NOW = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session(
    session_id: uuid.UUID | None = None,
    user_id: str = USER_ID,
    title: str | None = "테스트 세션",
) -> ChatSession:
    s = ChatSession(
        id=session_id or uuid.uuid4(),
        user_id=user_id,
        title=title,
    )
    s.created_at = NOW
    s.updated_at = NOW
    return s


def _make_message(
    msg_id: uuid.UUID | None = None,
    session_id: uuid.UUID | None = None,
    user_id: str = USER_ID,
    role: str = "user",
    content: str = "안녕하세요",
    sources: list[dict[str, Any]] | None = None,
) -> ChatMessage:
    m = ChatMessage(
        id=msg_id or uuid.uuid4(),
        session_id=session_id or SESSION_ID,
        user_id=user_id,
        role=role,
        content=content,
        sources=sources,
    )
    m.created_at = NOW
    return m


def _fake_current_user(user_id: str = USER_ID):
    fake_user = User(
        id=uuid.uuid4(),
        auth_id=user_id,
        username=user_id,
        email=f"{user_id}@example.com",
    )

    async def _override():
        return fake_user

    return _override


def _fake_db():
    async def _override():
        yield AsyncMock()

    return _override


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def authed_client():
    app.dependency_overrides[get_current_user] = _fake_current_user(USER_ID)
    app.dependency_overrides[get_db] = _fake_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def unauthed_client():
    app.dependency_overrides.clear()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# 1. 세션 생성 → 201
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_session_returns_201(authed_client):
    session = _make_session(session_id=SESSION_ID)

    with patch("app.services.chat_service.create_session", new_callable=AsyncMock, return_value=session):
        response = await authed_client.post("/api/v1/chats")

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == str(SESSION_ID)


# ---------------------------------------------------------------------------
# 2. 세션 목록 → 200, 본인 세션만
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_sessions_returns_own_sessions(authed_client):
    sessions = [_make_session(), _make_session()]

    with patch("app.services.chat_service.list_sessions", new_callable=AsyncMock, return_value=sessions):
        response = await authed_client.get("/api/v1/chats")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


# ---------------------------------------------------------------------------
# 3. 세션 상세 조회 → 200
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_session_detail_returns_200(authed_client):
    session = _make_session(session_id=SESSION_ID)
    session.messages = [_make_message(session_id=SESSION_ID)]

    with patch(
        "app.services.chat_service.get_session_with_messages",
        new_callable=AsyncMock,
        return_value=session,
    ):
        response = await authed_client.get(f"/api/v1/chats/{SESSION_ID}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(SESSION_ID)
    assert len(data["messages"]) == 1


# ---------------------------------------------------------------------------
# 4. 타인 세션 조회 → 404
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_other_user_session_returns_404(authed_client):
    with patch(
        "app.services.chat_service.get_session_with_messages",
        new_callable=AsyncMock,
        return_value=None,
    ):
        response = await authed_client.get(f"/api/v1/chats/{SESSION_ID}")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# 5. 세션 삭제 → 204
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_session_returns_204(authed_client):
    with patch("app.services.chat_service.delete_session", new_callable=AsyncMock, return_value=True):
        response = await authed_client.delete(f"/api/v1/chats/{SESSION_ID}")

    assert response.status_code == 204


# ---------------------------------------------------------------------------
# 6. 타인 세션 삭제 → 404
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_other_user_session_returns_404(authed_client):
    with patch("app.services.chat_service.delete_session", new_callable=AsyncMock, return_value=False):
        response = await authed_client.delete(f"/api/v1/chats/{SESSION_ID}")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# 7. 토큰 없음 → 401
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_session_no_auth(unauthed_client):
    response = await unauthed_client.post("/api/v1/chats")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_send_message_no_auth(unauthed_client):
    response = await unauthed_client.post(
        f"/api/v1/chats/{SESSION_ID}/messages",
        json={"content": "질문입니다"},
    )
    assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# 8. 메시지 전송 → SSE Content-Type 확인
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_message_sse_content_type(authed_client):
    session = _make_session(session_id=SESSION_ID)

    async def _fake_stream(*args, **kwargs):
        yield "event: token\ndata: {\"text\": \"안녕\"}\n\n"
        yield "event: sources\ndata: {\"sources\": []}\n\n"
        yield "event: done\ndata: {}\n\n"

    with (
        patch("app.api.v1.chat.svc.get_session", new_callable=AsyncMock, return_value=session),
        patch("app.api.v1.chat.stream_rag_response", side_effect=_fake_stream),
    ):
        response = await authed_client.post(
            f"/api/v1/chats/{SESSION_ID}/messages",
            json={"content": "안녕하세요"},
        )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]


# ---------------------------------------------------------------------------
# 9. 색인 없음 → fallback 스트림
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_message_no_chunks_fallback(authed_client):
    session = _make_session(session_id=SESSION_ID)

    async def _fallback_stream(*args, **kwargs):
        yield "event: token\ndata: {\"text\": \"참고할 문서가 없습니다. 파일을 업로드하고 색인을 완료해 주세요.\"}\n\n"
        yield "event: sources\ndata: {\"sources\": []}\n\n"
        yield "event: done\ndata: {}\n\n"

    with (
        patch("app.api.v1.chat.svc.get_session", new_callable=AsyncMock, return_value=session),
        patch("app.api.v1.chat.stream_rag_response", side_effect=_fallback_stream),
    ):
        response = await authed_client.post(
            f"/api/v1/chats/{SESSION_ID}/messages",
            json={"content": "질문입니다"},
        )

    assert response.status_code == 200
    content = response.text
    assert "참고할 문서가 없습니다" in content


# ---------------------------------------------------------------------------
# 10. 메시지 전송 - 존재하지 않는 세션 → 404
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_message_to_nonexistent_session_returns_404(authed_client):
    with patch("app.api.v1.chat.svc.get_session", new_callable=AsyncMock, return_value=None):
        response = await authed_client.post(
            f"/api/v1/chats/{SESSION_ID}/messages",
            json={"content": "안녕"},
        )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Unit tests: chat_service.py
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_service_create_session():
    """create_session must persist a ChatSession with user_id."""
    db = AsyncMock()

    from app.services.chat_service import create_session

    session = await create_session(db, USER_ID)
    assert session.user_id == USER_ID
    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_service_list_sessions_uses_user_filter():
    """list_sessions must query by user_id."""
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=result_mock)

    from app.services.chat_service import list_sessions

    sessions = await list_sessions(db, USER_ID)
    assert sessions == []
    db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_service_delete_session_returns_false_when_not_found():
    """delete_session returns False when session not found."""
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result_mock)

    from app.services.chat_service import delete_session

    result = await delete_session(db, SESSION_ID, USER_ID)
    assert result is False


@pytest.mark.asyncio
async def test_service_save_user_message():
    """save_user_message must create a ChatMessage with role='user'."""
    db = AsyncMock()

    from app.services.chat_service import save_user_message

    msg = await save_user_message(db, SESSION_ID, USER_ID, "테스트 메시지")
    assert msg.role == "user"
    assert msg.content == "테스트 메시지"
    assert msg.session_id == SESSION_ID
    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_service_save_assistant_message():
    """save_assistant_message must create a ChatMessage with role='assistant'."""
    db = AsyncMock()
    sources = [{"file_id": "abc", "chunk_index": 0}]

    from app.services.chat_service import save_assistant_message

    msg = await save_assistant_message(db, SESSION_ID, USER_ID, "답변입니다", sources)
    assert msg.role == "assistant"
    assert msg.sources == sources
    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_service_get_recent_messages():
    """get_recent_messages must query messages by session_id."""
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=result_mock)

    from app.services.chat_service import get_recent_messages

    msgs = await get_recent_messages(db, SESSION_ID, limit=20)
    assert msgs == []
    db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_service_set_session_title():
    """set_session_title must update title on the session object."""
    db = AsyncMock()
    session = _make_session(session_id=SESSION_ID, title=None)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = session
    db.execute = AsyncMock(return_value=result_mock)

    from app.services.chat_service import set_session_title

    await set_session_title(db, SESSION_ID, "새 제목")
    assert session.title == "새 제목"
    db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# RAG service: stream_rag_response no-chunks path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rag_stream_no_chunks_yields_fallback():
    """stream_rag_response yields fallback when no chunks exist."""
    db = AsyncMock()
    session = _make_session(session_id=SESSION_ID, title=None)

    mock_embed = AsyncMock()
    mock_embed.aembed_query = AsyncMock(return_value=[0.1] * 1536)

    with (
        patch("app.services.rag_service.get_session", new=AsyncMock(return_value=session)),
        patch("app.services.rag_service.save_user_message", new=AsyncMock()),
        patch("app.services.rag_service.set_session_title", new=AsyncMock()),
        patch("app.services.rag_service.get_recent_messages", new=AsyncMock(return_value=[])),
        patch("app.services.rag_service.search_similar_chunks", new=AsyncMock(return_value=[])),
        patch("app.services.rag_service.save_assistant_message", new=AsyncMock()),
        patch("app.services.rag_service.OpenAIEmbeddings", return_value=mock_embed),
    ):
        from app.services.rag_service import stream_rag_response

        events = []
        async for event in stream_rag_response(db, SESSION_ID, USER_ID, "질문"):
            events.append(event)

    assert any("참고할 문서가 없습니다" in e for e in events)
    assert any("event: done" in e for e in events)
