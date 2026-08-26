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
from backend.repositories.cards import _form_key

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
# POST /api/review/gym/generate (WP41: learner-triggered on-demand generation)
# ---------------------------------------------------------------------------


def _gen_ctx(point_id: str, code: str = "tr") -> dict:
    return {
        "point_id": point_id,
        "title": "Locative case",
        "explanation": "Add -de/-da to a noun.",
        "language_id": LANG,
        "language_code": code,
        "language_name": "Turkish",
        "examples": ["Ev{{answer}}yim."],
    }


_GEN_DRILLS = [
    {"sentence": " Okul{{answer}}yim.", "answer": "dayim",
     "translation": "I am at school.", "hint": "school"},
    {"sentence": "Bahçe{{answer}}sin.", "answer": "desin",
     "translation": "You are in the garden.", "hint": "garden"},
]


@asynccontextmanager
async def _fake_privileged():
    yield AsyncMock()


def _patch_gym_gen(*, contexts=None, allowance=None, struggles=None,
                   placement_cells=None):
    """Patch the whole gym/generate collaborator chain to no-ops."""
    if contexts is None:
        contexts = [_gen_ctx(POINT_A)]
    if allowance is None:
        allowance = {"tier": "free", "unlimited": False, "limit": 20,
                     "used": 3, "remaining": 17, "resets_at": "2026-08-01T00:00:00"}

    async def _ctx(conn, pid):
        return next((c for c in contexts if c["point_id"] == pid), None)

    return (
        patch("backend.routers.review.generation_available", return_value=True),
        patch("backend.routers.review.get_generation_context", new=_ctx),
        patch("backend.routers.review.get_allowance",
              new=AsyncMock(return_value=allowance)),
        patch("backend.routers.review.generate_drills",
              new=AsyncMock(return_value=list(_GEN_DRILLS))),
        patch("backend.routers.review.add_drill", new=AsyncMock()),
        patch("backend.routers.review.log_tutor_usage", new=AsyncMock()),
        patch("backend.routers.review.privileged_connection", _fake_privileged),
        patch("backend.routers.review.resolve_model", return_value="claude-x"),
        patch("backend.routers.review.get_form_struggles",
              new=AsyncMock(return_value=struggles or {})),
        # Cold start: forms missed at placement, when the Gym has no history.
        patch("backend.routers.review.get_placement_form_misses",
              new=AsyncMock(return_value=placement_cells or {})),
    )


