import logging

from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.core.config import settings
from app.services.keycloak_service import get_jwks, invalidate_jwks_cache

logger = logging.getLogger(__name__)


async def verify_token(token: str) -> dict:
    """JWKS 기반 JWT 서명·만료 검증. 실패 시 캐시 무효화 후 1회 재시도."""
    for attempt in range(2):
        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            if not kid:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token header")

            keys = await get_jwks()
            public_key = keys.get(kid)
            if not public_key:
                if attempt == 0:
                    invalidate_jwks_cache()
                    continue
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown token key")

            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                options={"verify_aud": False},
            )
            # azp(authorized party)로 클라이언트 검증
            if payload.get("azp") != settings.keycloak_client_id:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid client")
            return payload
        except HTTPException:
            raise
        except JWTError as exc:
            logger.debug("JWT verification failed (attempt %d): %s", attempt + 1, exc)
            if attempt == 0:
                invalidate_jwks_cache()
                continue
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
