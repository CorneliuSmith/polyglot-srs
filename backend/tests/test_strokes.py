"""The stroke library — the script model, the strokes it stores, and the
authoring endpoints (docs/plans/handwriting.md, §5–6)."""

from __future__ import annotations

import json
import time
from unittest.mock import AsyncMock, patch

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.repositories.strokes import clean_strokes
from backend.services.scripts import (
    alphabet_for,
    expected_forms,
    forms_for,
    script_of,
    styles_of,
)
from backend.tests.fakes import mock_conn

TEST_SECRET = "test-jwt-secret-for-unit-tests-32bytes"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
TEST_LANGUAGE_ID = "11111111-1111-1111-1111-111111111111"
GLYPH_ID = "22222222-2222-2222-2222-222222222222"


class FakeSettings:
    supabase_jwt_secret = TEST_SECRET
    supabase_url = "https://fake.supabase.co"
    supabase_anon_key = "k"
    supabase_service_role_key = "sk"
    database_url = "postgresql://fake/db"
    environment = "test"
    cors_origins = []
    anthropic_api_key = ""
    tutor_dev_mock = True


def _auth_headers() -> dict:
    token = pyjwt.encode(
        {"sub": TEST_USER_ID, "aud": "authenticated", "exp": int(time.time()) + 3600},
        TEST_SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


class TestScriptModel:
    def test_scripts_and_styles(self):
        assert script_of("ru") == "cyrillic" and script_of("fa") == "arabic"
        assert script_of("es") == "latin" and script_of(None) == "latin"
        assert styles_of("cyrillic") == ["cursive", "print"]
        assert styles_of("arabic") == ["naskh", "ruqah"]
        assert styles_of("thai") == ["print"]

    def test_forms_follow_the_hand_not_the_font(self):
        assert forms_for("arabic", "ب") == ["isolated", "final", "initial", "medial"]
        # Alif never joins left: two forms only.
        assert forms_for("arabic", "ا") == ["isolated", "final"]
        assert forms_for("cyrillic", "а") == ["lower", "upper"]
        assert forms_for("hangul", "ㄱ") == ["letter"]

    def test_alphabets_come_from_the_decks_and_latin_from_a_to_z(self):
        ru = alphabet_for("ru")
        assert len(ru) == 33 and ru[0]["glyph"] == "а" and ru[0]["forms"] == ["lower", "upper"]
        es = alphabet_for("es")
        assert [x["glyph"] for x in es][:3] == ["a", "b", "c"] and len(es) == 26
        assert expected_forms("ru") == 66
        ar = expected_forms("ar")
        assert ar > 2 * len(alphabet_for("ar"))


class TestCleanStrokes:
    def test_rounds_clamps_and_drops_taps(self):
        st = clean_strokes([[[0.4, 1200], [10, 20]], [[5, 5]], [{"x": -3, "y": 7}, {"x": 8, "y": 9}]])
        assert st == [[[0, 1000], [10, 20]], [[0, 7], [8, 9]]]

    def test_refuses_what_is_not_strokes(self):
        for bad in ([], "x", [[[1]]], [[["a", "b"], [1, 2]]], [[[1, 2]]]):
            with pytest.raises(ValueError):
                clean_strokes(bad)


def _conn(with_tables: bool) -> AsyncMock:
    conn = mock_conn()
    conn.fetch = AsyncMock(return_value=[])
    conn.execute = AsyncMock(return_value="UPDATE 1")

    async def fetchval(sql, *args):
        if "to_regclass" in sql:
            return with_tables
        if "SELECT code FROM languages" in sql:
            return "ar"
        return None

    async def fetchrow(sql, *args):
        if "FROM languages" in sql:
            return {"name": "Arabic", "code": "ar", "tutor_model": None}
        if "RETURNING id, script, glyph" in sql:
            return {"id": GLYPH_ID, "script": "arabic", "glyph": args[1], "form": args[2],
                    "style": args[3], "strokes": args[4], "joins": args[5],
                    "hints": args[6], "source": args[7], "reviewed": False}
        if "count(*) AS a" in sql:
            return {"a": 3, "r": 1}
        return None

    conn.fetchval = AsyncMock(side_effect=fetchval)
    conn.fetchrow = AsyncMock(side_effect=fetchrow)
    return conn


@pytest.fixture(params=["bare", "tables"])
def client(request):
    from contextlib import asynccontextmanager

    conn = _conn(request.param == "tables")

    @asynccontextmanager
    async def fake_conn(*args, **kwargs):
        yield conn

    with patch("backend.main.init_pool", new=AsyncMock()), \
         patch("backend.main.close_pool", new=AsyncMock()), \
         patch("backend.main.get_settings", return_value=FakeSettings()), \
         patch("backend.dependencies.get_settings", return_value=FakeSettings()), \
         patch("backend.routers.write.rls_connection", fake_conn), \
         patch("backend.routers.contribute.rls_connection", fake_conn), \
         patch("backend.routers.contribute.privileged_connection", fake_conn), \
         patch("backend.routers.contribute._require_language_role", new=AsyncMock()):
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as c:
            c.fake_conn = conn
            c.tables = request.param == "tables"
            yield c


class TestLearnerEndpoints:
    def test_alphabet_frames_the_library(self, client):
        resp = client.get(f"/api/write/alphabet?language_id={TEST_LANGUAGE_ID}",
                          headers=_auth_headers())
        assert resp.status_code == 200
        body = resp.json()
        assert body["script"] == "arabic" and body["styles"] == ["naskh", "ruqah"]
        assert body["letters"][0]["forms"]

    def test_manifest_counts_per_style(self, client):
        resp = client.get(f"/api/write/manifest?language_id={TEST_LANGUAGE_ID}",
                          headers=_auth_headers())
        assert resp.status_code == 200
        body = resp.json()
        assert body["available"] is client.tables
        if client.tables:
            assert body["styles"]["naskh"] == {"authored": 3, "reviewed": 1,
                                                "exemplars": 3, "exemplars_reviewed": 1}
        else:
            assert body["styles"]["naskh"]["authored"] == 0

    def test_glyphs_are_reviewed_only(self, client):
        client.fake_conn.fetch = AsyncMock(return_value=[])
        resp = client.get(f"/api/write/glyphs?language_id={TEST_LANGUAGE_ID}&style=naskh",
                          headers=_auth_headers())
        assert resp.status_code == 200 and resp.json()["glyphs"] == []
        if client.tables:
            sql, *args = client.fake_conn.fetch.await_args_list[0].args
            assert "reviewed" in sql and args[2] is True


class TestAuthoringEndpoints:
    def test_upsert_validates_style_form_and_strokes(self, client):
        base = {"language_id": TEST_LANGUAGE_ID, "glyph": "ب", "form": "medial",
                "style": "naskh", "strokes": [[[10, 10], [500, 500]]]}
        assert client.put("/api/contribute/strokes", headers=_auth_headers(),
                          json={**base, "style": "gothic"}).status_code == 422
        # Alif has no medial form.
        assert client.put("/api/contribute/strokes", headers=_auth_headers(),
                          json={**base, "glyph": "ا"}).status_code == 422
        assert client.put("/api/contribute/strokes", headers=_auth_headers(),
                          json={**base, "strokes": [[[1, 1]]]}).status_code in (422, 503)
        resp = client.put("/api/contribute/strokes", headers=_auth_headers(),
                          json={**base, "hints": ["start at the top"]})
        if client.tables:
            assert resp.status_code == 200, resp.text
            assert resp.json()["glyph"] == "ب" and resp.json()["reviewed"] is False
            sql, *args = client.fake_conn.fetchrow.await_args_list[-1].args
            assert "ON CONFLICT (script, glyph, form, style)" in sql
            assert json.loads(args[4]) == [[[10, 10], [500, 500]]]
        else:
            assert resp.status_code == 503

    def test_review_and_delete(self, client):
        r = client.post(f"/api/contribute/strokes/{GLYPH_ID}/review?language_id={TEST_LANGUAGE_ID}",
                        headers=_auth_headers())
        d = client.delete(f"/api/contribute/strokes/{GLYPH_ID}?language_id={TEST_LANGUAGE_ID}",
                          headers=_auth_headers())
        if client.tables:
            assert r.status_code == 200 and r.json()["reviewed"] is True
            assert d.status_code == 200
        else:
            assert r.status_code == 404 and d.status_code == 404

    def test_exemplar_create(self, client):
        client.fake_conn.fetchrow = AsyncMock(return_value={
            "id": GLYPH_ID, "script": "arabic", "language_code": "ar", "style": "naskh",
            "text": "أنا أحب البيت", "source": "workshop", "reviewed": False})
        resp = client.put("/api/contribute/exemplars", headers=_auth_headers(),
                          json={"language_id": TEST_LANGUAGE_ID, "style": "naskh",
                                "text": " أنا أحب البيت ", "strokes": [[[1, 1], [900, 20]]]})
        if client.tables:
            assert resp.status_code == 200, resp.text
            assert resp.json()["text"] == "أنا أحب البيت"
        else:
            assert resp.status_code == 503


class TestLettersProgress:
    def test_an_attempt_is_recorded_and_known_after_three_passes(self, client):
        client.fake_conn.fetchrow = AsyncMock(side_effect=lambda sql, *a: (
            {"name": "Arabic", "code": "ar", "tutor_model": None} if "FROM languages" in sql
            else {"attempts": 4, "passes": 3, "best_score": 0.9} if "RETURNING attempts" in sql
            else None))
        resp = client.post("/api/write/progress", headers=_auth_headers(),
                           json={"language_id": TEST_LANGUAGE_ID, "glyph_id": GLYPH_ID,
                                 "passed": True, "score": 0.9})
        assert resp.status_code == 200, resp.text
        if client.tables:
            assert resp.json() == {"glyph_id": GLYPH_ID, "attempts": 4, "passes": 3,
                                   "best_score": 0.9, "known": True}
        else:
            assert resp.json()["known"] is False

    def test_a_traced_word_records_each_form_once(self, client):
        calls: list[tuple] = []

        async def fetchrow(sql, *a):
            if "FROM languages" in sql:
                return {"name": "Arabic", "code": "ar", "tutor_model": None}
            if "RETURNING attempts" in sql:
                calls.append(a)
                return {"attempts": 1, "passes": 1 if a[2] else 0, "best_score": a[3]}
            return None
        client.fake_conn.fetchrow = AsyncMock(side_effect=fetchrow)
        other = "33333333-3333-3333-3333-333333333333"
        resp = client.post("/api/write/progress/batch", headers=_auth_headers(),
                           json={"language_id": TEST_LANGUAGE_ID, "attempts": [
                               {"glyph_id": GLYPH_ID, "passed": True, "score": 0.8},
                               {"glyph_id": other, "passed": False, "score": 0.2},
                               {"glyph_id": GLYPH_ID, "passed": False, "score": 0.1},
                           ]})
        assert resp.status_code == 200, resp.text
        if client.tables:
            # The repeat of the first form is folded: one row per form.
            assert [c[1] for c in calls] == [GLYPH_ID, other]
            assert [i["glyph_id"] for i in resp.json()["items"]] == [GLYPH_ID, other]
            assert resp.json()["items"][0]["passes"] == 1
        else:
            assert resp.json() == {"items": []}

    def test_progress_lists_the_learners_forms(self, client):
        resp = client.get(f"/api/write/progress?language_id={TEST_LANGUAGE_ID}&style=naskh",
                          headers=_auth_headers())
        assert resp.status_code == 200 and resp.json() == {"items": []}
