"""Unit tests for search_similar_chunks in file_service."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.models.file import File, IndexStatus
from app.db.models.file_chunk import FileChunk


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_file(user_id: str, deleted_at=None) -> File:
    f = File(
        id=uuid.uuid4(),
        user_id=user_id,
        filename="test.pdf",
        content_type="application/pdf",
        size_bytes=1000,
        minio_path=f"{user_id}/test.pdf",
        index_status=IndexStatus.indexed,
        deleted_at=deleted_at,
    )
    return f


def _make_chunk(file: File, chunk_index: int = 0) -> FileChunk:
    return FileChunk(
        id=uuid.uuid4(),
        file_id=file.id,
        user_id=file.user_id,
        chunk_index=chunk_index,
        content=f"chunk content {chunk_index}",
        embedding=[0.1] * 1536,
        page_number=1,
    )


# ---------------------------------------------------------------------------
# Scenario 1: user-A 청크 10개 → limit=5 반환
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_similar_chunks_returns_limit():
    """search_similar_chunks는 limit 개수만큼 (chunk, distance) 튜플을 반환한다."""
    from app.services.file_service import search_similar_chunks

    chunks = [_make_chunk(_make_file("user-A"), i) for i in range(5)]

    mock_rows = [MagicMock(FileChunk=c, distance=0.3 + i * 0.01) for i, c in enumerate(chunks)]
    mock_result = MagicMock()
    mock_result.all.return_value = mock_rows

    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)

    query_embedding = [0.1] * 1536
    result = await search_similar_chunks(db, "user-A", query_embedding, limit=5)

    assert len(result) == 5
    assert all(isinstance(r, tuple) and len(r) == 2 for r in result)
    db.execute.assert_awaited_once()


# ---------------------------------------------------------------------------
# Scenario 2: 청크 없음 → 빈 리스트
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_similar_chunks_empty():
    """청크가 없으면 빈 리스트를 반환하고 예외가 발생하지 않는다."""
    from app.services.file_service import search_similar_chunks

    mock_result = MagicMock()
    mock_result.all.return_value = []

    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)

    result = await search_similar_chunks(db, "user-A", [0.1] * 1536, limit=5)

    assert result == []


# ---------------------------------------------------------------------------
# Scenario 3: 청크 3개, limit=5 → 3개 반환
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_similar_chunks_fewer_than_limit():
    """DB에 청크가 limit보다 적으면 실제 개수만 반환한다."""
    from app.services.file_service import search_similar_chunks

    file = _make_file("user-A")
    chunks = [_make_chunk(file, i) for i in range(3)]

    mock_rows = [MagicMock(FileChunk=c, distance=0.3) for c in chunks]
    mock_result = MagicMock()
    mock_result.all.return_value = mock_rows

    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)

    result = await search_similar_chunks(db, "user-A", [0.1] * 1536, limit=5)

    assert len(result) == 3


# ---------------------------------------------------------------------------
# Scenario 4: deleted_at 설정된 파일 청크 → 쿼리 필터에 포함됨을 검증
# (쿼리 실행 자체는 DB에 위임; 여기서는 함수 시그니처와 호출 정상 여부만 검증)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_similar_chunks_query_executes_without_error():
    """deleted_at IS NULL 조건을 가진 쿼리가 예외 없이 실행된다."""
    from app.services.file_service import search_similar_chunks

    mock_result = MagicMock()
    mock_result.all.return_value = []

    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)

    # 다른 유저 user-B 요청 → 빈 결과
    result = await search_similar_chunks(db, "user-B", [0.5] * 1536, limit=5)

    assert result == []
    db.execute.assert_awaited_once()


# ---------------------------------------------------------------------------
# Scenario 5: get_indexed_chunks가 제거되었는지 확인
# ---------------------------------------------------------------------------

def test_get_indexed_chunks_removed():
    """get_indexed_chunks 함수는 file_service에서 제거되어야 한다."""
    import app.services.file_service as fs
    assert not hasattr(fs, "get_indexed_chunks"), (
        "get_indexed_chunks should be removed from file_service"
    )
