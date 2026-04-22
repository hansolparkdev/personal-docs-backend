"""Tests for add-page-number feature.

Covers:
- FileChunk model has page_number column
- file_parser.parse_to_pages: PDF pages numbered, non-PDF returns None
- file_service.index_file: page_number stored in chunk
- rag_service.stream_rag_response: sources include page_number
"""
from __future__ import annotations

import io
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

USER_ID = "user-page-test"
FILE_ID = uuid.uuid4()


# ===========================================================================
# 1. FileChunk model — page_number column exists
# ===========================================================================


def test_file_chunk_has_page_number_column():
    """FileChunk must have a nullable page_number column."""
    from app.db.models.file_chunk import FileChunk
    from sqlalchemy import inspect

    mapper = inspect(FileChunk)
    col_names = [c.key for c in mapper.mapper.column_attrs]
    assert "page_number" in col_names


def test_file_chunk_page_number_nullable():
    """page_number column must allow None."""
    chunk = _make_chunk(page_number=None)
    assert chunk.page_number is None


def test_file_chunk_page_number_set():
    """page_number column stores integer value."""
    chunk = _make_chunk(page_number=3)
    assert chunk.page_number == 3


def _make_chunk(page_number: int | None = None):
    from app.db.models.file_chunk import FileChunk

    return FileChunk(
        file_id=FILE_ID,
        user_id=USER_ID,
        chunk_index=0,
        content="sample text",
        embedding=None,
        page_number=page_number,
    )


# ===========================================================================
# 2. file_parser.parse_to_pages
# ===========================================================================


def test_parse_to_pages_pdf_uses_markitdown():
    """PDF files: parse_to_pages uses MarkItDown and returns [(None, text)]."""
    from app.utils.file_parser import parse_to_pages

    with patch("app.utils.file_parser.parse_to_markdown", return_value="PDF 전체 텍스트"):
        result = parse_to_pages(b"fake_pdf_bytes", "document.pdf")

    assert result == [(None, "PDF 전체 텍스트")]


def test_parse_to_pages_pdf_markitdown_fail_raises():
    """PDF MarkItDown 파싱 실패 시 UnsupportedFormatError 발생."""
    from app.utils.file_parser import UnsupportedFormatError, parse_to_pages

    with patch("app.utils.file_parser.parse_to_markdown", side_effect=UnsupportedFormatError("fail")):
        with pytest.raises(UnsupportedFormatError):
            parse_to_pages(b"bad bytes", "bad.pdf")


def test_parse_to_pages_non_pdf_returns_none_page():
    """Non-PDF files: parse_to_pages returns [(None, markdown_text)]."""
    from app.utils.file_parser import parse_to_pages

    with patch("app.utils.file_parser.parse_to_markdown", return_value="# Hello") as mock_md:
        result = parse_to_pages(b"hello bytes", "document.txt")

    assert result == [(None, "# Hello")]
    mock_md.assert_called_once_with(b"hello bytes", "document.txt")


def test_parse_to_pages_docx_uses_markitdown():
    """DOCX files use MarkItDown path and return [(None, text)]."""
    from app.utils.file_parser import parse_to_pages

    with patch("app.utils.file_parser.parse_to_markdown", return_value="docx content"):
        result = parse_to_pages(b"docx bytes", "report.docx")

    assert len(result) == 1
    page_num, text = result[0]
    assert page_num is None
    assert text == "docx content"


# ===========================================================================
# 3. file_service.index_file — page_number stored in FileChunk
# ===========================================================================


@pytest.mark.asyncio
async def test_index_file_pdf_chunks_have_page_number():
    """index_file must set page_number on FileChunk for PDF files."""
    from app.db.models.file import File, IndexStatus
    from app.services.file_service import index_file

    db_file = File(
        id=FILE_ID,
        user_id=USER_ID,
        filename="test.pdf",
        content_type="application/pdf",
        size_bytes=100,
        minio_path=f"{USER_ID}/{FILE_ID}/test.pdf",
        index_status=IndexStatus.pending,
    )

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = db_file
    db.execute = AsyncMock(return_value=result_mock)
    db.commit = AsyncMock()

    added_chunks: list[Any] = []

    def capture_add(obj):
        added_chunks.append(obj)

    db.add = MagicMock(side_effect=capture_add)

    minio_response = MagicMock()
    minio_response.read.return_value = b"fake_pdf"
    minio_response.close = MagicMock()
    minio_response.release_conn = MagicMock()
    mock_minio = MagicMock()
    mock_minio.get_object.return_value = minio_response

    pages = [(1, "First page text"), (2, "Second page text")]
    embeddings_list = [[0.1] * 1536, [0.2] * 1536]

    mock_embeddings_model = AsyncMock()
    mock_embeddings_model.aembed_documents = AsyncMock(return_value=embeddings_list)

    with (
        patch("app.services.file_service.get_minio_client", return_value=mock_minio),
        patch("app.services.file_service.parse_to_pages", return_value=pages),
        patch("langchain_openai.OpenAIEmbeddings", return_value=mock_embeddings_model),
    ):
        await index_file(db, FILE_ID)

    file_chunks = [obj for obj in added_chunks if hasattr(obj, "page_number")]
    assert len(file_chunks) >= 2
    page_numbers = [c.page_number for c in file_chunks]
    assert 1 in page_numbers
    assert 2 in page_numbers


