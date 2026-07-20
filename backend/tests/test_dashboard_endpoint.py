"""Unit tests for GET /api/dashboard/{language_id}.

All tests mock the repository layer — no DATABASE_URL required.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from backend.main import create_app

TEST_SECRET = "test-jwt-secret-for-unit-tests-32bytes"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
TEST_EMAIL = "test@example.com"
TEST_LANGUAGE_ID = "22222222-2222-2222-2222-222222222222"


class FakeSettings:
    supabase_jwt_secret = TEST_SECRET
    supabase_url = "https://fake.supabase.co"
    supabase_anon_key = "fake-anon-key"
    supabase_service_role_key = "fake-service-role-key"
    database_url = "postgresql://fake/db"
    environment = "test"
    cors_origins = []


def _make_token() -> str:
    payload = {
        "sub": TEST_USER_ID,
        "email": TEST_EMAIL,
        "aud": "authenticated",
        "exp": int(time.time()) + 3600,
    }
    return pyjwt.encode(payload, TEST_SECRET, algorithm="HS256")


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {_make_token()}"}


FAKE_STATS = {
    "due_count": 12,
    "due_grammar": 8,
    "due_vocab": 4,
    "streak_days": 5,
    "cefr_progress": {
        "A1": {"learned": 50, "total": 100},
        "A2": {"learned": 20, "total": 100},
        "B1": {"learned": 5, "total": 100},
        "B2": {"learned": 0, "total": 100},
        "C1": {"learned": 0, "total": 50},
        "C2": {"learned": 0, "total": 25},
    },
}


@pytest.fixture()
def client():
    with patch("backend.main.init_pool", new=AsyncMock()), \
         patch("backend.main.close_pool", new=AsyncMock()), \
         patch("backend.main.get_settings", return_value=FakeSettings()), \
         patch("backend.dependencies.get_settings", return_value=FakeSettings()):
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


# ---------------------------------------------------------------------------
# GET /api/dashboard/{language_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dashboard_returns_correct_shape(client):
    """Happy path: dashboard returns due_count, streak_days, cefr_progress."""
    with patch("backend.routers.dashboard.rls_connection") as mock_rls, patch(
        "backend.routers.dashboard.get_dashboard_stats",
        new=AsyncMock(return_value=FAKE_STATS),
    ):
        mock_rls.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_rls.return_value.__aexit__ = AsyncMock(return_value=False)

        resp = client.get(
            f"/api/dashboard/{TEST_LANGUAGE_ID}",
            headers=_auth_headers(),
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["due_count"] == 12
    # Review-tile expansion contract: type counts sum to the total.
    assert data["due_grammar"] == 8
    assert data["due_vocab"] == 4
    assert data["streak_days"] == 5
    assert "cefr_progress" in data
    assert set(data["cefr_progress"].keys()) == {"A1", "A2", "B1", "B2", "C1", "C2"}


@pytest.mark.asyncio
async def test_dashboard_cefr_progress_values(client):
    """Each CEFR level has learned and total keys."""
    with patch("backend.routers.dashboard.rls_connection") as mock_rls, patch(
        "backend.routers.dashboard.get_dashboard_stats",
        new=AsyncMock(return_value=FAKE_STATS),
    ):
        mock_rls.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_rls.return_value.__aexit__ = AsyncMock(return_value=False)

        resp = client.get(
            f"/api/dashboard/{TEST_LANGUAGE_ID}",
            headers=_auth_headers(),
        )

    data = resp.json()
    for lvl, entry in data["cefr_progress"].items():
        assert "learned" in entry, f"{lvl} missing 'learned'"
        assert "total" in entry, f"{lvl} missing 'total'"


@pytest.mark.asyncio
async def test_dashboard_requires_auth(client):
    """Dashboard returns 401/403 when no auth header provided."""
    resp = client.get(f"/api/dashboard/{TEST_LANGUAGE_ID}")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_dashboard_zero_streak_when_no_reviews(client):
    """streak_days can be 0 for a new user with no reviews."""
    stats_no_streak = {**FAKE_STATS, "streak_days": 0}
    with patch("backend.routers.dashboard.rls_connection") as mock_rls, patch(
        "backend.routers.dashboard.get_dashboard_stats",
        new=AsyncMock(return_value=stats_no_streak),
    ):
        mock_rls.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_rls.return_value.__aexit__ = AsyncMock(return_value=False)

        resp = client.get(
            f"/api/dashboard/{TEST_LANGUAGE_ID}",
            headers=_auth_headers(),
        )

    assert resp.status_code == 200
    assert resp.json()["streak_days"] == 0


# ---------------------------------------------------------------------------
# Unit tests for _compute_streak (pure logic, no HTTP)
# ---------------------------------------------------------------------------


def test_safe_tz_accepts_real_zones_and_rejects_garbage():
    from backend.repositories.dashboard import _safe_tz

    assert _safe_tz("America/New_York") == "America/New_York"
    assert _safe_tz("Europe/Madrid") == "Europe/Madrid"
    # Garbage from a hostile/broken client degrades to the old behavior,
    # never to a SQL error.
    assert _safe_tz("Not/AZone") == "UTC"
    assert _safe_tz("") == "UTC"
    assert _safe_tz(None) == "UTC"
    assert _safe_tz("'; DROP TABLE readings; --") == "UTC"


def test_compute_streak_uses_the_supplied_today():
    from datetime import date

    from backend.repositories.dashboard import _compute_streak

    # 23:30 in New York is already "tomorrow" in UTC: with the learner's
    # local date passed in, yesterday+today still count as a 2-day streak.
    local_today = date(2026, 7, 20)
    dates = {date(2026, 7, 19), date(2026, 7, 20)}
    assert _compute_streak(dates, today=local_today) == 2
    # A "today" one day later sees the same dates as ending yesterday.
    assert _compute_streak(dates, today=date(2026, 7, 21)) == 2
    assert _compute_streak(dates, today=date(2026, 7, 23)) == 0


@pytest.mark.asyncio
async def test_dashboard_passes_browser_timezone(client):
    with patch("backend.routers.dashboard.rls_connection") as mock_rls, patch(
        "backend.routers.dashboard.get_dashboard_stats",
        new=AsyncMock(return_value=FAKE_STATS),
    ) as mock_stats:
        mock_rls.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_rls.return_value.__aexit__ = AsyncMock(return_value=False)
        resp = client.get(
            f"/api/dashboard/{TEST_LANGUAGE_ID}",
            params={"tz": "America/New_York"},
            headers=_auth_headers(),
        )
    assert resp.status_code == 200
    assert mock_stats.await_args.kwargs["tz"] == "America/New_York"


def test_compute_streak_empty():
    from backend.repositories.dashboard import _compute_streak

    assert _compute_streak(set()) == 0


def test_compute_streak_today_only():
    from backend.repositories.dashboard import _compute_streak

    today = datetime.now(UTC).date()
    assert _compute_streak({today}) == 1


def test_compute_streak_consecutive_days():
    from backend.repositories.dashboard import _compute_streak

    today = datetime.now(UTC).date()
    dates = {today - timedelta(days=i) for i in range(5)}
    assert _compute_streak(dates) == 5


def test_compute_streak_gap_breaks_streak():
    from backend.repositories.dashboard import _compute_streak

    today = datetime.now(UTC).date()
    # today and 2 days ago — gap at yesterday breaks streak
    dates = {today, today - timedelta(days=2)}
    assert _compute_streak(dates) == 1


def test_compute_streak_yesterday_only():
    from backend.repositories.dashboard import _compute_streak

    yesterday = datetime.now(UTC).date() - timedelta(days=1)
    # Grace period: if no review today, streak counts from yesterday
    assert _compute_streak({yesterday}) == 1
