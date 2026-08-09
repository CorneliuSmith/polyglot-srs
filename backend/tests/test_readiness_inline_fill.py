"""GET /api/review/readiness — the wait screen's promise must not depend on
a background loop.

The kick() that follows demand recording is an in-process asyncio event. In
the deployed topology (several workers/replicas) the process that serves the
readiness request is routinely NOT the process whose sweep timer fires next,
so the event wakes nothing that matters: the owner watched "0 of 3" for
minutes while the fill landed "eventually" — at some other process's
quarter-hour sweep. The fix is that the request path fills the start batch
ITSELF (fill_start_batch), and these tests pin that wiring: a not-ready
readiness check must schedule the inline fill, in the serving process,
every time the cooldown allows.
"""
from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.services import auto_translate

TEST_SECRET = "test-jwt-secret-for-unit-tests-32bytes"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"


class FakeSettings:
    supabase_jwt_secret = TEST_SECRET
    supabase_url = "https://fake.supabase.co"
    supabase_anon_key = "fake-anon-key"
    supabase_service_role_key = "fake-service-role-key"
    database_url = "postgresql://fake/db"
    environment = "test"
    cors_origins = []


def _auth_headers() -> dict:
    token = pyjwt.encode(
        {"sub": TEST_USER_ID, "email": "t@example.com", "aud": "authenticated",
         "exp": int(time.time()) + 3600},
        TEST_SECRET, algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def client():
    with patch("backend.main.init_pool", new=AsyncMock()), \
         patch("backend.main.close_pool", new=AsyncMock()), \
         patch("backend.main.get_settings", return_value=FakeSettings()), \
         patch("backend.dependencies.get_settings", return_value=FakeSettings()):
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


def _not_ready():
    lane = {"total": 6, "ready": 0, "pct": 0.0, "cards": 3, "cards_ready": 0,
            "start_cards": 3, "ready_enough": False}
    return {"locale": "es", "threshold": 0.6,
            "learn": dict(lane), "review": dict(lane), "pairs": []}


def _ready():
    lane = {"total": 6, "ready": 6, "pct": 1.0, "cards": 3, "cards_ready": 3,
            "start_cards": 3, "ready_enough": True}
    return {"locale": "es", "threshold": 0.6,
            "learn": dict(lane), "review": dict(lane), "pairs": []}


def _rls(conn):
    m = MagicMock()
    m.return_value.__aenter__ = AsyncMock(return_value=conn)
    m.return_value.__aexit__ = AsyncMock(return_value=False)
    return patch("backend.routers.review.rls_connection", m)


def test_a_not_ready_wait_fills_its_own_start_batch(client):
    """The load-bearing wiring: not ready → the SERVING process schedules
    the inline fill with the batch the readiness gate is scoring."""
    conn = AsyncMock()
    filled = MagicMock(side_effect=lambda *a: asyncio.sleep(0))
    with _rls(conn), \
        patch("backend.routers.review.session_readiness",
              new=AsyncMock(return_value=_not_ready())), \
        patch("backend.routers.review.pretranslate_upcoming", new=AsyncMock()), \
        patch("backend.routers.review.start_batch_ids",
              new=AsyncMock(return_value=(["v1", "v2"], ["g1"]))), \
        patch("backend.routers.review.kick"), \
        patch("backend.routers.review.fill_start_batch", filled):
        resp = client.get(
            "/api/review/readiness?language_id=lang-1", headers=_auth_headers())

    assert resp.status_code == 200
    filled.assert_called_once_with(TEST_USER_ID, "lang-1", ["v1", "v2"], ["g1"])


def test_a_ready_session_spends_nothing(client):
    conn = AsyncMock()
    filled = MagicMock()
    with _rls(conn), \
        patch("backend.routers.review.session_readiness",
              new=AsyncMock(return_value=_ready())), \
        patch("backend.routers.review.pretranslate_upcoming", new=AsyncMock()) as pre, \
        patch("backend.routers.review.fill_start_batch", filled):
        resp = client.get(
            "/api/review/readiness?language_id=lang-1", headers=_auth_headers())

    assert resp.status_code == 200
    filled.assert_not_called()
    pre.assert_not_awaited()


@pytest.mark.asyncio
async def test_the_inline_fill_cooldown_stops_refresh_stampedes():
    """fill_start_batch runs model calls on the web worker; a learner
    hammering refresh must cost ONE round trip per cooldown window."""
    calls = []

    async def fake_available():
        return True

    with patch.object(auto_translate, "translations_available",
                      side_effect=lambda: (calls.append(1), True)[1]):
        auto_translate._INLINE_FILLS.clear()
        await auto_translate.fill_start_batch("u1", "l1", [], [])
        await auto_translate.fill_start_batch("u1", "l1", [], [])
        await auto_translate.fill_start_batch("u1", "l1", [], [])
    # Only the first call got past the cooldown to the provider check.
    assert len(calls) == 1
    auto_translate._INLINE_FILLS.clear()


@pytest.mark.asyncio
async def test_the_inline_fill_carries_the_sentence_layer():
    """A card that opens with a translated gloss/explanation over English
    "in context" lines reads as another failure — the fill must cover the
    start batch's example sentences and drill lines, not only the fields
    the readiness gate counts (the Thai/Spanish screenshot)."""
    auto_translate._INLINE_FILLS.clear()
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value="es")
    conn.fetchrow = AsyncMock(return_value={
        "language_id": "l1", "language_code": "th",
        "language_name": "Thai", "locale": "es", "locale_name": "Spanish"})
    conn.fetch = AsyncMock(return_value=[{"id": "d1"}])  # the points' drills

    ctx = MagicMock()
    ctx.return_value.__aenter__ = AsyncMock(return_value=conn)
    ctx.return_value.__aexit__ = AsyncMock(return_value=False)

    ex_rows = [{"id": "e1", "vocabulary_id": "v1", "language_id": "l1",
                "sentence": "s", "translation": "t"}]
    dr_rows = [{"id": "d1", "sentence": "s", "translation": "t", "hint": "h"}]
    tex = AsyncMock(return_value=1)
    tdr = AsyncMock(return_value=1)
    with patch("backend.repositories.pool.privileged_connection", ctx), \
         patch.object(auto_translate, "translations_available",
                      return_value=True), \
         patch.object(auto_translate, "pending_words",
                      new=AsyncMock(return_value=[])), \
         patch.object(auto_translate, "pending_explanations",
                      new=AsyncMock(return_value=[])), \
         patch.object(auto_translate, "pending_examples",
                      new=AsyncMock(return_value=ex_rows)), \
         patch.object(auto_translate, "pending_drills",
                      new=AsyncMock(return_value=dr_rows)), \
         patch.object(auto_translate, "_translate_examples", tex), \
         patch.object(auto_translate, "_translate_drills", tdr), \
         patch.object(auto_translate, "_settle", new=AsyncMock()) as settle:
        await auto_translate.fill_start_batch("u3", "l1", ["v1"], ["g1"])

    tex.assert_awaited_once()
    tdr.assert_awaited_once()
    settled_kinds = [c.args[1] for c in settle.await_args_list]
    assert "example" in settled_kinds and "drill" in settled_kinds
    auto_translate._INLINE_FILLS.clear()


@pytest.mark.asyncio
async def test_the_inline_fill_never_raises():
    """It is create_task'd from a request handler; an exception must die
    here, logged, not as an unhandled task error."""
    auto_translate._INLINE_FILLS.clear()
    with patch.object(auto_translate, "translations_available",
                      return_value=True), \
         patch("backend.repositories.pool.privileged_connection",
               side_effect=RuntimeError("db down")):
        await auto_translate.fill_start_batch("u2", "l2", ["v"], [])
    auto_translate._INLINE_FILLS.clear()
