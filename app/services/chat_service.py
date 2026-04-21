from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.chat import ChatMessage, ChatSession

logger = logging.getLogger(__name__)


async def create_session(db: AsyncSession, user_id: str) -> ChatSession:
    """Create a new chat session for user_id."""
    session = ChatSession(user_id=user_id)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def list_sessions(db: AsyncSession, user_id: str, limit: int = 50) -> list[ChatSession]:
    """Return sessions belonging to user_id ordered by updated_at desc."""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user_id)
        .order_by(desc(ChatSession.updated_at))
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_session(
    db: AsyncSession, session_id: uuid.UUID, user_id: str
) -> ChatSession | None:
    """Return a session if it belongs to user_id."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def get_session_with_messages(
    db: AsyncSession, session_id: uuid.UUID, user_id: str
) -> ChatSession | None:
    """Return a session with its messages if it belongs to user_id."""
    result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def delete_session(
    db: AsyncSession, session_id: uuid.UUID, user_id: str
) -> bool:
    """Delete a session if it belongs to user_id. Returns True if deleted."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        return False
    await db.delete(session)
    await db.commit()
    return True


async def set_session_title(
    db: AsyncSession, session_id: uuid.UUID, title: str
) -> None:
    """Set the title of a session (first message prefix)."""
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if session is not None:
        session.title = title
        await db.commit()


async def save_user_message(
    db: AsyncSession, session_id: uuid.UUID, user_id: str, content: str
) -> ChatMessage:
    """Persist a user message and return it."""
    msg = ChatMessage(
        session_id=session_id,
        user_id=user_id,
        role="user",
        content=content,
        sources=None,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def save_assistant_message(
    db: AsyncSession,
    session_id: uuid.UUID,
    user_id: str,
    content: str,
    sources: list[dict[str, Any]] | None,
) -> ChatMessage:
    """Persist an assistant message with sources and return it."""
    msg = ChatMessage(
        session_id=session_id,
        user_id=user_id,
        role="assistant",
        content=content,
        sources=sources,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def get_recent_messages(
    db: AsyncSession, session_id: uuid.UUID, limit: int = 20
) -> list[ChatMessage]:
    """Return the most recent messages for a session, ordered ascending."""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(desc(ChatMessage.created_at))
        .limit(limit)
    )
    messages = list(result.scalars().all())
    # Return in chronological order
    return list(reversed(messages))
