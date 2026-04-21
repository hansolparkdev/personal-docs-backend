from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

import app.services.chat_service as svc
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.user import User
from app.schemas.chat import (
    ChatSessionDetailResponse,
    ChatSessionResponse,
    SendMessageRequest,
)
from app.services.rag_service import stream_rag_response

router = APIRouter(prefix="/chats", tags=["chat"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ChatSessionResponse)
async def create_session(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await svc.create_session(db, current_user.auth_id)
    return session


@router.get("", response_model=list[ChatSessionResponse])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.list_sessions(db, current_user.auth_id)


@router.get("/{session_id}", response_model=ChatSessionDetailResponse)
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await svc.get_session_with_messages(db, session_id, current_user.auth_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ok = await svc.delete_session(db, session_id, current_user.auth_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.post("/{session_id}/messages")
async def send_message(
    session_id: uuid.UUID,
    body: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await svc.get_session(db, session_id, current_user.auth_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return StreamingResponse(
        stream_rag_response(db, session_id, current_user.auth_id, body.content),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
