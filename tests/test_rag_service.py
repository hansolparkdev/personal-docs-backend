"""Unit tests for rag_service — numpy 제거, 검색 교체, 히스토리 중복 버그 수정."""
from __future__ import annotations

import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chunk(file_id=None, chunk_index=0, content="chunk text"):
    chunk = MagicMock()
    chunk.id = uuid.uuid4()
    chunk.file_id = file_id or uuid.uuid4()
    chunk.chunk_index = chunk_index
    chunk.content = content
    chunk.embedding = [0.1] * 1536
    chunk.page_number = 1
    return chunk


def _make_chunk_result(chunk=None, distance=0.3):
    """(FileChunk, distance) 튜플 반환."""
    return (chunk or _make_chunk(), distance)


def _make_message(role: str, content: str):
    msg = MagicMock()
    msg.role = role
    msg.content = content
    return msg


async def _collect(gen: AsyncGenerator) -> list[str]:
    return [item async for item in gen]


def _rag_patches(
    *,
    session=None,
    chunks=None,
    messages=None,
    file_obj=None,
):
    """rag_service 모듈 레벨 임포트 대상 패치 컨텍스트를 반환한다."""
    if session is None:
        session = MagicMock()
        session.title = "title"
    if chunks is None:
        chunks = []
    if messages is None:
        messages = []
    if file_obj is None:
        file_obj = MagicMock()
        file_obj.filename = "test.pdf"

    return [
        patch("app.services.rag_service.get_session", new=AsyncMock(return_value=session)),
        patch("app.services.rag_service.set_session_title", new=AsyncMock()),
        patch("app.services.rag_service.get_recent_messages", new=AsyncMock(return_value=messages)),
        patch("app.services.rag_service.save_user_message", new=AsyncMock()),
        patch("app.services.rag_service.save_assistant_message", new=AsyncMock()),
        patch("app.services.rag_service.search_similar_chunks", new=AsyncMock(return_value=chunks)),
        patch("app.services.rag_service.get_file", new=AsyncMock(return_value=file_obj)),
    ]


# ---------------------------------------------------------------------------
# Task 3.1 — numpy import 제거 검증
# ---------------------------------------------------------------------------

def test_rag_service_no_numpy_import():
    """rag_service 모듈에 numpy import가 없어야 한다."""
    import app.services.rag_service as mod
    source_file = mod.__file__
    with open(source_file) as f:
        source = f.read()
    assert "import numpy" not in source, "rag_service must not import numpy"
    assert "numpy as np" not in source, "rag_service must not import numpy as np"


def test_cosine_sim_function_removed():
    """_cosine_sim 함수는 rag_service에서 제거되어야 한다."""
    import app.services.rag_service as mod
    assert not hasattr(mod, "_cosine_sim"), "_cosine_sim should be removed from rag_service"


# ---------------------------------------------------------------------------
# Task 3.2 — search_similar_chunks 호출로 교체
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stream_rag_uses_search_similar_chunks():
    """stream_rag_response는 search_similar_chunks를 호출해야 한다."""
    from app.services import rag_service

    db = AsyncMock()
    chunk = _make_chunk()
    query_embedding = [0.1] * 1536

    mock_search = AsyncMock(return_value=[_make_chunk_result(chunk)])
    mock_embed = AsyncMock()
    mock_embed.aembed_query = AsyncMock(return_value=query_embedding)

    session = MagicMock()
    session.title = "existing title"

    mock_llm = MagicMock()
    async def fake_stream(_):
        token = MagicMock()
        token.content = "answer"
        yield token
    mock_llm.astream = fake_stream

    with (
        patch("app.services.rag_service.get_session", new=AsyncMock(return_value=session)),
        patch("app.services.rag_service.set_session_title", new=AsyncMock()),
        patch("app.services.rag_service.get_recent_messages", new=AsyncMock(return_value=[])),
        patch("app.services.rag_service.save_user_message", new=AsyncMock()),
        patch("app.services.rag_service.save_assistant_message", new=AsyncMock()),
        patch("app.services.rag_service.search_similar_chunks", new=mock_search),
        patch("app.services.rag_service.get_file", new=AsyncMock(return_value=MagicMock(filename="test.pdf"))),
        patch("app.services.rag_service.OpenAIEmbeddings", return_value=mock_embed),
        patch("app.services.rag_service.ChatOpenAI", return_value=mock_llm),
    ):
        events = await _collect(
            rag_service.stream_rag_response(db, "sess-1", "user-A", "질문")
        )

    mock_search.assert_awaited_once()
    call_args = mock_search.call_args
    assert call_args.args[1] == "user-A"        # user_id
    assert call_args.args[2] == query_embedding  # query_embedding


