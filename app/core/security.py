from typing import Annotated

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings

bearer_scheme = HTTPBearer()

_keycloak_public_keys: dict = {}


async def _get_keycloak_public_key(kid: str) -> dict:
    if kid not in _keycloak_public_keys:
        url = f"{settings.keycloak_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/certs"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            resp.raise_for_status()
            for key in resp.json()["keys"]:
                _keycloak_public_keys[key["kid"]] = key
    return _keycloak_public_keys.get(kid)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> dict:
    token = credentials.credentials
    try:
        header = jwt.get_unverified_header(token)
        public_key = await _get_keycloak_public_key(header["kid"])
        if not public_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token key")
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=settings.keycloak_client_id,
        )
        return payload
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
