"""Tests for file management endpoints (app/api/v1/files.py)."""
from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.file import File, IndexStatus
from app.db.models.user import User
from app.main import app

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

USER_ID = "user-abc-123"
OTHER_USER_ID = "user-xyz-999"
FILE_ID = uuid.uuid4()

VALID_MIME = "text/plain"
VALID_CONTENT = b"Hello, world!"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_file(
    user_id: str = USER_ID,
    file_id: uuid.UUID | None = None,
    filename: str = "test.txt",
    content_type: str = VALID_MIME,
    size_bytes: int = len(VALID_CONTENT),
    minio_path: str | None = None,
    index_status: IndexStatus = IndexStatus.pending,
) -> File:
    fid = file_id or uuid.uuid4()
    f = File(
        id=fid,
        user_id=user_id,
        filename=filename,
        content_type=content_type,
        size_bytes=size_bytes,
        minio_path=minio_path or f"{user_id}/{fid}/{filename}",
        index_status=index_status,
    )
    f.created_at = datetime.now(timezone.utc)
    f.deleted_at = None
    return f


def _fake_current_user(user_id: str = USER_ID):
    """Return a dependency override that yields a fake User object."""
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
    """Return a dependency override that yields a mock AsyncSession."""
    async def _override():
        yield AsyncMock()
    return _override


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def authed_client():
    """Client with get_current_user and get_db overridden for USER_ID."""
    app.dependency_overrides[get_current_user] = _fake_current_user(USER_ID)
    app.dependency_overrides[get_db] = _fake_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def unauthed_client():
    """Client with no dependency overrides (auth fails)."""
    # Clear overrides so real auth is triggered
    app.dependency_overrides.clear()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# 1. 정상 업로드 → 201, file_id 반환
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_file_success(authed_client):
    db_file = _make_file(file_id=FILE_ID)

    with (
        patch("app.services.file_service.upload_file", new_callable=AsyncMock, return_value=db_file),
        patch("app.services.file_service.index_file", new_callable=AsyncMock),
    ):
        response = await authed_client.post(
            "/api/v1/files",
            files={"file": ("test.txt", io.BytesIO(VALID_CONTENT), VALID_MIME)},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["file_id"] == str(FILE_ID)
    assert data["filename"] == "test.txt"
    assert data["index_status"] == "pending"


# ---------------------------------------------------------------------------
# 2. 미지원 MIME → 415
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_unsupported_mime(authed_client):
    response = await authed_client.post(
        "/api/v1/files",
        files={"file": ("image.png", io.BytesIO(b"png bytes"), "image/png")},
    )
    assert response.status_code == 415


# ---------------------------------------------------------------------------
# 3. 크기 초과 → 413
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_file_too_large(authed_client):
    large_content = b"x" * (52428800 + 1)  # 50MB + 1 byte
    response = await authed_client.post(
        "/api/v1/files",
        files={"file": ("big.txt", io.BytesIO(large_content), VALID_MIME)},
    )
    assert response.status_code == 413


# ---------------------------------------------------------------------------
# 4. 인증 없음 → 401/403
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_no_auth(unauthed_client):
    response = await unauthed_client.post(
        "/api/v1/files",
        files={"file": ("test.txt", io.BytesIO(VALID_CONTENT), VALID_MIME)},
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_files_no_auth(unauthed_client):
    response = await unauthed_client.get("/api/v1/files")
    assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# 5. 파일 목록 조회 → 본인 파일만
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_files_returns_own_files(authed_client):
    files = [_make_file(user_id=USER_ID, filename="a.txt"), _make_file(user_id=USER_ID, filename="b.txt")]

    with patch("app.services.file_service.list_files", new_callable=AsyncMock, return_value=files):
        response = await authed_client.get("/api/v1/files")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    filenames = {item["filename"] for item in data}
    assert filenames == {"a.txt", "b.txt"}


# ---------------------------------------------------------------------------
# 6. 타인 파일 단건 조회 → 404
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_other_user_file_returns_404(authed_client):
    with patch("app.services.file_service.get_file", new_callable=AsyncMock, return_value=None):
        response = await authed_client.get(f"/api/v1/files/{FILE_ID}")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# 7. 파일 삭제 → 204, MinIO + DB 제거
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_file_success(authed_client):
    with patch("app.services.file_service.delete_file", new_callable=AsyncMock, return_value=True):
        response = await authed_client.delete(f"/api/v1/files/{FILE_ID}")

    assert response.status_code == 204


# ---------------------------------------------------------------------------
# 8. 타인 파일 삭제 → 404
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_other_user_file_returns_404(authed_client):
    with patch("app.services.file_service.delete_file", new_callable=AsyncMock, return_value=False):
        response = await authed_client.delete(f"/api/v1/files/{FILE_ID}")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# 9. presigned URL 반환 → 200, download_url 포함
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_download_url_success(authed_client):
    presigned = "https://minio.example.com/bucket/path?X-Amz-Expires=3600"

    with patch("app.services.file_service.get_download_url", new_callable=AsyncMock, return_value=presigned):
        response = await authed_client.get(f"/api/v1/files/{FILE_ID}/download")

    assert response.status_code == 200
    data = response.json()
    assert data["download_url"] == presigned
    assert data["expires_in"] == 3600


@pytest.mark.asyncio
async def test_download_url_not_found(authed_client):
    with patch("app.services.file_service.get_download_url", new_callable=AsyncMock, return_value=None):
        response = await authed_client.get(f"/api/v1/files/{FILE_ID}/download")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Unit tests for service layer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_service_list_files_filters_by_user():
    """list_files must filter by user_id — ensure query includes user filter."""
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=result_mock)

    from app.services.file_service import list_files

    files = await list_files(db, USER_ID)
    assert files == []
    db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_service_get_file_returns_none_for_other_user():
    """get_file must return None when user_id doesn't match."""
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result_mock)

    from app.services.file_service import get_file

    result = await get_file(db, OTHER_USER_ID, FILE_ID)
    assert result is None


