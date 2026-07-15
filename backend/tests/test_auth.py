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


# ── single-plan enforcement on the profile upsert (WP16c) ───────────────────

from contextlib import asynccontextmanager  # noqa: E402
from unittest.mock import AsyncMock  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from backend.main import create_app  # noqa: E402

LICENSED_LANG = "11111111-1111-1111-1111-111111111111"
OTHER_LANG = "22222222-2222-2222-2222-222222222222"


class FakeAppSettings:
    supabase_jwt_secret = TEST_SECRET
    supabase_url = "https://fake.supabase.co"
    supabase_anon_key = "k"
    supabase_service_role_key = "k"
    database_url = "postgresql://fake/db"
    environment = "test"
    cors_origins = []


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {_make_token(_valid_payload())}"}


def _client_with_plan(plan_row):
    """A TestClient whose RLS connection reports *plan_row* for the profile."""
    conn = AsyncMock()
    conn.fetchrow.return_value = plan_row

    @asynccontextmanager
    async def fake_rls(user_id):
        yield conn

    return (
        patch("backend.main.init_pool", new=AsyncMock()),
        patch("backend.main.close_pool", new=AsyncMock()),
        patch("backend.main.get_settings", return_value=FakeAppSettings()),
        patch("backend.dependencies.get_settings", return_value=FakeAppSettings()),
        patch("backend.routers.auth.rls_connection", fake_rls),
    )


def test_single_plan_cannot_switch_language():
    """A Single-language account switching active_language away from its
    licensed language gets a 403 telling it to upgrade."""
    p1, p2, p3, p4, p5 = _client_with_plan(
        {"plan_scope": "single", "plan_language_id": LICENSED_LANG}
    )
    with p1, p2, p3, p4, p5:
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as client:
            resp = client.post(
                "/api/auth/profile",
                json={"active_language_id": OTHER_LANG},
                headers=_auth_headers(),
            )
    assert resp.status_code == 403
    assert "plan covers one language" in resp.json()["detail"]


def test_single_plan_keeps_its_own_language():
    """Re-selecting the licensed language is always allowed."""
    plan_row = {"plan_scope": "single", "plan_language_id": LICENSED_LANG}
    p1, p2, p3, p4, p5 = _client_with_plan(plan_row)
    with p1, p2, p3, p4, p5:
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as client:
            resp = client.post(
                "/api/auth/profile",
                json={"active_language_id": LICENSED_LANG},
                headers=_auth_headers(),
            )
    # Not rejected by the plan gate (the mocked upsert returns the same
    # plan row for the RETURNING clause).
    assert resp.status_code == 200
