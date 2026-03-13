"""JWT validation unit tests — no DB or Supabase required."""

from __future__ import annotations

import time
from unittest.mock import patch

import jwt as pyjwt
import pytest
from fastapi import HTTPException

from backend.dependencies import get_current_user

TEST_SECRET = "test-jwt-secret-for-unit-tests"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
TEST_EMAIL = "test@example.com"


class FakeSettings:
    supabase_jwt_secret = TEST_SECRET


class FakeCred:
    def __init__(self, token: str):
        self.credentials = token


def _make_token(payload: dict, secret: str = TEST_SECRET) -> str:
    return pyjwt.encode(payload, secret, algorithm="HS256")


def _valid_payload() -> dict:
    return {
        "sub": TEST_USER_ID,
        "email": TEST_EMAIL,
        "aud": "authenticated",
        "exp": int(time.time()) + 3600,
    }


@pytest.fixture()
def _mock_settings():
    with patch("backend.dependencies.get_settings", return_value=FakeSettings()):
        yield


@pytest.mark.asyncio
@pytest.mark.usefixtures("_mock_settings")
async def test_valid_jwt_returns_user():
    token = _make_token(_valid_payload())
    result = await get_current_user(FakeCred(token))
    assert result == {"id": TEST_USER_ID, "email": TEST_EMAIL}


@pytest.mark.asyncio
@pytest.mark.usefixtures("_mock_settings")
async def test_expired_jwt_returns_401():
    payload = _valid_payload()
    payload["exp"] = int(time.time()) - 60
    token = _make_token(payload)
    with pytest.raises(HTTPException) as exc:
        await get_current_user(FakeCred(token))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
@pytest.mark.usefixtures("_mock_settings")
async def test_missing_auth_header_returns_401():
    with pytest.raises(HTTPException) as exc:
        await get_current_user(None)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
@pytest.mark.usefixtures("_mock_settings")
async def test_invalid_jwt_returns_401():
    with pytest.raises(HTTPException) as exc:
        await get_current_user(FakeCred("not-a-valid-jwt"))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
@pytest.mark.usefixtures("_mock_settings")
async def test_wrong_audience_returns_401():
    payload = _valid_payload()
    payload["aud"] = "wrong-audience"
    token = _make_token(payload)
    with pytest.raises(HTTPException) as exc:
        await get_current_user(FakeCred(token))
    assert exc.value.status_code == 401
