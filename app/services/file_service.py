from __future__ import annotations

import io
import logging
import uuid
from datetime import timedelta

from minio import Minio
from minio.error import S3Error
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.file import File, IndexStatus
from app.db.models.file_chunk import FileChunk

logger = logging.getLogger(__name__)


def get_minio_client() -> Minio:
    client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )
    if not client.bucket_exists(settings.minio_bucket):
        client.make_bucket(settings.minio_bucket)
    return client


async def upload_file(
    db: AsyncSession,
    user_id: str,
    filename: str,
    content_type: str,
    size_bytes: int,
    content: bytes,
) -> File:
    """Upload a file to MinIO and create a DB record."""
    file_id = uuid.uuid4()
    minio_path = f"{user_id}/{file_id}/{filename}"

    client = get_minio_client()
    client.put_object(
        settings.minio_bucket,
        minio_path,
        io.BytesIO(content),
        length=size_bytes,
        content_type=content_type,
    )

    db_file = File(
        id=file_id,
        user_id=user_id,
        filename=filename,
        content_type=content_type,
        size_bytes=size_bytes,
        minio_path=minio_path,
        index_status=IndexStatus.pending,
    )
    db.add(db_file)
    await db.commit()
    await db.refresh(db_file)
    return db_file


async def index_file(db: AsyncSession, file_id: uuid.UUID) -> None:
    """Parse and embed file content as chunks (BackgroundTask)."""
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_openai import OpenAIEmbeddings

    from app.utils.file_parser import UnsupportedFormatError, parse_to_markdown

    result = await db.execute(select(File).where(File.id == file_id))
    db_file = result.scalar_one_or_none()
    if db_file is None:
        logger.warning("index_file: file %s not found", file_id)
        return

    db_file.index_status = IndexStatus.indexing
    await db.commit()

    try:
        client = get_minio_client()
        response = client.get_object(settings.minio_bucket, db_file.minio_path)
        raw_bytes = response.read()
        response.close()
        response.release_conn()
    except Exception as exc:
        logger.error("index_file: MinIO read failed for %s: %s", file_id, exc)
        db_file.index_status = IndexStatus.failed
        await db.commit()
        return

    try:
        markdown_text = parse_to_markdown(raw_bytes, db_file.filename)
    except UnsupportedFormatError:
        db_file.index_status = IndexStatus.unsupported
        await db.commit()
        return
    except Exception as exc:
        logger.error("index_file: parse failed for %s: %s", file_id, exc)
        db_file.index_status = IndexStatus.failed
        await db.commit()
        return

    try:
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = splitter.split_text(markdown_text)

        embeddings_model = OpenAIEmbeddings(
            model=settings.embedding_model,
            openai_api_key=settings.openai_api_key,
        )
        vectors = await embeddings_model.aembed_documents(chunks)

        for idx, (chunk_text, vector) in enumerate(zip(chunks, vectors)):
            chunk = FileChunk(
                file_id=file_id,
                user_id=db_file.user_id,
                chunk_index=idx,
                content=chunk_text,
                embedding=vector,
            )
            db.add(chunk)

        db_file.index_status = IndexStatus.indexed
        await db.commit()
        logger.info("index_file: indexed %d chunks for file %s", len(chunks), file_id)
    except Exception as exc:
        logger.error("index_file: embedding/save failed for %s: %s", file_id, exc)
        db_file.index_status = IndexStatus.failed
        await db.commit()


async def list_files(db: AsyncSession, user_id: str) -> list[File]:
    """Return all non-deleted files belonging to user_id."""
    result = await db.execute(
        select(File).where(File.user_id == user_id, File.deleted_at.is_(None))
    )
    return list(result.scalars().all())


async def get_file(db: AsyncSession, user_id: str, file_id: uuid.UUID) -> File | None:
    """Return a single file if it belongs to user_id and is not deleted."""
    result = await db.execute(
        select(File).where(
            File.id == file_id,
            File.user_id == user_id,
            File.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def delete_file(db: AsyncSession, user_id: str, file_id: uuid.UUID) -> bool:
    """Delete file from MinIO first, then remove DB record.

    Returns True if deleted, False if not found.
    Raises S3Error if MinIO deletion fails (DB is NOT modified).
    """
    db_file = await get_file(db, user_id, file_id)
    if db_file is None:
        return False

    client = get_minio_client()
    try:
        client.remove_object(settings.minio_bucket, db_file.minio_path)
    except S3Error as exc:
        logger.error("delete_file: MinIO delete failed for %s: %s", file_id, exc)
        raise

    await db.delete(db_file)
    await db.commit()
    return True


async def get_download_url(db: AsyncSession, user_id: str, file_id: uuid.UUID) -> str | None:
    """Return a presigned download URL for the file if it belongs to user_id."""
    db_file = await get_file(db, user_id, file_id)
    if db_file is None:
        return None

    client = get_minio_client()
    url = client.presigned_get_object(
        settings.minio_bucket,
        db_file.minio_path,
        expires=timedelta(hours=1),
    )
    return url


async def get_indexed_chunks(db: AsyncSession, user_id: str) -> list[FileChunk]:
    """Return all embedded chunks belonging to user_id (RAG internal interface)."""
    result = await db.execute(
        select(FileChunk).where(FileChunk.user_id == user_id)
    )
    return list(result.scalars().all())
