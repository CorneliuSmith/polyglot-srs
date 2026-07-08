"""Unit tests for new review endpoints: validate-answer and learn.

All tests mock the DB layer and NLP layer — no DATABASE_URL required.
Follows patterns from test_auth.py: override FastAPI dependencies, mock DB calls.
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from backend.main import create_app

TEST_SECRET = "test-jwt-secret-for-unit-tests-32bytes"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
TEST_EMAIL = "test@example.com"
TEST_LANGUAGE_ID = "11111111-1111-1111-1111-111111111111"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client():
    """Create a test client with mocked settings and no DB pool."""
    with patch("backend.main.init_pool", new=AsyncMock()), \
         patch("backend.main.close_pool", new=AsyncMock()), \
         patch("backend.main.get_settings", return_value=FakeSettings()), \
         patch("backend.dependencies.get_settings", return_value=FakeSettings()):
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


# ---------------------------------------------------------------------------
# POST /api/review/validate-answer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_answer_returns_result_and_feedback(client):
    """Happy path: known language returns answer_result + feedback."""
    from backend.services.nlp.base import AnswerResult as AR

    with patch(
        "backend.routers.review.validate_answer_async",
        new=AsyncMock(return_value=(AR.CORRECT, "Perfect!")),
    ):
        resp = client.post(
            "/api/review/validate-answer",
            json={
                "language_code": "en",
                "user_input": "run",
                "correct_answer": "run",
            },
            headers=_auth_headers(),
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["answer_result"] == "correct"
    assert data["feedback"] == "Perfect!"


@pytest.mark.asyncio
async def test_validate_answer_wrong_form(client):
    """WRONG_FORM result is serialised as 'wrong_form' (snake_case)."""
    from backend.services.nlp.base import AnswerResult as AR

    with patch(
        "backend.routers.review.validate_answer_async",
        new=AsyncMock(return_value=(AR.WRONG_FORM, "Close — check the verb form.")),
    ):
        resp = client.post(
            "/api/review/validate-answer",
            json={
                "language_code": "ru",
                "user_input": "бежать",
                "correct_answer": "бегу",
                "card_context": {"pos": "verb"},
            },
            headers=_auth_headers(),
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["answer_result"] == "wrong_form"
    assert "verb form" in data["feedback"]


@pytest.mark.asyncio
async def test_validate_answer_unknown_language_returns_422(client):
    """Unknown language code raises ValueError which must become HTTP 422."""
    with patch(
        "backend.routers.review.validate_answer_async",
        side_effect=ValueError("No NLP backend registered for 'xx'"),
    ):
        resp = client.post(
            "/api/review/validate-answer",
            json={
                "language_code": "xx",
                "user_input": "hello",
                "correct_answer": "hello",
            },
            headers=_auth_headers(),
        )

    assert resp.status_code == 422
    assert "xx" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_validate_answer_requires_auth(client):
    """validate-answer returns 403 when no auth header provided."""
    resp = client.post(
        "/api/review/validate-answer",
        json={
            "language_code": "en",
            "user_input": "run",
            "correct_answer": "run",
        },
    )
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /api/review/learn
# ---------------------------------------------------------------------------


def _make_fake_conn(batch_size: int = 5, profile_exists: bool = True):
    """Build an async mock connection that returns profile and learn results."""
    conn = AsyncMock()
    if profile_exists:
        profile_row = MagicMock()
        profile_row.__getitem__ = MagicMock(
            side_effect=lambda key: batch_size if key == "batch_size" else None
        )
        conn.fetchrow.return_value = profile_row
    else:
        conn.fetchrow.return_value = None
    return conn


@pytest.mark.asyncio
async def test_learn_adds_batch_of_cards(client):
    """Happy path: learn returns added count and card ID list."""
    fake_result = {"added": 3, "items": ["id-1", "id-2", "id-3"]}

    with patch("backend.routers.review.rls_connection") as mock_rls, patch(
        "backend.routers.review.add_learn_batch", new=AsyncMock(return_value=fake_result)
    ), patch(
        "backend.routers.review.get_card_details_bulk",
        new=AsyncMock(return_value={
            i: {"card_type": "vocabulary", "title": "casa"}
            for i in ["id-1", "id-2", "id-3"]
        }),
    ):
        conn = _make_fake_conn(batch_size=3)
        mock_rls.return_value.__aenter__ = AsyncMock(return_value=conn)
        mock_rls.return_value.__aexit__ = AsyncMock(return_value=False)

        resp = client.post(
            "/api/review/learn",
            json={"language_id": TEST_LANGUAGE_ID},
            headers=_auth_headers(),
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["added"] == 3
    assert data["items"] == ["id-1", "id-2", "id-3"]
    # The teach-before-quiz payload: one lesson per new card
    assert [lesson["card_id"] for lesson in data["lessons"]] == fake_result["items"]
    assert data["lessons"][0]["title"] == "casa"


@pytest.mark.asyncio
async def test_learn_reads_batch_size_from_profile(client):
    """Learn reads batch_size from user_profiles and passes it to add_learn_batch."""
    fake_result = {"added": 10, "items": [f"id-{i}" for i in range(10)]}

    captured_batch_size = []

    async def capture_batch(*args, **kwargs):
        captured_batch_size.append(args[3])  # batch_size is 4th positional arg
        return fake_result

    with patch("backend.routers.review.rls_connection") as mock_rls, patch(
        "backend.routers.review.add_learn_batch", new=capture_batch
    ), patch(
        "backend.routers.review.get_card_details_bulk",
        new=AsyncMock(return_value={}),
    ):
        conn = _make_fake_conn(batch_size=10)
        mock_rls.return_value.__aenter__ = AsyncMock(return_value=conn)
        mock_rls.return_value.__aexit__ = AsyncMock(return_value=False)

        resp = client.post(
            "/api/review/learn",
            json={"language_id": TEST_LANGUAGE_ID},
            headers=_auth_headers(),
        )

    assert resp.status_code == 200
    assert captured_batch_size == [10]


@pytest.mark.asyncio
async def test_learn_defaults_batch_size_to_5_when_no_profile(client):
    """If user has no profile row, batch_size defaults to 5."""
    fake_result = {"added": 5, "items": [f"id-{i}" for i in range(5)]}

    captured_batch_size = []

    async def capture_batch(*args, **kwargs):
        captured_batch_size.append(args[3])
        return fake_result

    with patch("backend.routers.review.rls_connection") as mock_rls, patch(
        "backend.routers.review.add_learn_batch", new=capture_batch
    ), patch(
        "backend.routers.review.get_card_details_bulk",
        new=AsyncMock(return_value={}),
    ):
        conn = _make_fake_conn(profile_exists=False)
        mock_rls.return_value.__aenter__ = AsyncMock(return_value=conn)
        mock_rls.return_value.__aexit__ = AsyncMock(return_value=False)

        resp = client.post(
            "/api/review/learn",
            json={"language_id": TEST_LANGUAGE_ID},
            headers=_auth_headers(),
        )

    assert resp.status_code == 200
    assert captured_batch_size == [5]


@pytest.mark.asyncio
async def test_learn_requires_auth(client):
    """learn returns 403 when no auth header provided."""
    resp = client.post(
        "/api/review/learn",
        json={"language_id": TEST_LANGUAGE_ID},
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_learn_level_scopes_batch_and_subscribes(client):
    """A deck-scoped learn passes the level through and queues the deck."""
    fake_result = {"added": 2, "items": ["id-1", "id-2"]}
    captured = {}

    async def capture_batch(conn, user_id, language_id, batch_size, level=None):
        captured["level"] = level
        return fake_result

    with patch("backend.routers.review.rls_connection") as mock_rls, patch(
        "backend.routers.review.add_grammar_learn_batch", new=capture_batch
    ), patch(
        "backend.routers.review.get_card_details_bulk",
        new=AsyncMock(return_value={}),
    ):
        conn = _make_fake_conn(batch_size=5)
        mock_rls.return_value.__aenter__ = AsyncMock(return_value=conn)
        mock_rls.return_value.__aexit__ = AsyncMock(return_value=False)

        resp = client.post(
            "/api/review/learn",
            json={
                "language_id": TEST_LANGUAGE_ID,
                "card_type": "grammar",
                "level": "A1",
            },
            headers=_auth_headers(),
        )

    assert resp.status_code == 200
    assert captured["level"] == "A1"
    # The deliberate deck choice auto-subscribes (INSERT … ON CONFLICT)
    subscribe_calls = [
        c for c in conn.execute.await_args_list
        if "user_content_subscriptions" in str(c.args[0])
    ]
    assert len(subscribe_calls) == 1


@pytest.mark.asyncio
async def test_decks_returns_deck_rows(client):
    """GET /decks returns the per-level deck rows with progress."""
    fake_decks = [
        {
            "id": "deck-1",
            "list_type": "grammar",
            "level": "A1",
            "title": "A1 Grammar",
            "subscribed": True,
            "total": 10,
            "learned": 3,
        }
    ]
    with patch("backend.routers.review.rls_connection") as mock_rls, patch(
        "backend.routers.review.get_learn_decks",
        new=AsyncMock(return_value=fake_decks),
    ):
        conn = AsyncMock()
        mock_rls.return_value.__aenter__ = AsyncMock(return_value=conn)
        mock_rls.return_value.__aexit__ = AsyncMock(return_value=False)

        resp = client.get(
            "/api/review/decks",
            params={"language_id": TEST_LANGUAGE_ID},
            headers=_auth_headers(),
        )

    assert resp.status_code == 200
    assert resp.json()["decks"] == fake_decks


@pytest.mark.asyncio
async def test_decks_requires_auth(client):
    resp = client.get(
        "/api/review/decks", params={"language_id": TEST_LANGUAGE_ID}
    )
    assert resp.status_code in (401, 403)
