import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IndexStatus(str, enum.Enum):
    pending = "pending"
    indexing = "indexing"
    indexed = "indexed"
    failed = "failed"
    unsupported = "unsupported"


class File(Base):
    __tablename__ = "files"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    minio_path: Mapped[str] = mapped_column(String, nullable=False)
    index_status: Mapped[IndexStatus] = mapped_column(SAEnum(IndexStatus), default=IndexStatus.pending)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(  # noqa: UP007
        DateTime(timezone=True), nullable=True
    )