class TestGymGenerateEndpoint:
    def test_requires_auth(self, client):
        assert client.post(
            "/api/review/gym/generate", json={"point_ids": [POINT_A]}
        ).status_code == 401

    def test_generates_and_draws_one_message(self, client):
        # The chart path is pinned shut so this test measures what its name
        # says: one form topped up draws one message. Left unpatched it did
        # not measure that at all — WP45 charges a message per new word, so
        # the real answer is 3, and the only reason this ever read 1 was that
        # `make_chart` CRASHED. With TUTOR_DEV_MOCK unset (which is how CI
        # runs — no workflow sets it) it builds a live Anthropic client, the
        # call raises, and the router's `except: break` skips both charges.
        # So CI passed on an exception while a developer with dev-mock on saw
        # the honest 3 and a red test. An assertion satisfied by a crash is
        # not a passing assertion.
        p = _patch_gym_gen()
        charted = {_form_key("dayim"): "okul", _form_key("desin"): "bahçe"}
        with p[0], p[1], p[2], p[3], p[4] as mock_add, \
             p[5] as mock_log, p[6], p[7], p[8], p[9], \
             patch("backend.routers.review._chart_form_index",
                   new=AsyncMock(return_value=charted)), \
             patch("backend.routers.review._reset_chart_form_index"), \
             patch("backend.routers.review.generate_chart",
                   new=AsyncMock()) as mock_chart:
            resp = client.post(
                "/api/review/gym/generate",
                json={"point_ids": [POINT_A]},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["generated"] == 2          # both drills persisted
        assert body["charged"] == 1            # one form topped up -> one message
        assert body["remaining"] == 16         # 17 - 1 message drawn
        assert body["unlimited"] is False
        assert mock_add.await_count == 2
        # the added drills are tagged 'ai' and DON'T de-certify the form
        assert mock_add.await_args.kwargs["source"] == "ai"
        assert mock_add.await_args.kwargs["decertify"] is False
        # Never the live generator: with no key this test was passing because
        # the call threw, and with a key it would have SPENT one.
        mock_chart.assert_not_awaited()
        # one message per FORM (here a single form), not per drill
        mock_log.assert_awaited_once()
        assert mock_log.await_args.kwargs["kind"] == "gym_gen"

    def test_targets_the_learners_struggling_cell(self, client):
        # The 'forms' assessment tier: with evidenced misses on one cell,
        # generation aims every new drill at THAT form and tags it so.
        struggles = {POINT_A: [
            {"cell": "vosotros", "seen": 6, "misses": 3,
             "wrong_form": 2, "hint_used": 1},
        ]}
        p = _patch_gym_gen(struggles=struggles)
        with p[0], p[1], p[2], p[3] as mock_gen, p[4] as mock_add, \
             p[5], p[6], p[7], p[8], p[9]:
            resp = client.post(
                "/api/review/gym/generate",
                json={"point_ids": [POINT_A]},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert mock_gen.await_args.kwargs["cell"] == "vosotros"
        assert mock_add.await_args.kwargs["cell"] == "vosotros"

    def test_no_struggle_evidence_stays_cell_agnostic(self, client):
        # One slip is noise (misses < 2) — generation keeps varied forms.
        struggles = {POINT_A: [
            {"cell": "yo", "seen": 4, "misses": 1,
             "wrong_form": 1, "hint_used": 0},
        ]}
        p = _patch_gym_gen(struggles=struggles)
        with p[0], p[1], p[2], p[3] as mock_gen, p[4], p[5], p[6], p[7], p[8], p[9]:
            resp = client.post(
                "/api/review/gym/generate",
                json={"point_ids": [POINT_A]},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert mock_gen.await_args.kwargs["cell"] is None

    def test_503_when_generation_disabled(self, client):
        with patch("backend.routers.review.generation_available",
                   return_value=False):
            resp = client.post(
                "/api/review/gym/generate",
                json={"point_ids": [POINT_A]},
                headers=_auth_headers(),
            )
        assert resp.status_code == 503

    def test_402_when_allowance_exhausted(self, client):
        spent = {"tier": "free", "unlimited": False, "limit": 20,
                 "used": 20, "remaining": 0, "resets_at": "2026-08-01T00:00:00"}
        p = _patch_gym_gen(allowance=spent)
        with p[0], p[1], p[2], p[3], p[4] as mock_add, p[5], p[6], p[7], p[8], p[9]:
            resp = client.post(
                "/api/review/gym/generate",
                json={"point_ids": [POINT_A]},
                headers=_auth_headers(),
            )
        assert resp.status_code == 402
        assert resp.json()["detail"]["code"] == "allowance_exhausted"
        mock_add.assert_not_awaited()          # nothing spent when blocked

    def test_404_when_no_valid_points(self, client):
        p = _patch_gym_gen(contexts=[])        # get_generation_context finds none
        with p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8], p[9]:
            resp = client.post(
                "/api/review/gym/generate",
                json={"point_ids": [POINT_A]},
                headers=_auth_headers(),
            )
        assert resp.status_code == 404

    def test_charts_made_for_new_words_before_returning(self, client):
        # WP45: a fresh drill exercising a word no chart covers gets its chart
        # inside the SAME request (so the re-fetch delivers chart-complete
        # cards), charged one message per word from the same allowance.
        p = _patch_gym_gen()
        chart = {"lemma": "okul", "part_of_speech": "noun",
                 "usage_note": None, "charts": [{"title": "Cases",
                                                 "rows": [["loc", "dayim"]]}]}
        with p[0], p[1], p[2], p[3], p[4], p[5] as mock_log, p[6], p[7], p[8], p[9], \
             patch("backend.routers.review._chart_form_index",
                   new=AsyncMock(return_value={})), \
             patch("backend.routers.review._reset_chart_form_index"), \
             patch("backend.routers.review.generate_chart",
                   new=AsyncMock(return_value=chart)) as mock_chart, \
             patch("backend.routers.review.upsert_vocabulary_charts",
                   new=AsyncMock(return_value=("vid", "created"))) as mock_upsert:
            resp = client.post(
                "/api/review/gym/generate",
                json={"point_ids": [POINT_A]},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        body = resp.json()
        # Two drills with two distinct new answers -> two charts, each charged.
        assert body["generated"] == 2
        assert body["charts"] == 2
        assert body["charged"] == 3            # 1 form top-up + 2 charts
        assert body["remaining"] == 14         # 17 - 3
        assert mock_chart.await_count == 2
        assert mock_upsert.await_count == 2
        kinds = [c.kwargs["kind"] for c in mock_log.await_args_list]
        assert kinds == ["gym_gen", "gym_chart", "gym_chart"]

    def test_already_charted_answers_spend_nothing_extra(self, client):
        # Both answers resolve in the reverse form index -> no chart calls,
        # no extra charges.
        index = {_form_key("dayim"): "okul", _form_key("desin"): "bahçe"}
        p = _patch_gym_gen()
        with p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8], p[9], \
             patch("backend.routers.review._chart_form_index",
                   new=AsyncMock(return_value=index)), \
             patch("backend.routers.review._reset_chart_form_index"), \
             patch("backend.routers.review.generate_chart",
                   new=AsyncMock()) as mock_chart:
            resp = client.post(
                "/api/review/gym/generate",
                json={"point_ids": [POINT_A]},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["charts"] == 0
        assert body["charged"] == 1
        mock_chart.assert_not_awaited()

    def test_chart_spend_never_exceeds_the_allowance(self, client):
        # 2 messages left: the form top-up takes 1, so only ONE chart fits —
        # the second new word is left for a later run, never an overdraw.
        tight = {"tier": "free", "unlimited": False, "limit": 20,
                 "used": 18, "remaining": 2, "resets_at": "2026-08-01T00:00:00"}
        chart = {"lemma": "okul", "part_of_speech": "noun",
                 "usage_note": None, "charts": [{"title": "Cases",
                                                 "rows": [["loc", "dayim"]]}]}
        p = _patch_gym_gen(allowance=tight)
        with p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8], p[9], \
             patch("backend.routers.review._chart_form_index",
                   new=AsyncMock(return_value={})), \
             patch("backend.routers.review._reset_chart_form_index"), \
             patch("backend.routers.review.generate_chart",
                   new=AsyncMock(return_value=chart)) as mock_chart, \
             patch("backend.routers.review.upsert_vocabulary_charts",
                   new=AsyncMock(return_value=("vid", "created"))):
            resp = client.post(
                "/api/review/gym/generate",
                json={"point_ids": [POINT_A]},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        body = resp.json()
        assert mock_chart.await_count == 1
        assert body["charged"] == 2
        assert body["remaining"] == 0

    def test_rejected_chart_never_persists(self, client):
        # The containment checker said no -> nothing stored; the card simply
        # shows no chart (the Gym's normal bare state, not a broken one).
        p = _patch_gym_gen()
        with p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8], p[9], \
             patch("backend.routers.review._chart_form_index",
                   new=AsyncMock(return_value={})), \
             patch("backend.routers.review._reset_chart_form_index"), \
             patch("backend.routers.review.generate_chart",
                   new=AsyncMock(return_value=None)), \
             patch("backend.routers.review.upsert_vocabulary_charts",
                   new=AsyncMock()) as mock_upsert:
            resp = client.post(
                "/api/review/gym/generate",
                json={"point_ids": [POINT_A]},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json()["charts"] == 0
        mock_upsert.assert_not_awaited()

    def test_caps_points_per_call(self, client):
        ids = [POINT_A, POINT_B,
               "44444444-4444-4444-4444-444444444444",
               "55555555-5555-5555-5555-555555555555"]
        seen = []

        async def _ctx(conn, pid):
            seen.append(pid)
            return _gen_ctx(pid)

        p = _patch_gym_gen()
        with p[0], patch("backend.routers.review.get_generation_context", new=_ctx), \
             p[2], p[3], p[4], p[5], p[6], p[7], p[8], p[9]:
            resp = client.post(
                "/api/review/gym/generate",
                json={"point_ids": ids},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        # only the first GYM_GEN_MAX_POINTS forms are ever looked up
        from backend.routers.review import GYM_GEN_MAX_POINTS
        assert len(seen) == GYM_GEN_MAX_POINTS


# ---------------------------------------------------------------------------
# get_cram_cards (drill picking, seeded rotation, DueCard shape)
# ---------------------------------------------------------------------------


def _point_row(point_id: str, n_drills: int, code: str = "tr") -> dict:
    return {
        "point_id": point_id,
        "title": "Locative case",
        "language_code": code,
        "drill_ids": [f"{point_id[:-2]}{i:02d}" for i in range(n_drills)],
        "sentences": [f"S{i} {{{{answer}}}}." for i in range(n_drills)],
        "answers": [f"a{i}" for i in range(n_drills)],
        "hints": [None] * n_drills,
        "translations": [f"t{i}" for i in range(n_drills)],
        "glosses": [None] * n_drills,
        "transliterations": [None] * n_drills,
        "cells": [None] * n_drills,
        "lemmas": [None] * n_drills,
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
# attach_cram_charts (WP25c: Gym drills carry the exercised word's chart)
# ---------------------------------------------------------------------------


class _StubNLP:
    """Just enough NLP to bridge a surface form to its dictionary form."""

    def normalize(self, text: str) -> str:
        return text.lower().strip()

    def lemmatize(self, word: str) -> str:
        return {"evlerde": "ev"}.get(word, word)


def _gym_card(answer: str, code: str = "tr") -> dict:
    return {
        "id": f"cram-{POINT_A}-0",
        "card_type": "grammar",
        "card_id": POINT_A,
        "correct_answer": answer,
        "language_code": code,
        "morphology": None,
    }


CHARTED = (
    '{"charts": [{"title": "Cases", "rows": [["locative", "evde"]]}]}'
)


class TestAttachCramCharts:
    @pytest.mark.asyncio
    async def test_lemma_links_drill_to_chart(self):
        from backend.repositories.cards import attach_cram_charts

        card = _gym_card("evlerde")
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[
            {"word": "ev", "morphology": CHARTED, "usage_note": "house"},
        ])
        with patch.dict("backend.services.nlp.NLP_BACKENDS", {"tr": _StubNLP()}):
            await attach_cram_charts(conn, [card])

        assert card["morphology"] == CHARTED
        assert card["chart_word"] == "ev"
        assert card["chart_usage_note"] == "house"
        # The lookup asked for both the lemma and the surface form.
        looked_up = conn.fetch.await_args.args[2]
        assert "ev" in looked_up and "evlerde" in looked_up

    @pytest.mark.asyncio
    async def test_no_vocabulary_match_leaves_card_bare(self):
        from backend.repositories.cards import attach_cram_charts

        card = _gym_card("evlerde")
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[])
        with patch.dict("backend.services.nlp.NLP_BACKENDS", {"tr": _StubNLP()}):
            await attach_cram_charts(conn, [card])
        assert card["morphology"] is None
        assert "chart_word" not in card

    @pytest.mark.asyncio
    async def test_chips_only_morphology_is_not_a_chart(self):
        from backend.repositories.cards import attach_cram_charts

        card = _gym_card("evlerde")
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[
            {"word": "ev", "morphology": '{"chips": [{"label": "gender"}]}',
             "usage_note": None},
        ])
        with patch.dict("backend.services.nlp.NLP_BACKENDS", {"tr": _StubNLP()}):
            await attach_cram_charts(conn, [card])
        assert card["morphology"] is None

    @pytest.mark.asyncio
    async def test_short_answers_skip_the_lookup_entirely(self):
        from backend.repositories.cards import attach_cram_charts

        card = _gym_card("a0")
        conn = AsyncMock()
        await attach_cram_charts(conn, [card])
        conn.fetch.assert_not_awaited()
        assert card["morphology"] is None


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


class TestGymAttemptEndpoint:
    DRILL = "cccccccc-cccc-cccc-cccc-cccccccccccc"

    def test_requires_auth(self, client):
        assert client.post(
            "/api/review/gym/attempt",
            json={"drill_id": self.DRILL, "answer_result": "correct"},
        ).status_code == 401

    def test_records_attempt(self, client):
        with patch("backend.routers.review.record_gym_attempt",
                   new=AsyncMock()) as mock_rec:
            resp = client.post(
                "/api/review/gym/attempt",
                json={"drill_id": self.DRILL, "answer_result": "wrong_form",
                      "used_hint": True},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
        # (conn, user_id, drill_id, answer_result, used_hint)
        assert mock_rec.await_args.args[2] == self.DRILL
        assert mock_rec.await_args.args[3] == "wrong_form"
        assert mock_rec.await_args.args[4] is True


class TestGymPlacementColdStart:
    """Owner: the Gym should have insight into test results.

    A learner who has never opened the Gym has no gym_progress at all, so the
    'forms' tier is empty and generation aims at nothing. The forms they
    missed at placement are the only evidence that exists on day one.
    """

    def test_placement_miss_aims_generation_when_the_gym_has_no_history(self, client):
        p = _patch_gym_gen(placement_cells={POINT_A: "gecmis"})
        with p[0], p[1], p[2], p[3] as mock_gen, p[4] as mock_add, \
             p[5], p[6], p[7], p[8], p[9]:
            resp = client.post(
                "/api/review/gym/generate",
                json={"point_ids": [POINT_A]},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert mock_gen.await_args.kwargs["cell"] == "gecmis"
        assert mock_add.await_args.kwargs["cell"] == "gecmis"

    def test_gym_history_outranks_the_placement_miss(self, client):
        """Repeated, recent evidence from this very surface beats one miss on
        a test — the placement only fills the gap."""
        p = _patch_gym_gen(
            struggles={POINT_A: [
                {"cell": "vosotros", "seen": 6, "misses": 3,
                 "wrong_form": 2, "hint_used": 1},
            ]},
            placement_cells={POINT_A: "gecmis"},
        )
        with p[0], p[1], p[2], p[3] as mock_gen, p[4], \
             p[5], p[6], p[7], p[8], p[9]:
            resp = client.post(
                "/api/review/gym/generate",
                json={"point_ids": [POINT_A]},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert mock_gen.await_args.kwargs["cell"] == "vosotros"

    def test_no_evidence_anywhere_stays_cell_agnostic(self, client):
        p = _patch_gym_gen()
        with p[0], p[1], p[2], p[3] as mock_gen, p[4], \
             p[5], p[6], p[7], p[8], p[9]:
            resp = client.post(
                "/api/review/gym/generate",
                json={"point_ids": [POINT_A]},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert mock_gen.await_args.kwargs["cell"] is None
