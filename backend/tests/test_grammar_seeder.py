"""Tests for the grammar curriculum seeder and the grammar learn path."""

from __future__ import annotations

import json
import time
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.services.seeder.seed_grammar import GrammarSeeder

TEST_SECRET = "test-jwt-secret-for-unit-tests-32bytes"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
TEST_LANGUAGE_ID = "11111111-1111-1111-1111-111111111111"


# ---------------------------------------------------------------------------
# Curriculum transform
# ---------------------------------------------------------------------------


class TestGrammarTransform:
    def test_real_russian_curriculum_parses(self):
        data = GrammarSeeder("fake://db", "ru").transform()
        assert len(data["points"]) >= 3
        assert any("Prepositional" in p["title"] for p in data["points"])
        for p in data["points"]:
            assert p["explanation"]  # shipped content has real explanations
            for d in p["drills"]:
                assert "{{answer}}" in d["sentence"]
                assert d["answer"]

    def test_real_curriculum_includes_references(self):
        data = GrammarSeeder("fake://db", "ru").transform()
        prep = next(p for p in data["points"] if "Prepositional" in p["title"])
        assert prep["references"]
        assert all(
            r["url"].startswith("https://") for r in prep["references"]
        )

    def test_real_turkish_curriculum_parses(self):
        data = GrammarSeeder("fake://db", "tr").transform()
        titles = [p["title"] for p in data["points"]]
        assert any("Locative" in t for t in titles)
        # Every point has a valid source; the A1 core is human-reviewed, while
        # deeper levels MAY be drafts (reviewed=false) awaiting verification.
        assert all(p["source"] == "contributor" for p in data["points"])
        assert any(p["reviewed"] for p in data["points"])

    def test_non_latin_paths_reach_c2_with_transliteration(self):
        # Regression guard for the A1->C2 deepening of the non-Latin-script
        # languages (WP3b): full CEFR ladder, every drill transliterated (the
        # SCRIPT_FIRST hint layer depends on it), and the paradigm density
        # gate satisfied by transform().
        for code in ("ar", "el"):
            data = GrammarSeeder("fake://db", code).transform()
            levels = {p["level"] for p in data["points"]}
            assert {"A1", "A2", "B1", "B2", "C1", "C2"} <= levels, code
            assert len(data["points"]) >= 40, code
            for p in data["points"]:
                for d in p["drills"]:
                    assert d["transliteration"], f"{code}/{p['title']}: no translit"

    def test_full_c2_ladder_languages(self):
        # WP2 + WP3b: every language authored all the way to C2 keeps the full
        # CEFR ladder and its reviewed-live status. Guards against a partial
        # re-seed silently dropping the advanced tiers.
        for code in ("es", "tr", "ru", "ar", "el", "ro", "fr", "de", "it", "ca", "pt", "en", "mi"):
            data = GrammarSeeder("fake://db", code).transform()
            levels = {p["level"] for p in data["points"]}
            assert {"A1", "A2", "B1", "B2", "C1", "C2"} <= levels, code
            assert len(data["points"]) >= 40, code
            assert all(p["source"] == "contributor" for p in data["points"]), code
            # these paths are human-reviewed and live (not draft-gated)
            assert any(p["reviewed"] for p in data["points"]), code

    def test_every_point_leads_with_authoritative_reference(self):
        # Content standard (§3b, 2026-07): Wikipedia is fine but never alone.
        # Every point's references open with a verified authoritative source
        # (academy grammar, national-corpus portal, or public-domain course).
        for code in ("es", "fr", "de", "it", "ca", "pt", "ro", "el", "ru",
                     "ar", "en", "tr", "mi", "sw", "yo", "ha", "xh"):
            data = GrammarSeeder("fake://db", code).transform()
            for point in data["points"]:
                refs = point.get("references") or []
                assert refs, f"{code}/{point['title']}: no references"
                assert "wikipedia.org" not in refs[0]["url"], (
                    f"{code}/{point['title']}: leads with Wikipedia"
                )

    def test_invalid_drills_and_points_skipped(self, tmp_path):
        import backend.services.seeder.seed_grammar as mod

        (tmp_path / "zz_grammar.json").write_text(json.dumps({
            "lists": [],
            "points": [
                {"title": "Good", "drills": [
                    {"sentence": "a {{answer}} b", "answer": "x"},
                    {"sentence": "no marker here", "answer": "y"},
                    {"sentence": "c {{answer}}", "answer": ""},
                ]},
                {"title": "", "drills": []},
            ],
        }), encoding="utf-8")

        original = mod.GRAMMAR_DIR
        mod.GRAMMAR_DIR = tmp_path
        try:
            data = GrammarSeeder("fake://db", "zz").transform()
        finally:
            mod.GRAMMAR_DIR = original

        assert len(data["points"]) == 1
        assert len(data["points"][0]["drills"]) == 1

    def test_missing_file_raises(self, tmp_path):
        import backend.services.seeder.seed_grammar as mod

        original = mod.GRAMMAR_DIR
        mod.GRAMMAR_DIR = tmp_path
        try:
            with pytest.raises(FileNotFoundError):
                GrammarSeeder("fake://db", "ru").transform()
        finally:
            mod.GRAMMAR_DIR = original

    def test_unknown_source_falls_back_to_pending(self, tmp_path):
        import backend.services.seeder.seed_grammar as mod

        (tmp_path / "zz_grammar.json").write_text(json.dumps({
            "points": [{"title": "P", "source": "bogus", "drills": []}],
        }), encoding="utf-8")
        original = mod.GRAMMAR_DIR
        mod.GRAMMAR_DIR = tmp_path
        try:
            data = GrammarSeeder("fake://db", "zz").transform()
        finally:
            mod.GRAMMAR_DIR = original
        assert data["points"][0]["source"] == "pending"

    def _transform(self, tmp_path, points):
        import backend.services.seeder.seed_grammar as mod

        (tmp_path / "zz_grammar.json").write_text(
            json.dumps({"points": points}), encoding="utf-8"
        )
        original = mod.GRAMMAR_DIR
        mod.GRAMMAR_DIR = tmp_path
        try:
            return GrammarSeeder("fake://db", "zz").transform()
        finally:
            mod.GRAMMAR_DIR = original

    def test_paradigm_full_coverage_passes(self, tmp_path):
        data = self._transform(tmp_path, [{
            "title": "Pronouns",
            "paradigm": ["yo", "tú"],
            "drills": [
                {"sentence": "{{answer}} soy.", "answer": "Yo", "cell": "yo"},
                {"sentence": "{{answer}} soy alto.", "answer": "Yo", "cell": "yo"},
                {"sentence": "{{answer}} eres.", "answer": "Tú", "cell": "tú"},
                {"sentence": "{{answer}} eres alto.", "answer": "Tú", "cell": "tú"},
            ],
        }])
        assert [d["cell"] for d in data["points"][0]["drills"]] == \
            ["yo", "yo", "tú", "tú"]

    def test_paradigm_thin_cell_fails_density_gate(self, tmp_path):
        # One frame per form invites memorizing the sentence — 2 per cell
        # is the floor.
        with pytest.raises(ValueError, match="below 2 drills"):
            self._transform(tmp_path, [{
                "title": "Pronouns",
                "paradigm": ["yo", "tú"],
                "drills": [
                    {"sentence": "{{answer}} soy.", "answer": "Yo", "cell": "yo"},
                    {"sentence": "{{answer}} soy alto.", "answer": "Yo", "cell": "yo"},
                    {"sentence": "{{answer}} eres.", "answer": "Tú", "cell": "tú"},
                ],
            }])

    def test_paradigm_uncovered_cell_fails_loudly(self, tmp_path):
        # A paradigm member with no drill is a member the learner never
        # learns — the seed must fail, not ship the gap silently.
        with pytest.raises(ValueError, match="no drill.*vosotros|vosotros"):
            self._transform(tmp_path, [{
                "title": "Pronouns",
                "paradigm": ["yo", "vosotros"],
                "drills": [
                    {"sentence": "{{answer}} soy.", "answer": "Yo", "cell": "yo"},
                ],
            }])

    def test_paradigm_unknown_cell_fails(self, tmp_path):
        with pytest.raises(ValueError, match="not in the paradigm"):
            self._transform(tmp_path, [{
                "title": "Pronouns",
                "paradigm": ["yo"],
                "drills": [
                    {"sentence": "{{answer}} soy.", "answer": "Yo", "cell": "typo"},
                ],
            }])

    def test_real_spanish_pronoun_paradigm_fully_covered(self):
        # The motivating case: 9 persons = 9 questions wearing one card.
        data = GrammarSeeder("fake://db", "es").transform()
        pron = next(
            p for p in data["points"] if p["title"].startswith("Subject pronouns")
        )
        cells = {d["cell"] for d in pron["drills"]}
        assert {"yo", "tú", "él", "ella", "usted",
                "nosotros", "vosotros", "ellos", "ustedes"} <= cells
        assert len(pron["drills"]) >= 9


