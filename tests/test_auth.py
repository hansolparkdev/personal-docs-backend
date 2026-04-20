"""Tests for auth endpoints (app/api/v1/auth.py)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.user import User
from app.main import app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

AUTH_ID = "keycloak-sub-abc123"
USERNAME = "testuser"
EMAIL = "testuser@example.com"
PASSWORD = "securepassword123"
NAME = "Test User"

ACCESS_TOKEN = "fake.access.token"
REFRESH_TOKEN = "fake.refresh.token"


def _make_user(
    auth_id: str = AUTH_ID,
    username: str = USERNAME,
    email: str = EMAIL,
    name: str | None = NAME,
) -> User:
    user = User(
        id=uuid.uuid4(),
        auth_id=auth_id,
        username=username,
        email=email,
        name=name,
    )
    user.created_at = datetime.now(timezone.utc)
    user.last_login_at = datetime.now(timezone.utc)
    return user


def _fake_token_data() -> dict:
    return {
        "access_token": ACCESS_TOKEN,
        "refresh_token": REFRESH_TOKEN,
        "token_type": "Bearer",
        "expires_in": 300,
    }


def _fake_jwt_claims(auth_id: str = AUTH_ID) -> dict:
    return {
        "sub": auth_id,
        "preferred_username": USERNAME,
        "email": EMAIL,
        "name": NAME,
        "azp": "backend",
    }


def _fake_db():
    async def _override():
        yield AsyncMock()
    return _override


def _fake_current_user(user: User | None = None):
    resolved = user or _make_user()

    async def _override():
        return resolved
    return _override


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def client_with_db():
    """DB가 mock된 클라이언트"""
    app.dependency_overrides[get_db] = _fake_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def authed_client():
    """인증된 유저가 주입된 클라이언트"""
    user = _make_user()
    app.dependency_overrides[get_current_user] = _fake_current_user(user)
    app.dependency_overrides[get_db] = _fake_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c, user
    app.dependency_overrides.clear()


@pytest.fixture
async def unauthed_client():
    app.dependency_overrides.clear()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# 1. 회원가입 정상 → 201
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_success(client_with_db):
    user = _make_user()
    token_data = _fake_token_data()
    claims = _fake_jwt_claims()

    with (
        patch("app.api.v1.auth.kc.get_service_account_token", new_callable=AsyncMock, return_value="admin-token"),
        patch("app.api.v1.auth.kc.create_keycloak_user", new_callable=AsyncMock, return_value=None),
        patch("app.api.v1.auth.kc.password_grant", new_callable=AsyncMock, return_value=token_data),
        patch("app.api.v1.auth.jose_jwt.get_unverified_claims", return_value=claims),  # noqa: E501
        patch("app.api.v1.auth.upsert_user", new_callable=AsyncMock, return_value=user),
    ):
        response = await client_with_db.post(
            "/api/v1/auth/register",
            json={"username": USERNAME, "email": EMAIL, "password": PASSWORD, "name": NAME},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["username"] == USERNAME
    assert data["email"] == EMAIL


# ---------------------------------------------------------------------------
# 2. username 중복 → 409
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_conflict(client_with_db):
    from app.services.keycloak_service import ConflictError

    with (
        patch("app.api.v1.auth.kc.get_service_account_token", new_callable=AsyncMock, return_value="admin-token"),
        patch("app.api.v1.auth.kc.create_keycloak_user", new_callable=AsyncMock, side_effect=ConflictError("Username or email already exists")),
    ):
        response = await client_with_db.post(
            "/api/v1/auth/register",
            json={"username": USERNAME, "email": EMAIL, "password": PASSWORD},
        )

    assert response.status_code == 409


# ---------------------------------------------------------------------------
# 3. password 8자 미만 → 422
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_short_password(client_with_db):
    response = await client_with_db.post(
        "/api/v1/auth/register",
        json={"username": USERNAME, "email": EMAIL, "password": "short"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 4. Keycloak 장애 → 502
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_keycloak_unavailable(client_with_db):
    from app.services.keycloak_service import KeycloakUnavailableError

    with (
        patch("app.api.v1.auth.kc.get_service_account_token", new_callable=AsyncMock, side_effect=KeycloakUnavailableError("Auth server unavailable")),
    ):
        response = await client_with_db.post(
            "/api/v1/auth/register",
            json={"username": USERNAME, "email": EMAIL, "password": PASSWORD},
        )

    assert response.status_code == 502


# ---------------------------------------------------------------------------
# 5. 로그인 정상 → 200 + 토큰
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_success(client_with_db):
    token_data = _fake_token_data()
    claims = _fake_jwt_claims()
    user = _make_user()

    with (
        patch("app.api.v1.auth.kc.password_grant", new_callable=AsyncMock, return_value=token_data),
        patch("app.api.v1.auth.jose_jwt.get_unverified_claims", return_value=claims),  # noqa: E501
        patch("app.api.v1.auth.upsert_user", new_callable=AsyncMock, return_value=user),
    ):
        response = await client_with_db.post(
            "/api/v1/auth/login",
            json={"username": USERNAME, "password": PASSWORD},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == ACCESS_TOKEN
    assert data["refresh_token"] == REFRESH_TOKEN
    assert data["token_type"] == "Bearer"


# ---------------------------------------------------------------------------
# 6. 잘못된 비밀번호 → 401
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_invalid_credentials(client_with_db):
    from app.services.keycloak_service import UnauthorizedError

    with patch("app.api.v1.auth.kc.password_grant", new_callable=AsyncMock, side_effect=UnauthorizedError("Invalid credentials")):
        response = await client_with_db.post(
            "/api/v1/auth/login",
            json={"username": USERNAME, "password": "wrongpass"},
        )

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# 7. 토큰 갱신 → 200
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_success(client):
    token_data = _fake_token_data()

    with patch("app.api.v1.auth.kc.refresh_grant", new_callable=AsyncMock, return_value=token_data):
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": REFRESH_TOKEN},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == ACCESS_TOKEN


# ---------------------------------------------------------------------------
# 8. 만료된 refresh_token → 401
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_expired_token(client):
    from app.services.keycloak_service import UnauthorizedError

    with patch("app.api.v1.auth.kc.refresh_grant", new_callable=AsyncMock, side_effect=UnauthorizedError("Invalid or expired refresh token")):
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "expired.refresh.token"},
        )

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# 9. SSO 콜백 정상 → 200
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sso_callback_success(client_with_db):
    token_data = _fake_token_data()
    claims = _fake_jwt_claims()
    user = _make_user()

    with (
        patch("app.api.v1.auth.kc.exchange_code", new_callable=AsyncMock, return_value=token_data),
        patch("app.api.v1.auth.jose_jwt.get_unverified_claims", return_value=claims),  # noqa: E501
        patch("app.api.v1.auth.upsert_user", new_callable=AsyncMock, return_value=user),
    ):
        response = await client_with_db.get(
            "/api/v1/auth/callback",
            params={"code": "valid-code", "redirect_uri": "http://localhost:3000/callback"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == ACCESS_TOKEN


# ---------------------------------------------------------------------------
# 10. 잘못된 code → 400
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sso_callback_invalid_code(client_with_db):
    from app.services.keycloak_service import InvalidCodeError

    with patch("app.api.v1.auth.kc.exchange_code", new_callable=AsyncMock, side_effect=InvalidCodeError("Invalid or expired authorization code")):
        response = await client_with_db.get(
            "/api/v1/auth/callback",
            params={"code": "bad-code", "redirect_uri": "http://localhost:3000/callback"},
        )

    assert response.status_code == 400


# ---------------------------------------------------------------------------
# 11. /me 정상 → 200 + 사용자 정보
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_me_success(authed_client):
    c, user = authed_client
    response = await c.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == user.username
    assert data["email"] == user.email


# ---------------------------------------------------------------------------
# 12. /me 토큰 없음 → 401
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_me_no_token(unauthed_client):
    response = await unauthed_client.get("/api/v1/auth/me")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# 13. /me 만료 토큰 → 401
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_me_expired_token(client):
    from fastapi import HTTPException

    with patch("app.core.dependencies.verify_token", new_callable=AsyncMock, side_effect=HTTPException(status_code=401, detail="Invalid token")):
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer expired.token.here"},
        )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Unit tests for keycloak_service
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_jwks_uses_cache():
    """JWKS 캐시 TTL 내 재요청 시 HTTP 호출 없음"""
    import time

    from app.services import keycloak_service as kc_svc

    kc_svc._jwks_cache["keys"] = {"kid1": {"kid": "kid1", "kty": "RSA"}}
    kc_svc._jwks_cache["fetched_at"] = time.time()

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        result = await kc_svc.get_jwks()

    mock_get.assert_not_called()
    assert "kid1" in result


@pytest.mark.asyncio
async def test_get_jwks_fetches_when_expired():
    """JWKS 캐시 만료 시 HTTP 호출"""
    from app.services import keycloak_service as kc_svc

    kc_svc._jwks_cache["keys"] = {}
    kc_svc._jwks_cache["fetched_at"] = 0

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"keys": [{"kid": "kid2", "kty": "RSA"}]}
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        result = await kc_svc.get_jwks()

    assert "kid2" in result


@pytest.mark.asyncio
async def test_password_grant_raises_unauthorized_on_401():
    """password_grant: 401 응답 → UnauthorizedError"""
    from app.services import keycloak_service as kc_svc

    mock_resp = MagicMock()
    mock_resp.status_code = 401

    with (
        patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp),
        pytest.raises(kc_svc.UnauthorizedError),
    ):
        await kc_svc.password_grant("user", "wrong")


@pytest.mark.asyncio
async def test_password_grant_raises_unavailable_on_500():
    """password_grant: 5xx 응답 → KeycloakUnavailableError"""
    from app.services import keycloak_service as kc_svc

    mock_resp = MagicMock()
    mock_resp.status_code = 503

    with (
        patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp),
        pytest.raises(kc_svc.KeycloakUnavailableError),
    ):
        await kc_svc.password_grant("user", "pass")


# ---------------------------------------------------------------------------
# Unit tests for user_service
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_user_by_auth_id_returns_none_when_not_found():
    """auth_id 없으면 None 반환"""
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result_mock)

    from app.services.user_service import get_user_by_auth_id

    result = await get_user_by_auth_id(db, "nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_get_user_by_id_returns_user():
    """user_id로 유저 조회"""
    user = _make_user()
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = user
    db.execute = AsyncMock(return_value=result_mock)

    from app.services.user_service import get_user_by_id

    result = await get_user_by_id(db, user.id)
    assert result is user
