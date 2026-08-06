"""GET /api/review/trivia — where the questions come from, and in what order.

The endpoint has three sources: the bank, the written baseline, and the
generator. The order matters more than it looks. Reaching for the model
first meant the game only existed where a provider key was configured, and
a bank that cannot be written at all (the migration not yet applied) meant
no game anywhere — which is the state the wait screen was reported stuck
in.
"""
from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.routers import review as review_router

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
        {
            "sub": TEST_USER_ID,
            "email": "test@example.com",
            "aud": "authenticated",
            "exp": int(time.time()) + 3600,
        },
        TEST_SECRET,
        algorithm="HS256",
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


@pytest.fixture(autouse=True)
def _forget_seeded_locales():
    """The seed guard is process-wide, so one test would otherwise decide
    what the next one sees."""
    review_router._SEEDED.clear()
    yield
    review_router._SEEDED.clear()


def _conn_returning(locale: str = "es"):
    conn = AsyncMock()
    conn.fetchval.return_value = locale
    return conn


def _patch_pools(conn):
    """Both connection helpers hand back the same fake."""
    rls = MagicMock()
    rls.return_value.__aenter__ = AsyncMock(return_value=conn)
    rls.return_value.__aexit__ = AsyncMock(return_value=False)
    priv = MagicMock()
    priv.return_value.__aenter__ = AsyncMock(return_value=conn)
    priv.return_value.__aexit__ = AsyncMock(return_value=False)
    return (
        patch("backend.routers.review.rls_connection", rls),
        patch("backend.routers.review.privileged_connection", priv),
    )


@pytest.mark.asyncio
async def test_empty_bank_is_seeded_from_the_baseline_before_any_model_call(client):
    """The written corpus is free and instant; the generator is neither."""
    conn = _conn_returning("es")
    seeded: list[dict] = []

    async def fake_store(_conn, _locale, items, source="ai"):
        seeded.extend(items)
        return len(items)

    # Empty on the first read, stocked on the second — what seeding does.
    reads = [[], [{"id": "t1", "question": "q", "options": ["a", "b"],
                   "answer_index": 0, "fact": "f"}]]
    rls, priv = _patch_pools(conn)
    with rls, priv, \
        patch("backend.routers.review.unseen_trivia",
              new=AsyncMock(side_effect=lambda *a, **k: reads.pop(0))), \
        patch("backend.routers.review.count_unseen", new=AsyncMock(return_value=40)), \
        patch("backend.routers.review.store_trivia", new=AsyncMock(side_effect=fake_store)), \
        patch("backend.routers.review.translations_available", return_value=True), \
        patch("backend.routers.review.generate_trivia", new=AsyncMock()) as gen:
        resp = client.get("/api/review/trivia", headers=_auth_headers())

    assert resp.status_code == 200
    assert resp.json()["questions"][0]["id"] == "t1"
    # Written in Spanish, not English, and marked as the hand-written set.
    assert len(seeded) >= 15
    assert any("lengua" in it["question"].lower()
               or "lenguas" in it["question"].lower() for it in seeded)
    # count_unseen is above LOW_WATER here, so nothing is topping up behind
    # the request either: the model was not consulted at all.
    gen.assert_not_awaited()


@pytest.mark.asyncio
async def test_a_bank_that_cannot_be_written_still_yields_a_game(client):
    """The migration not being applied yet is the likeliest reason, and it
    must not be the difference between a game and a blank panel."""
    conn = _conn_returning("fr")
    rls, priv = _patch_pools(conn)
    with rls, priv, \
        patch("backend.routers.review.unseen_trivia", new=AsyncMock(return_value=[])), \
        patch("backend.routers.review.count_unseen", new=AsyncMock(return_value=0)), \
        patch("backend.routers.review.store_trivia", new=AsyncMock(return_value=0)), \
        patch("backend.routers.review.translations_available", return_value=False):
        resp = client.get(
            "/api/review/trivia", params={"limit": 5}, headers=_auth_headers()
        )

    body = resp.json()
    assert resp.status_code == 200
    assert body["locale"] == "fr"
    assert len(body["questions"]) == 5
    for q in body["questions"]:
        assert q["id"] and q["question"] and q["fact"]
        assert 0 <= q["answer_index"] < len(q["options"])