# ---------------------------------------------------------------------------
# Grammar learn endpoint
# ---------------------------------------------------------------------------


class FakeSettings:
    supabase_jwt_secret = TEST_SECRET
    supabase_url = "https://fake.supabase.co"
    supabase_anon_key = "k"
    supabase_service_role_key = "k"
    database_url = "postgresql://fake/db"
    environment = "test"
    cors_origins = []
    tutor_dev_mock = True
    anthropic_api_key = ""
    tutor_model = "claude-opus-4-8"
    tutor_summary_model = "claude-sonnet-4-6"
    tutor_free_access = True


def _auth_headers() -> dict:
    token = pyjwt.encode(
        {"sub": TEST_USER_ID, "aud": "authenticated", "exp": int(time.time()) + 3600},
        TEST_SECRET, algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


@asynccontextmanager
async def _fake_rls(user_id: str):
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)  # no profile row -> batch_size 5
    yield conn


@pytest.fixture()
def client():
    with patch("backend.main.init_pool", new=AsyncMock()), \
         patch("backend.main.close_pool", new=AsyncMock()), \
         patch("backend.main.get_settings", return_value=FakeSettings()), \
         patch("backend.dependencies.get_settings", return_value=FakeSettings()), \
         patch("backend.routers.review.rls_connection", _fake_rls):
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


