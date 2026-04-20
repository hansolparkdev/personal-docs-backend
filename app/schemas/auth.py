from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8)
    name: Optional[str] = None


class TokenRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class UserResponse(BaseModel):
    user_id: UUID
    username: str
    email: str
    name: Optional[str]
    created_at: datetime
    last_login_at: Optional[datetime]
    model_config = {"from_attributes": True}