@pytest.mark.asyncio
async def test_index_file_non_pdf_chunks_have_none_page_number():
    """index_file must set page_number=None on FileChunk for non-PDF files."""
    from app.db.models.file import File, IndexStatus
    from app.services.file_service import index_file

    db_file = File(
        id=FILE_ID,
        user_id=USER_ID,
        filename="notes.txt",
        content_type="text/plain",
        size_bytes=50,
        minio_path=f"{USER_ID}/{FILE_ID}/notes.txt",
        index_status=IndexStatus.pending,
    )

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = db_file
    db.execute = AsyncMock(return_value=result_mock)
    db.commit = AsyncMock()

    added_chunks: list[Any] = []
    db.add = MagicMock(side_effect=lambda obj: added_chunks.append(obj))

    minio_response = MagicMock()
    minio_response.read.return_value = b"hello text"
    minio_response.close = MagicMock()
    minio_response.release_conn = MagicMock()
    mock_minio = MagicMock()
    mock_minio.get_object.return_value = minio_response

    pages = [(None, "All the text content")]
    embeddings_list = [[0.1] * 1536]

    mock_embeddings_model = AsyncMock()
    mock_embeddings_model.aembed_documents = AsyncMock(return_value=embeddings_list)

    with (
        patch("app.services.file_service.get_minio_client", return_value=mock_minio),
        patch("app.services.file_service.parse_to_pages", return_value=pages),
        patch("langchain_openai.OpenAIEmbeddings", return_value=mock_embeddings_model),
    ):
        await index_file(db, FILE_ID)

    file_chunks = [obj for obj in added_chunks if hasattr(obj, "page_number")]
    assert len(file_chunks) >= 1
    for chunk in file_chunks:
        assert chunk.page_number is None


# ===========================================================================
# 4. rag_service.stream_rag_response — sources include page_number
# ===========================================================================


@pytest.mark.asyncio
async def test_rag_sources_include_page_number():
    """sources event from stream_rag_response must include page_number field."""
    import json
    from app.db.models.file_chunk import FileChunk
    from app.db.models.chat import ChatSession
    from datetime import datetime, timezone

    db = AsyncMock()
    now = datetime.now(timezone.utc)
    session_id = uuid.uuid4()

    session = ChatSession(id=session_id, user_id=USER_ID, title=None)
    session.created_at = now
    session.updated_at = now

    chunk = FileChunk(
        file_id=FILE_ID,
        user_id=USER_ID,
        chunk_index=0,
        content="relevant content",
        embedding=[0.5] * 1536,
        page_number=3,
    )

    mock_file = MagicMock()
    mock_file.filename = "doc.pdf"

    mock_embeddings_model = AsyncMock()
    mock_embeddings_model.aembed_query = AsyncMock(return_value=[0.5] * 1536)

    mock_llm = MagicMock()

    async def _fake_astream(_msgs):
        token = MagicMock()
        token.content = "답변 텍스트"
        yield token

    mock_llm.astream = _fake_astream

    with (
        patch("app.services.rag_service.get_session", new=AsyncMock(return_value=session)),
        patch("app.services.rag_service.save_user_message", new=AsyncMock()),
        patch("app.services.rag_service.set_session_title", new=AsyncMock()),
        patch("app.services.rag_service.search_similar_chunks", new=AsyncMock(return_value=[(chunk, 0.3)])),
        patch("app.services.rag_service.get_recent_messages", new=AsyncMock(return_value=[])),
        patch("app.services.rag_service.get_file", new=AsyncMock(return_value=mock_file)),
        patch("app.services.rag_service.save_assistant_message", new=AsyncMock()),
        patch("app.services.rag_service.OpenAIEmbeddings", return_value=mock_embeddings_model),
        patch("app.services.rag_service.ChatOpenAI", return_value=mock_llm),
    ):
        from app.services.rag_service import stream_rag_response

        events = []
        async for event in stream_rag_response(db, session_id, USER_ID, "질문"):
            events.append(event)

    sources_events = [e for e in events if "event: sources" in e]
    assert len(sources_events) == 1

    data_line = sources_events[0].split("\n")[1]
    payload = json.loads(data_line.removeprefix("data: "))
    sources = payload["sources"]
    assert len(sources) >= 1
    assert "page_number" in sources[0]
    assert sources[0]["page_number"] == 3
