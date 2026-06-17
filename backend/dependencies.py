"""FastAPI dependencies for authentication."""

from __future__ import annotations

from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from backend.config import get_settings

security = HTTPBearer(auto_error=False)

# Algorithms accepted for asymmetric (JWKS-verified) Supabase tokens.
_ASYMMETRIC_ALGS = ["ES256", "RS256"]


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient:
    """Cached client for the project's JWKS (public signing keys).

    Supabase serves the current ECC/RSA public key here; the client caches keys
    so we don't refetch on every request.
    """
    base = get_settings().supabase_url.rstrip("/")
    return PyJWKClient(f"{base}/auth/v1/.well-known/jwks.json", cache_keys=True)


async def get_current_user(
    cred: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Validate a Supabase JWT and return user info.

    Supports both signing schemes Supabase uses: asymmetric keys (ES256/RS256,
    verified against the project's published JWKS — the current default) and the
    legacy HS256 shared secret. Returns {'id' (sub), 'email'}; raises 401 for
    missing, invalid, or expired tokens.
    """
    if cred is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer authentication required",
        )
    settings = get_settings()
    token = cred.credentials
    try:
        alg = jwt.get_unverified_header(token).get("alg", "HS256")
        if alg == "HS256":
            # Legacy shared-secret tokens.
            payload = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                audience="authenticated",
                algorithms=["HS256"],
                options={"require": ["exp", "sub"]},
            )
        else:
            # Asymmetric tokens — verify with the public key from the JWKS.
            signing_key = _jwks_client().get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                audience="authenticated",
                algorithms=_ASYMMETRIC_ALGS,
                options={"require": ["exp", "sub"]},
            )
        return {"id": payload["sub"], "email": payload.get("email")}
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
