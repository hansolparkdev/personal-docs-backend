import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from jose import jwt as jose_jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.user import User
from app.schemas.auth import (
    RefreshRequest,
    RegisterRequest,
    TokenRequest,
    TokenResponse,
    UserResponse,
)
from app.services import keycloak_service as kc
from app.services.user_service import upsert_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """회원가입: Keycloak에 유저 생성 후 DB users upsert"""
    try:
        token = await kc.get_service_account_token()
        await kc.create_keycloak_user(
            token=token,
            username=body.username,
            email=body.email,
            password=body.password,
            name=body.name,
        )
    except kc.ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except kc.KeycloakUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    # Keycloak에서 발급된 sub를 얻기 위해 password grant로 로그인
    try:
        token_data = await kc.password_grant(body.username, body.password)
    except kc.UnauthorizedError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except kc.KeycloakUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    raw_payload = jose_jwt.get_unverified_claims(token_data["access_token"])
    auth_id: str = raw_payload["sub"]
    email_val: str = raw_payload.get("email", body.email)
    username_val: str = raw_payload.get("preferred_username", body.username)

    user = await upsert_user(db, auth_id=auth_id, username=username_val, email=email_val, name=body.name)
    return UserResponse(
        user_id=user.id,
        username=user.username,
        email=user.email,
        name=user.name,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: TokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """로그인: Resource Owner Password Credentials grant"""
    try:
        token_data = await kc.password_grant(body.username, body.password)
    except kc.UnauthorizedError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except kc.KeycloakUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    raw_payload = jose_jwt.get_unverified_claims(token_data["access_token"])
    auth_id: str = raw_payload["sub"]
    email_val: str = raw_payload.get("email", "")
    username_val: str = raw_payload.get("preferred_username", body.username)
    name_val: str | None = raw_payload.get("name")

    await upsert_user(db, auth_id=auth_id, username=username_val, email=email_val, name=name_val)

    return TokenResponse(
        access_token=token_data["access_token"],
        refresh_token=token_data["refresh_token"],
        token_type=token_data.get("token_type", "Bearer"),
        expires_in=token_data.get("expires_in", 300),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest):
    """토큰 갱신: refresh_token으로 새 access_token 발급"""
    try:
        token_data = await kc.refresh_grant(body.refresh_token)
    except kc.UnauthorizedError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except kc.KeycloakUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    return TokenResponse(
        access_token=token_data["access_token"],
        refresh_token=token_data["refresh_token"],
        token_type=token_data.get("token_type", "Bearer"),
        expires_in=token_data.get("expires_in", 300),
    )


@router.get("/callback", response_model=TokenResponse)
async def sso_callback(
    code: str = Query(..., description="Authorization code from Keycloak"),
    redirect_uri: str = Query(..., description="Redirect URI used in authorization request"),
    db: AsyncSession = Depends(get_db),
):
    """SSO 콜백: authorization code를 token으로 교환"""
    try:
        token_data = await kc.exchange_code(code=code, redirect_uri=redirect_uri)
    except kc.InvalidCodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except kc.KeycloakUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    raw_payload = jose_jwt.get_unverified_claims(token_data["access_token"])
    auth_id: str = raw_payload["sub"]
    email_val: str = raw_payload.get("email", "")
    username_val: str = raw_payload.get("preferred_username", auth_id)
    name_val: str | None = raw_payload.get("name")

    await upsert_user(db, auth_id=auth_id, username=username_val, email=email_val, name=name_val)

    return TokenResponse(
        access_token=token_data["access_token"],
        refresh_token=token_data["refresh_token"],
        token_type=token_data.get("token_type", "Bearer"),
        expires_in=token_data.get("expires_in", 300),
    )


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    """현재 인증된 사용자 정보 반환"""
    return UserResponse(
        user_id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        name=current_user.name,
        created_at=current_user.created_at,
        last_login_at=current_user.last_login_at,
    )