# ---------------------------------------------------------------------------
# Task 4.1 — 히스토리 중복 버그: save_user_message 순서 검증
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_save_user_message_called_after_llm():
    """save_user_message는 LLM 스트리밍 완료 이후에 호출되어야 한다."""
    from app.services import rag_service

    db = AsyncMock()
    chunk = _make_chunk()
    call_order: list[str] = []

    async def fake_get_recent(db, session_id, limit=20):
        call_order.append("get_history")
        return []

    async def fake_save_user(db, session_id, user_id, query):
        call_order.append("save_user")

    async def fake_save_ai(db, session_id, user_id, answer, sources):
        call_order.append("save_ai")

    mock_embed = AsyncMock()
    mock_embed.aembed_query = AsyncMock(return_value=[0.1] * 1536)

    session = MagicMock()
    session.title = "title"

    mock_llm = MagicMock()
    async def fake_stream(_):
        token = MagicMock()
        token.content = "response"
        yield token
    mock_llm.astream = fake_stream

    with (
        patch("app.services.rag_service.get_session", new=AsyncMock(return_value=session)),
        patch("app.services.rag_service.set_session_title", new=AsyncMock()),
        patch("app.services.rag_service.get_recent_messages", new=fake_get_recent),
        patch("app.services.rag_service.save_user_message", new=fake_save_user),
        patch("app.services.rag_service.save_assistant_message", new=fake_save_ai),
        patch("app.services.rag_service.search_similar_chunks", new=AsyncMock(return_value=[_make_chunk_result(chunk)])),
        patch("app.services.rag_service.get_file", new=AsyncMock(return_value=MagicMock(filename="f.pdf"))),
        patch("app.services.rag_service.OpenAIEmbeddings", return_value=mock_embed),
        patch("app.services.rag_service.ChatOpenAI", return_value=mock_llm),
    ):
        await _collect(
            rag_service.stream_rag_response(db, "sess-1", "user-A", "질문")
        )

    # get_history → LLM → save_user → save_ai 순서 확인
    assert "get_history" in call_order
    assert "save_user" in call_order
    assert "save_ai" in call_order

    history_idx = call_order.index("get_history")
    save_user_idx = call_order.index("save_user")
    save_ai_idx = call_order.index("save_ai")

    assert history_idx < save_user_idx, "get_history must come before save_user"
    assert save_user_idx < save_ai_idx, "save_user must come before save_ai"


# ---------------------------------------------------------------------------
# Scenario: 첫 메시지 → 히스토리 빈 리스트, 현재 질문 1회만 전달
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_first_message_history_empty():
    """첫 메시지 시 히스토리가 비어있어, LLM에는 질문이 1회만 전달된다."""
    from app.services import rag_service

    db = AsyncMock()
    chunk = _make_chunk()
    captured_messages: list = []

    mock_embed = AsyncMock()
    mock_embed.aembed_query = AsyncMock(return_value=[0.1] * 1536)

    session = MagicMock()
    session.title = None

    mock_llm = MagicMock()
    async def fake_stream(msgs):
        captured_messages.extend(msgs)
        token = MagicMock()
        token.content = "답변"
        yield token
    mock_llm.astream = fake_stream

    with (
        patch("app.services.rag_service.get_session", new=AsyncMock(return_value=session)),
        patch("app.services.rag_service.set_session_title", new=AsyncMock()),
        patch("app.services.rag_service.get_recent_messages", new=AsyncMock(return_value=[])),
        patch("app.services.rag_service.save_user_message", new=AsyncMock()),
        patch("app.services.rag_service.save_assistant_message", new=AsyncMock()),
        patch("app.services.rag_service.search_similar_chunks", new=AsyncMock(return_value=[_make_chunk_result(chunk)])),
        patch("app.services.rag_service.get_file", new=AsyncMock(return_value=MagicMock(filename="f.pdf"))),
        patch("app.services.rag_service.OpenAIEmbeddings", return_value=mock_embed),
        patch("app.services.rag_service.ChatOpenAI", return_value=mock_llm),
    ):
        await _collect(
            rag_service.stream_rag_response(db, "sess-1", "user-A", "첫 질문")
        )

    from langchain.schema import HumanMessage
    human_messages = [m for m in captured_messages if isinstance(m, HumanMessage)]
    # SystemMessage(context) + HumanMessage(query) — 히스토리 없으므로 HumanMessage 1개
    assert len(human_messages) == 1
    assert human_messages[0].content == "첫 질문"


# ---------------------------------------------------------------------------
# Scenario: 청크 없음 → fallback 응답
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_chunks_returns_fallback():
    """청크가 없으면 fallback 이벤트를 반환한다."""
    from app.services import rag_service

    db = AsyncMock()
    session = MagicMock()
    session.title = "t"

    mock_embed = AsyncMock()
    mock_embed.aembed_query = AsyncMock(return_value=[0.1] * 1536)

    with (
        patch("app.services.rag_service.get_session", new=AsyncMock(return_value=session)),
        patch("app.services.rag_service.set_session_title", new=AsyncMock()),
        patch("app.services.rag_service.get_recent_messages", new=AsyncMock(return_value=[])),
        patch("app.services.rag_service.save_user_message", new=AsyncMock()),
        patch("app.services.rag_service.save_assistant_message", new=AsyncMock()),
        patch("app.services.rag_service.search_similar_chunks", new=AsyncMock(return_value=[])),
        patch("app.services.rag_service.OpenAIEmbeddings", return_value=mock_embed),
    ):
        events = await _collect(
            rag_service.stream_rag_response(db, "sess-1", "user-A", "질문")
        )

    assert any("참고할 문서가 없습니다" in e for e in events)
    done_events = [e for e in events if "done" in e]
    assert len(done_events) >= 1