@pytest.mark.asyncio
async def test_a_locale_with_no_baseline_falls_through_to_the_generator(client):
    """German has no written corpus, so the model is the only source — the
    behaviour that existed before the baseline, still intact."""
    conn = _conn_returning("de")
    rls, priv = _patch_pools(conn)
    with rls, priv, \
        patch("backend.routers.review.unseen_trivia", new=AsyncMock(return_value=[])), \
        patch("backend.routers.review.count_unseen", new=AsyncMock(return_value=0)), \
        patch("backend.routers.review.existing_questions", new=AsyncMock(return_value=[])), \
        patch("backend.routers.review.store_trivia", new=AsyncMock(return_value=0)), \
        patch("backend.routers.review.translations_available", return_value=True), \
        patch("backend.routers.review.generate_trivia",
              new=AsyncMock(return_value=[])) as gen:
        resp = client.get("/api/review/trivia", headers=_auth_headers())

    assert resp.status_code == 200
    gen.assert_awaited()
    # Nothing written, nothing generated, nothing to fake: an empty list is
    # the honest answer, and the client falls back to plain progress.
    assert resp.json()["questions"] == []


@pytest.mark.asyncio
async def test_a_thin_bank_grows_behind_the_learner(client):
    """The baseline is a floor, not a ceiling — once a learner has worked
    below LOW_WATER the generator widens the corpus after the request is
    answered rather than making anyone wait for it.

    Asserted on the SCHEDULING rather than on generate_trivia having run:
    the top-up is a fire-and-forget task, so whether it has got as far as
    the model by the time the response comes back is a race. It failed in
    CI on one interpreter and passed on another.
    """
    conn = _conn_returning("ru")
    served = [{"id": "t1", "question": "q", "options": ["a", "b"],
               "answer_index": 0, "fact": "f"}]

    async def _noop() -> None:
        return None

    top_up = MagicMock(side_effect=lambda _locale: _noop())
    rls, priv = _patch_pools(conn)
    with rls, priv, \
        patch("backend.routers.review.unseen_trivia", new=AsyncMock(return_value=served)), \
        patch("backend.routers.review.count_unseen", new=AsyncMock(return_value=5)), \
        patch("backend.routers.review.translations_available", return_value=True), \
        patch("backend.routers.review._locale_has_pending_translations",
              new=AsyncMock(return_value=False)), \
        patch("backend.routers.review._top_up_trivia", top_up):
        resp = client.get("/api/review/trivia", headers=_auth_headers())

    assert resp.json()["questions"] == served
    top_up.assert_called_once_with("ru")


@pytest.mark.asyncio
async def test_the_baseline_is_only_laid_down_once_per_locale(client):
    conn = _conn_returning("pt")
    rls, priv = _patch_pools(conn)
    store = AsyncMock(return_value=0)
    with rls, priv, \
        patch("backend.routers.review.unseen_trivia", new=AsyncMock(return_value=[])), \
        patch("backend.routers.review.count_unseen", new=AsyncMock(return_value=0)), \
        patch("backend.routers.review.store_trivia", new=store), \
        patch("backend.routers.review.translations_available", return_value=False):
        client.get("/api/review/trivia", headers=_auth_headers())
        client.get("/api/review/trivia", headers=_auth_headers())

    assert store.await_count == 1


async def test_the_game_does_not_compete_with_the_fill_it_covers_for(client):
    """Entertainment yields to the session.

    /api/review/trivia is called at exactly the moment a learner is sitting
    on the wait screen watching for their own translations — and the game
    and the fill spend the same API key. A top-up here competes with the
    thing they are waiting on and can provoke the rate limit that stalls
    it, which is what "whenever the game shows up the translation feature
    fails" looked like from the outside.

    (It was guaranteed, too: the written baseline is 20 questions and
    LOW_WATER used to be 30, so a freshly seeded locale was permanently
    "running low" and every single request fired a generation.)
    """
    conn = _conn_returning("fr")
    served = [{"id": "t1", "question": "q", "options": ["a", "b"],
               "answer_index": 0, "fact": "f"}]

    async def _noop() -> None:
        return None

    top_up = MagicMock(side_effect=lambda _locale: _noop())
    rls, priv = _patch_pools(conn)
    with rls, priv, \
        patch("backend.routers.review.unseen_trivia", new=AsyncMock(return_value=served)), \
        patch("backend.routers.review.count_unseen", new=AsyncMock(return_value=5)), \
        patch("backend.routers.review.translations_available", return_value=True), \
        patch("backend.routers.review._locale_has_pending_translations",
              new=AsyncMock(return_value=True)), \
        patch("backend.routers.review._top_up_trivia", top_up):
        resp = client.get("/api/review/trivia", headers=_auth_headers())

    # The learner still gets their game — from the bank, for free.
    assert resp.status_code == 200
    assert resp.json()["questions"] == served
    top_up.assert_not_called()


def test_the_bank_is_considered_stocked_once_the_baseline_is_down():
    """LOW_WATER must sit BELOW the written baseline.

    Above it, a seeded locale can never be "stocked": every request sees a
    bank under the mark and schedules a generation, forever, for a bank
    that was already fine.
    """
    from backend.repositories.trivia import LOW_WATER
    from backend.services.trivia_corpus import seed_questions

    assert LOW_WATER < len(seed_questions("en"))