class TestGrammarLearnEndpoint:
    def test_learns_grammar_cards(self, client):
        added = {"added": 3, "items": ["a", "b", "c"]}
        with patch("backend.routers.review.add_grammar_learn_batch",
                   new=AsyncMock(return_value=added)) as mock_grammar, \
             patch("backend.routers.review.add_learn_batch",
                   new=AsyncMock()) as mock_vocab:
            resp = client.post(
                "/api/review/learn",
                json={"language_id": TEST_LANGUAGE_ID, "card_type": "grammar"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json()["added"] == 3
        mock_grammar.assert_awaited_once()
        mock_vocab.assert_not_awaited()

    def test_defaults_to_vocabulary(self, client):
        with patch("backend.routers.review.add_learn_batch",
                   new=AsyncMock(return_value={"added": 0, "items": []})) as mock_vocab, \
             patch("backend.routers.review.add_grammar_learn_batch",
                   new=AsyncMock()) as mock_grammar:
            resp = client.post(
                "/api/review/learn",
                json={"language_id": TEST_LANGUAGE_ID},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        mock_vocab.assert_awaited_once()
        mock_grammar.assert_not_awaited()

    def test_invalid_card_type_422(self, client):
        resp = client.post(
            "/api/review/learn",
            json={"language_id": TEST_LANGUAGE_ID, "card_type": "audio"},
            headers=_auth_headers(),
        )
        assert resp.status_code == 422


def test_every_pointed_level_gets_a_deck(tmp_path):
    # A level with points but no declared list gets one synthesized —
    # eight languages once showed only their A1 deck because the
    # deepening waves appended points without lists.
    import backend.services.seeder.seed_grammar as mod

    (tmp_path / "zz_grammar.json").write_text(json.dumps({"points": [
        {"title": "P1", "level": "A1", "drills": [
            {"sentence": "a {{answer}}", "answer": "x"}]},
        {"title": "P2", "level": "B2", "drills": [
            {"sentence": "b {{answer}}", "answer": "y"}]},
    ]}), encoding="utf-8")
    original = mod.GRAMMAR_DIR
    mod.GRAMMAR_DIR = tmp_path
    try:
        data = GrammarSeeder("fake://db", "zz").transform()
    finally:
        mod.GRAMMAR_DIR = original
    levels = {lst["level"] for lst in data["lists"]}
    assert levels == {"A1", "B2"}
