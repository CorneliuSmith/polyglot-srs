"""Tests for WP13(f) Quick-Cram and WP13(g) in-app search.

Router behavior with the repository mocked, plus the pure drill-picking
logic of get_cram_cards against a faked connection.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from backend.main import create_app

TEST_SECRET = "test-jwt-secret-for-unit-tests-32bytes"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
POINT_A = "22222222-2222-2222-2222-222222222222"
POINT_B = "33333333-3333-3333-3333-333333333333"
LANG = "11111111-1111-1111-1111-111111111111"


class FakeSettings:
    supabase_jwt_secret = TEST_SECRET
    supabase_url = "https://fake.supabase.co"
    supabase_anon_key = "k"
    supabase_service_role_key = "k"
    database_url = "postgresql://fake/db"
    environment = "test"
    cors_origins = []


def _auth_headers() -> dict:
    token = pyjwt.encode(
        {"sub": TEST_USER_ID, "aud": "authenticated", "exp": int(time.time()) + 3600},
        TEST_SECRET, algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


@asynccontextmanager
async def _fake_rls(user_id: str):
    yield AsyncMock()


@pytest.fixture()
def client():
    with patch("backend.main.init_pool", new=AsyncMock()), \
         patch("backend.main.close_pool", new=AsyncMock()), \
         patch("backend.main.get_settings", return_value=FakeSettings()), \
         patch("backend.dependencies.get_settings", return_value=FakeSettings()), \
         patch("backend.routers.review.rls_connection", _fake_rls), \
         patch("backend.routers.curriculum.rls_connection", _fake_rls):
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


# ---------------------------------------------------------------------------
# GET /api/review/cram (router gating)
# ---------------------------------------------------------------------------


class TestCramEndpoint:
    def test_requires_auth(self, client):
        assert client.get(
            "/api/review/cram", params={"point_ids": POINT_A}
        ).status_code == 401

    def test_returns_cards(self, client):
        cards = [{"id": f"cram-{POINT_A}-0", "sentence": "Ev{{answer}}yim."}]
        with patch(
            "backend.routers.review.get_cram_cards",
            new=AsyncMock(return_value=cards),
        ) as mock_cram:
            resp = client.get(
                "/api/review/cram",
                params={"point_ids": f"{POINT_A},{POINT_B}"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json() == cards
        assert mock_cram.await_args.args[1] == [POINT_A, POINT_B]

    def test_rejects_non_uuid_ids(self, client):
        resp = client.get(
            "/api/review/cram",
            params={"point_ids": "not-a-uuid"},
            headers=_auth_headers(),
        )
        assert resp.status_code == 422

    def test_rejects_too_many_points(self, client):
        ids = ",".join([POINT_A] * 13)
        resp = client.get(
            "/api/review/cram", params={"point_ids": ids}, headers=_auth_headers()
        )
        assert resp.status_code == 422

    def test_rejects_empty(self, client):
        resp = client.get(
            "/api/review/cram", params={"point_ids": " , "}, headers=_auth_headers()
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# get_cram_cards (drill picking, seeded rotation, DueCard shape)
# ---------------------------------------------------------------------------


def _point_row(point_id: str, n_drills: int, code: str = "tr") -> dict:
    return {
        "point_id": point_id,
        "title": "Locative case",
        "language_code": code,
        "sentences": [f"S{i} {{{{answer}}}}." for i in range(n_drills)],
        "answers": [f"a{i}" for i in range(n_drills)],
        "hints": [None] * n_drills,
        "translations": [f"t{i}" for i in range(n_drills)],
        "glosses": [None] * n_drills,
        "transliterations": [None] * n_drills,
    }


class TestGetCramCards:
    @pytest.mark.asyncio
    async def test_picks_capped_per_point_and_shapes_cards(self):
        from backend.repositories.cards import get_cram_cards

        conn = AsyncMock()
        conn.fetch = AsyncMock(
            return_value=[_point_row(POINT_A, 8), _point_row(POINT_B, 2)]
        )
        cards = await get_cram_cards(conn, [POINT_A, POINT_B])

        by_point: dict[str, int] = {}
        for c in cards:
            by_point[c["card_id"]] = by_point.get(c["card_id"], 0) + 1
        assert by_point[POINT_A] == 3  # capped at per_point
        assert by_point[POINT_B] == 2  # fewer drills than the cap -> all

        for c in cards:
            # Shaped like a DueCard, safe for the session UI...
            for key in ("sentence", "correct_answer", "language_code",
                        "repetitions", "streak", "lapses", "next_review"):
                assert key in c
            # ...but with a synthetic id /review/submit would never accept.
            assert c["id"].startswith("cram-")
            assert c["card_type"] == "grammar"

    @pytest.mark.asyncio
    async def test_same_day_same_picks(self):
        """Seeded rotation: a reload mid-cram keeps the same drill set."""
        from backend.repositories.cards import get_cram_cards

        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[_point_row(POINT_A, 10)])
        first = await get_cram_cards(conn, [POINT_A])
        second = await get_cram_cards(conn, [POINT_A])
        assert [c["id"] for c in first] == [c["id"] for c in second]

    @pytest.mark.asyncio
    async def test_points_without_drills_are_skipped(self):
        from backend.repositories.cards import get_cram_cards

        row = _point_row(POINT_A, 0)
        row["sentences"] = None
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[row])
        assert await get_cram_cards(conn, [POINT_A]) == []


# ---------------------------------------------------------------------------
# GET /api/curriculum/search
# ---------------------------------------------------------------------------


class TestSearchEndpoint:
    def test_requires_auth(self, client):
        assert client.get(
            "/api/curriculum/search", params={"language_id": LANG, "q": "ev"}
        ).status_code == 401

    def test_returns_grammar_and_vocab(self, client):
        results = {
            "grammar": [{
                "id": POINT_A, "title": "Locative case", "level": "A1",
                "function_note": "in/at/on", "learned": True,
            }],
            "vocabulary": [{
                "id": POINT_B, "word": "ev", "level": "A1",
                "part_of_speech": "noun", "definition": "house", "learned": False,
            }],
        }
        with patch(
            "backend.routers.curriculum.search_content",
            new=AsyncMock(return_value=results),
        ) as mock_search:
            resp = client.get(
                "/api/curriculum/search",
                params={"language_id": LANG, "q": "  ev "},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json() == results
        assert mock_search.await_args.args[3] == "ev"  # trimmed

    def test_blank_query_422(self, client):
        resp = client.get(
            "/api/curriculum/search",
            params={"language_id": LANG, "q": "   "},
            headers=_auth_headers(),
        )
        assert resp.status_code == 422

    def test_overlong_query_422(self, client):
        resp = client.get(
            "/api/curriculum/search",
            params={"language_id": LANG, "q": "x" * 101},
            headers=_auth_headers(),
        )
        assert resp.status_code == 422

    def test_search_not_swallowed_by_language_id_route(self, client):
        """Route-order guard: /search must not match /{language_id}."""
        with patch(
            "backend.routers.curriculum.search_content",
            new=AsyncMock(return_value={"grammar": [], "vocabulary": []}),
        ), patch(
            "backend.routers.curriculum.get_curriculum", new=AsyncMock(),
        ) as mock_curriculum:
            resp = client.get(
                "/api/curriculum/search",
                params={"language_id": LANG, "q": "ev"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        mock_curriculum.assert_not_awaited()


class TestLikeEscape:
    def test_wildcards_match_literally(self):
        from backend.repositories.curriculum import _like_escape

        assert _like_escape("100%") == "100\\%"
        assert _like_escape("a_b") == "a\\_b"
        assert _like_escape("back\\slash") == "back\\\\slash"
