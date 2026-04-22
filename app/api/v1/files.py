from __future__ import annotations

import logging
import os
import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.file_service as svc
from app.core.config import settings
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.schemas.file import (
    FileDetailResponse,
    FileDownloadResponse,
    FileListItem,
    FileUploadResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["files"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Upload a file. Supported extensions and 50MB limit enforced."""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: '{ext}'. Allowed: {sorted(settings.allowed_extensions)}",
        )

    content = await file.read()
    size_bytes = len(content)

    if size_bytes > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size {size_bytes} exceeds the limit of {settings.max_upload_size_bytes} bytes",
        )

    user_id: str = current_user.auth_id

    db_file = await svc.upload_file(
        db=db,
        user_id=user_id,
        filename=file.filename or "untitled",
        content_type=file.content_type,
        size_bytes=size_bytes,
        content=content,
    )

    background_tasks.add_task(svc.index_file, db, db_file.id)

    return FileUploadResponse.model_validate(db_file)


@router.get("", response_model=list[FileListItem])
async def list_files(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return all non-deleted files belonging to the authenticated user."""
    user_id: str = current_user.auth_id
    files = await svc.list_files(db=db, user_id=user_id)
    return [FileListItem.model_validate(f) for f in files]


@router.get("/{file_id}", response_model=FileDetailResponse)
async def get_file(
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return detail of a single file. Returns 404 if not owned by caller."""
    user_id: str = current_user.auth_id
    db_file = await svc.get_file(db=db, user_id=user_id, file_id=file_id)
    if db_file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return FileDetailResponse.model_validate(db_file)


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Delete a file from MinIO and DB. Returns 404 if not owned by caller."""
    user_id: str = current_user.auth_id
    deleted = await svc.delete_file(db=db, user_id=user_id, file_id=file_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")


@router.get("/{file_id}/download", response_model=FileDownloadResponse)
async def download_file(
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return a presigned download URL (1h expiry)."""
    user_id: str = current_user.auth_id
    url = await svc.get_download_url(db=db, user_id=user_id, file_id=file_id)
    if url is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return FileDownloadResponse(download_url=url)
