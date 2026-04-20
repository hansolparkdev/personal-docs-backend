from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, model_validator

from app.db.models.file import IndexStatus


class FileUploadResponse(BaseModel):
    file_id: UUID
    filename: str
    index_status: IndexStatus
    created_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def _map_id_to_file_id(cls, data):
        if hasattr(data, "__dict__") or hasattr(data, "id"):
            # ORM object: map .id -> file_id
            try:
                raw_id = getattr(data, "id", None)
                if raw_id is not None and not isinstance(getattr(data, "file_id", None), (str, UUID)):
                    object.__setattr__(data, "file_id", raw_id) if hasattr(data, "__dict__") else None
                    # For ORM objects, return a dict representation
                    return {
                        "file_id": raw_id,
                        "filename": data.filename,
                        "index_status": data.index_status,
                        "created_at": data.created_at,
                    }
            except AttributeError:
                pass
        return data


class FileListItem(BaseModel):
    file_id: UUID
    filename: str
    content_type: str
    size_bytes: int
    index_status: IndexStatus
    created_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def _map_id_to_file_id(cls, data):
        if hasattr(data, "id") and not isinstance(data, dict):
            try:
                raw_id = getattr(data, "id", None)
                if raw_id is not None:
                    return {
                        "file_id": raw_id,
                        "filename": data.filename,
                        "content_type": data.content_type,
                        "size_bytes": data.size_bytes,
                        "index_status": data.index_status,
                        "created_at": data.created_at,
                    }
            except AttributeError:
                pass
        return data


class FileDetailResponse(BaseModel):
    file_id: UUID
    filename: str
    content_type: str
    size_bytes: int
    index_status: IndexStatus
    created_at: datetime
    minio_path: str

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def _map_id_to_file_id(cls, data):
        if hasattr(data, "id") and not isinstance(data, dict):
            try:
                raw_id = getattr(data, "id", None)
                if raw_id is not None:
                    return {
                        "file_id": raw_id,
                        "filename": data.filename,
                        "content_type": data.content_type,
                        "size_bytes": data.size_bytes,
                        "index_status": data.index_status,
                        "created_at": data.created_at,
                        "minio_path": data.minio_path,
                    }
            except AttributeError:
                pass
        return data


class FileDownloadResponse(BaseModel):
    download_url: str
    expires_in: int = 3600
