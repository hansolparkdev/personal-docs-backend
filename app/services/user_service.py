import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User


async def upsert_user(
    db: AsyncSession,
    auth_id: str,
    username: str,
    email: str,
    name: str | None = None,
) -> User:
    """auth_id 기준 upsert, last_login_at 갱신"""
    now = datetime.now(timezone.utc)
    stmt = (
        insert(User)
        .values(
            id=uuid.uuid4(),
            auth_id=auth_id,
            username=username,
            email=email,
            name=name,
            created_at=now,
            updated_at=now,
            last_login_at=now,
        )
        .on_conflict_do_update(
            index_elements=["auth_id"],
            set_={
                "username": username,
                "email": email,
                "name": name,
                "updated_at": now,
                "last_login_at": now,
            },
        )
        .returning(User)
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.scalar_one()


async def get_user_by_auth_id(db: AsyncSession, auth_id: str) -> User | None:
    result = await db.execute(select(User).where(User.auth_id == auth_id))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