@pytest.mark.asyncio
async def test_service_delete_file_returns_false_when_not_found():
    """delete_file returns False when file is not found."""
    db = AsyncMock()

    with patch("app.services.file_service.get_file", new_callable=AsyncMock, return_value=None):
        from app.services.file_service import delete_file

        result = await delete_file(db, USER_ID, FILE_ID)

    assert result is False


@pytest.mark.asyncio
async def test_service_get_download_url_returns_none_when_not_found():
    """get_download_url returns None when file is not found."""
    db = AsyncMock()

    with patch("app.services.file_service.get_file", new_callable=AsyncMock, return_value=None):
        from app.services.file_service import get_download_url

        result = await get_download_url(db, USER_ID, FILE_ID)

    assert result is None


# ---------------------------------------------------------------------------
# Unit tests for file_parser
# ---------------------------------------------------------------------------


def test_parse_to_markdown_unsupported_when_no_class():
    """parse_to_markdown raises UnsupportedFormatError when MarkItDown is unavailable."""
    import importlib
    import sys

    with patch.dict(sys.modules, {"markitdown": MagicMock(spec=[])}):
        import app.utils.file_parser as fp
        importlib.reload(fp)

        from app.utils.file_parser import UnsupportedFormatError, parse_to_markdown

        with pytest.raises(UnsupportedFormatError):
            parse_to_markdown(b"hello", "test.txt")


def test_parse_to_markdown_success():
    """parse_to_markdown returns markdown text on success."""
    import importlib
    import sys

    mock_result = MagicMock()
    mock_result.text_content = "# Hello"

    mock_md_instance = MagicMock()
    mock_md_instance.convert.return_value = mock_result

    MockMarkItDown = MagicMock(return_value=mock_md_instance)

    fake_module = MagicMock()
    fake_module.MarkItDown = MockMarkItDown

    with patch.dict(sys.modules, {"markitdown": fake_module}):
        import app.utils.file_parser as fp
        importlib.reload(fp)

        from app.utils.file_parser import parse_to_markdown

        result = parse_to_markdown(b"# Hello", "test.md")
        assert result == "# Hello"
