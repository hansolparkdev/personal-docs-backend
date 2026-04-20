import time

import httpx

from app.core.config import settings

KEYCLOAK_BASE = f"{settings.keycloak_url}/realms/{settings.keycloak_realm}"
ADMIN_BASE = f"{settings.keycloak_url}/admin/realms/{settings.keycloak_realm}"

# JWKS 인메모리 캐시 (TTL 600s)
_jwks_cache: dict = {"keys": {}, "fetched_at": 0}


async def get_service_account_token() -> str:
    """Client Credentials grant로 Admin API 토큰 발급"""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{KEYCLOAK_BASE}/protocol/openid-connect/token",
            data={
                "grant_type": "client_credentials",
                "client_id": settings.keycloak_client_id,
                "client_secret": settings.keycloak_client_secret,
            },
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


async def create_keycloak_user(
    token: str,
    username: str,
    email: str,
    password: str,
    name: str | None = None,
) -> None:
    """Keycloak Admin API로 유저 생성"""
    payload: dict = {
        "username": username,
        "email": email,
        "enabled": True,
        "credentials": [{"type": "password", "value": password, "temporary": False}],
    }
    if name:
        payload["firstName"] = name
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{ADMIN_BASE}/users",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code == 409:
            raise ConflictError("Username or email already exists")
        resp.raise_for_status()


async def password_grant(username: str, password: str) -> dict:
    """Resource Owner Password Credentials grant"""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{KEYCLOAK_BASE}/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": settings.keycloak_client_id,
                "client_secret": settings.keycloak_client_secret,
                "username": username,
                "password": password,
            },
        )
        if resp.status_code == 401:
            raise UnauthorizedError("Invalid credentials")
        if resp.status_code >= 500:
            raise KeycloakUnavailableError("Auth server unavailable")
        resp.raise_for_status()
        return resp.json()


async def refresh_grant(refresh_token: str) -> dict:
    """Refresh token grant"""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{KEYCLOAK_BASE}/protocol/openid-connect/token",
            data={
                "grant_type": "refresh_token",
                "client_id": settings.keycloak_client_id,
                "client_secret": settings.keycloak_client_secret,
                "refresh_token": refresh_token,
            },
        )
        if resp.status_code in (400, 401):
            raise UnauthorizedError("Invalid or expired refresh token")
        if resp.status_code >= 500:
            raise KeycloakUnavailableError("Auth server unavailable")
        resp.raise_for_status()
        return resp.json()


async def exchange_code(code: str, redirect_uri: str) -> dict:
    """Authorization Code grant"""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{KEYCLOAK_BASE}/protocol/openid-connect/token",
            data={
                "grant_type": "authorization_code",
                "client_id": settings.keycloak_client_id,
                "client_secret": settings.keycloak_client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )
        if resp.status_code in (400, 401):
            raise InvalidCodeError("Invalid or expired authorization code")
        if resp.status_code >= 500:
            raise KeycloakUnavailableError("Auth server unavailable")
        resp.raise_for_status()
        return resp.json()


async def get_jwks() -> dict:
    """JWKS fetch with TTL cache"""
    now = time.time()
    if now - _jwks_cache["fetched_at"] < settings.keycloak_jwks_cache_ttl and _jwks_cache["keys"]:
        return _jwks_cache["keys"]
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{KEYCLOAK_BASE}/protocol/openid-connect/certs")
        resp.raise_for_status()
        keys = {k["kid"]: k for k in resp.json()["keys"]}
        _jwks_cache["keys"] = keys
        _jwks_cache["fetched_at"] = now
        return keys


def invalidate_jwks_cache() -> None:
    """JWKS 캐시 무효화 (검증 실패 시 재시도용)"""
    _jwks_cache["keys"] = {}
    _jwks_cache["fetched_at"] = 0


class ConflictError(Exception):
    pass


class UnauthorizedError(Exception):
    pass


class KeycloakUnavailableError(Exception):
    pass


class InvalidCodeError(Exception):
    pass
