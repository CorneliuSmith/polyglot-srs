"""WP21 Reader tests — service shape, gap matching, endpoint flow.

The dev-mock path (tutor_dev_mock=True) exercises generation end-to-end
with no API key, same pattern as the tutor tests.
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, patch

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.repositories.reader import log_grammar_gaps
from backend.services.reader import _mock_reading, _validate_reading

TEST_SECRET = "test-jwt-secret-for-unit-tests-32bytes"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
TEST_LANGUAGE_ID = "11111111-1111-1111-1111-111111111111"
TEST_READING_ID = "22222222-2222-2222-2222-222222222222"


class FakeSettings:
    supabase_jwt_secret = TEST_SECRET
    supabase_url = "https://fake.supabase.co"
    supabase_anon_key = "k"
    supabase_service_role_key = "sk"
    database_url = "postgresql://fake/db"
    environment = "test"
    cors_origins = []
    anthropic_api_key = ""
    tutor_model = "claude-sonnet-5"
    tutor_model_low_resource = "claude-opus-4-8"
    tutor_dev_mock = True
    tutor_free_access = True
    tutor_free_monthly_messages = 20
    tutor_single_monthly_messages = 100
    tutor_all_monthly_messages = 300
    tutor_plus_monthly_messages = 1000


def _auth_headers() -> dict:
    token = pyjwt.encode(
        {"sub": TEST_USER_ID, "aud": "authenticated",
         "exp": int(time.time()) + 3600},
        TEST_SECRET, algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class TestReadingShape:
    def test_mock_reading_passes_validation(self):
        reading = _validate_reading(_mock_reading("cats"))
        assert reading["sentences"]
        assert reading["new_words"]
        # Every token glossed; seeded words marked.
        seeded = [
            t for s in reading["sentences"] for t in s["tokens"] if t.get("new")
        ]
        assert seeded
        for s in reading["sentences"]:
            assert all(t.get("gloss") for t in s["tokens"])

    def test_validation_rejects_empty(self):
        with pytest.raises(ValueError):
            _validate_reading({"sentences": []})
        with pytest.raises(ValueError):
            _validate_reading(
                {"sentences": [{"text": "x", "tokens": []}]}
            )


class TestGapMatching:
    def _run(self, titles: list[str], structures: list[str]) -> int:
        conn = AsyncMock()
        conn.fetch = AsyncMock(
            return_value=[{"t": t.lower()} for t in titles]
        )
        conn.execute = AsyncMock()
        return asyncio.run(
            log_grammar_gaps(conn, "lang-1", structures, "example")
        ), conn

    def test_covered_structures_are_not_logged(self):
        logged, conn = self._run(
            ["Present tense of -ar verbs", "Gustar and similar verbs"],
            # exact-insensitive and containment both count as covered
            ["gustar and similar verbs", "present tense"],
        )
        assert logged == 0
        conn.execute.assert_not_awaited()

    def test_uncovered_structures_are_upserted(self):
        logged, conn = self._run(
            ["Present tense of -ar verbs"],
            ["Diminutives (-ito/-ita)", "present tense"],
        )
        assert logged == 1
        sql = conn.execute.await_args.args[0]
        assert "ON CONFLICT (language_id, structure)" in sql
        assert conn.execute.await_args.args[2] == "Diminutives (-ito/-ita)"


# ---------------------------------------------------------------------------
# Endpoints (dev-mock generation, DB mocked)
# ---------------------------------------------------------------------------


def _conn_for_generate():
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])          # learner model queries
    conn.fetchrow = AsyncMock(return_value=None)     # profile row
    conn.fetchval = AsyncMock(return_value=None)     # model override
    conn.execute = AsyncMock()
    return conn


@pytest.fixture()
def client():
    from contextlib import asynccontextmanager

    conn = _conn_for_generate()

    @asynccontextmanager
    async def fake_conn(*args):
        yield conn

    with patch("backend.main.init_pool", new=AsyncMock()), \
         patch("backend.main.close_pool", new=AsyncMock()), \
         patch("backend.main.get_settings", return_value=FakeSettings()), \
         patch("backend.dependencies.get_settings", return_value=FakeSettings()), \
         patch("backend.routers.tutor.get_settings", return_value=FakeSettings()), \
         patch("backend.services.reader.get_settings", return_value=FakeSettings()), \
         patch("backend.routers.reader.rls_connection", fake_conn), \
         patch("backend.routers.reader.privileged_connection", fake_conn), \
         patch("backend.services.allowance.get_settings", return_value=FakeSettings()), \
         patch("backend.services.allowance.rls_connection", fake_conn), \
         patch("backend.routers.tutor.rls_connection", fake_conn):
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as c:
            c.fake_conn = conn
            yield c


def _poll_status(client, tries: int = 100) -> dict:
    """Ask until the write settles. Dev-mock generation is instant, so this
    is a handful of loops in practice — the loop exists because the work is
    a background task now, not because it is slow."""
    for _ in range(tries):
        resp = client.get(
            "/api/reader/generate/status", headers=_auth_headers()
        )
        assert resp.status_code == 200
        body = resp.json()
        if not body.get("generating"):
            return body
        time.sleep(0.02)
    raise AssertionError("the write never settled")


@pytest.fixture(autouse=True)
def _clear_writes():
    """The in-flight write is module state (it has to outlive the request),
    so it needs clearing between tests like any shared fixture."""
    from backend.routers import reader as reader_router

    for store in (
        reader_router._WRITES,
        reader_router._RESULTS,
        reader_router._WRITE_ERRORS,
    ):
        store.clear()
    yield


class TestGenerateEndpoint:
    def test_requires_auth(self, client):
        resp = client.post(
            "/api/reader/generate",
            json={"language_id": TEST_LANGUAGE_ID,
                  "language_code": "es", "topic": "cats"},
        )
        assert resp.status_code == 401

    def test_generates_saves_and_reports_allowance(self, client):
        """The request starts the write and answers at once; the reading
        arrives on the poll. Holding the connection through a graded C2
        text is what DigitalOcean's gateway killed."""
        with patch(
            "backend.routers.reader.save_reading",
            new=AsyncMock(return_value=TEST_READING_ID),
        ) as mock_save, patch(
            "backend.routers.reader.log_grammar_gaps",
            new=AsyncMock(return_value=1),
        ) as mock_gaps, patch(
            "backend.routers.reader.log_tutor_usage", new=AsyncMock(),
        ) as mock_usage:
            resp = client.post(
                "/api/reader/generate",
                json={"language_id": TEST_LANGUAGE_ID,
                      "language_code": "es", "topic": "cats"},
                headers=_auth_headers(),
            )
            assert resp.status_code == 200
            assert resp.json() == {"generating": True}
            body = _poll_status(client)

        assert body["id"] == TEST_READING_ID
        assert body["reading"]["sentences"]
        assert body["reading"]["new_words"]
        assert body["allowance"]["unlimited"] is True
        mock_save.assert_awaited_once()
        mock_usage.assert_awaited_once()
        # The dev-mock reading contains an uncovered structure — the gap
        # collector must have been fed the structure list.
        structures = mock_gaps.await_args.args[2]
        assert "[dev mock] an uncovered structure" in structures

    def test_the_reading_is_served_exactly_once(self, client):
        # Collecting clears the slot: a later poll must not re-open a text
        # the learner has already been given (and maybe closed).
        with patch(
            "backend.routers.reader.save_reading",
            new=AsyncMock(return_value=TEST_READING_ID),
        ), patch(
            "backend.routers.reader.log_grammar_gaps", new=AsyncMock(return_value=0),
        ), patch(
            "backend.routers.reader.log_tutor_usage", new=AsyncMock(),
        ):
            client.post(
                "/api/reader/generate",
                json={"language_id": TEST_LANGUAGE_ID,
                      "language_code": "es", "topic": "cats"},
                headers=_auth_headers(),
            )
            assert _poll_status(client)["id"] == TEST_READING_ID
        again = client.get(
            "/api/reader/generate/status", headers=_auth_headers()
        ).json()
        assert again == {"generating": False}

    def test_a_failed_write_is_reported_not_swallowed(self, client):
        """A background task nobody awaits fails silently — the whole point
        of the error slot is that the page can say what went wrong instead
        of spinning forever."""
        with patch(
            "backend.routers.reader.generate_reading",
            new=AsyncMock(side_effect=ValueError("ran past the token limit")),
        ):
            client.post(
                "/api/reader/generate",
                json={"language_id": TEST_LANGUAGE_ID, "language_code": "es",
                      "topic": "theoretical physics", "complexity": "C2"},
                headers=_auth_headers(),
            )
            body = _poll_status(client)
        assert body["generating"] is False
        assert "Couldn't write that one" in body["error"]
        # …and the error is served once, then cleared.
        assert client.get(
            "/api/reader/generate/status", headers=_auth_headers()
        ).json() == {"generating": False}

    def test_a_second_tap_joins_the_write_instead_of_doubling_it(self, client):
        started = asyncio.Event()
        release = asyncio.Event()

        async def slow(*args, **kwargs):
            started.set()
            await release.wait()
            return _mock_reading("cats"), {"input_tokens": 1, "output_tokens": 1}

        with patch("backend.routers.reader.generate_reading", new=slow), patch(
            "backend.routers.reader.save_reading",
            new=AsyncMock(return_value=TEST_READING_ID),
        ), patch(
            "backend.routers.reader.log_grammar_gaps", new=AsyncMock(return_value=0),
        ), patch(
            "backend.routers.reader.log_tutor_usage", new=AsyncMock(),
        ):
            body = {"language_id": TEST_LANGUAGE_ID, "language_code": "es",
                    "topic": "cats"}
            first = client.post(
                "/api/reader/generate", json=body, headers=_auth_headers()
            )
            second = client.post(
                "/api/reader/generate", json=body, headers=_auth_headers()
            )
            assert first.json() == {"generating": True}
            assert second.json() == {"generating": True}
            # The impatient second tap did NOT spend a second generation.
            status = client.get(
                "/api/reader/generate/status", headers=_auth_headers()
            ).json()
            assert status == {"generating": True}
            release.set()
            assert _poll_status(client)["id"] == TEST_READING_ID

    def test_topic_length_limited(self, client):
        resp = client.post(
            "/api/reader/generate",
            json={"language_id": TEST_LANGUAGE_ID,
                  "language_code": "es", "topic": "x" * 500},
            headers=_auth_headers(),
        )
        assert resp.status_code == 422


class TestDeleteReading:
    """Shelf housekeeping (owner request): drop an old story, keep the words
    it taught. The endpoint's only job is ownership + the 404."""

    def test_requires_auth(self, client):
        resp = client.delete(f"/api/reader/readings/{TEST_READING_ID}")
        assert resp.status_code == 401

    def test_deletes_own_reading(self, client):
        with patch(
            "backend.routers.reader.delete_reading",
            new=AsyncMock(return_value=True),
        ) as mock_delete:
            resp = client.delete(
                f"/api/reader/readings/{TEST_READING_ID}",
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json() == {"deleted": True}
        # Scoped to the caller — the id alone is never enough.
        assert mock_delete.await_args.args[1] == TEST_USER_ID
        assert mock_delete.await_args.args[2] == TEST_READING_ID

    def test_someone_elses_reading_is_a_404(self, client):
        # The repo returns False for "not yours" AND "already gone"; both
        # become the same 404 so the endpoint leaks nothing about which.
        with patch(
            "backend.routers.reader.delete_reading",
            new=AsyncMock(return_value=False),
        ):
            resp = client.delete(
                f"/api/reader/readings/{TEST_READING_ID}",
                headers=_auth_headers(),
            )
        assert resp.status_code == 404

    def test_a_bad_id_never_reaches_the_repo(self, client):
        with patch(
            "backend.routers.reader.delete_reading", new=AsyncMock(),
        ) as mock_delete:
            resp = client.delete(
                "/api/reader/readings/not-a-uuid", headers=_auth_headers()
            )
        assert resp.status_code == 422
        mock_delete.assert_not_awaited()


class TestShelfEndpoints:
    def test_reading_404_when_not_owned(self, client):
        with patch(
            "backend.routers.reader.get_reading", new=AsyncMock(return_value=None),
        ):
            resp = client.get(
                f"/api/reader/readings/{TEST_READING_ID}",
                headers=_auth_headers(),
            )
        assert resp.status_code == 404

    def test_explain_uses_dev_mock(self, client):
        reading = {
            "id": TEST_READING_ID, "topic": "cats", "title": "t",
            "level": "A1", "created_at": "2026-07-16T00:00:00",
            "sentences": [{"text": "El gato duerme.",
                           "translation": "The cat sleeps.", "tokens": []}],
            "new_words": [], "structures": [],
        }
        lang_row = {"language_id": TEST_LANGUAGE_ID, "code": "es",
                    "tutor_model": None}

        async def fetchrow_side(sql, *args):
            # The same fake conn serves the language lookup AND the
            # allowance's tutor-access lookup — answer each by its SQL.
            if "FROM readings r JOIN languages" in sql:
                return lang_row
            return None  # no tutor_account_access row → default access

        client.fake_conn.fetchrow = AsyncMock(side_effect=fetchrow_side)
        with patch(
            "backend.routers.reader.get_reading",
            new=AsyncMock(return_value=reading),
        ), patch(
            "backend.routers.reader.log_tutor_usage", new=AsyncMock(),
        ):
            resp = client.post(
                f"/api/reader/readings/{TEST_READING_ID}/explain",
                json={"sentence_index": 0},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert "dev mock" in resp.json()["explanation"]

    def test_explain_rejects_bad_index(self, client):
        reading = {
            "id": TEST_READING_ID, "topic": "cats", "title": "t",
            "level": "A1", "created_at": "2026-07-16T00:00:00",
            "sentences": [{"text": "x", "translation": "", "tokens": []}],
            "new_words": [], "structures": [],
        }
        with patch(
            "backend.routers.reader.get_reading",
            new=AsyncMock(return_value=reading),
        ):
            resp = client.post(
                f"/api/reader/readings/{TEST_READING_ID}/explain",
                json={"sentence_index": 5},
                headers=_auth_headers(),
            )
        assert resp.status_code == 422


def test_system_prompt_honours_text_options():
    """Each per-text option maps to one explicit prompt rule; unknown values
    fall back to the defaults instead of leaking into the prompt."""
    from backend.services.reader import _system_prompt

    learner = {"level": "B1"}
    base = _system_prompt("es", "en", learner)
    assert "150–250" in base

    shaped = _system_prompt(
        "es", "en", learner,
        {"length": "short", "voice": "dialogue", "complexity": "stretch"},
    )
    assert "80–120" in shaped
    assert "DIALOGUE" in shaped
    # Stretch is a LEVEL SHIFT now, not a tone sentence: B1 learner →
    # text pitched at B2, cage opened (see test_level_rules.py for the
    # full dial matrix).
    assert "pitched at: B2" in shaped
    assert "FLOOR, not the limit" in shaped

    longer = _system_prompt("es", "en", learner, {"length": "long", "voice": "first"})
    assert "300–400" in longer and "FIRST person" in longer

    bogus = _system_prompt("es", "en", learner, {"length": "epic", "voice": "ghost"})
    assert "150–250" in bogus  # silently back to defaults


@pytest.mark.asyncio
async def test_generate_rejects_bad_option(client):
    resp = client.post(
        "/api/reader/generate",
        json={
            "language_id": TEST_LANGUAGE_ID,
            "language_code": "es",
            "topic": "cats",
            "length": "epic",
        },
        headers=_auth_headers(),
    )
    assert resp.status_code == 422


def test_generate_accepts_an_explicit_cefr_level(client):
    """The challenge dial's absolute half: A1–C2 are valid complexity
    values, anything else is still rejected."""
    with patch(
        "backend.routers.reader.save_reading",
        new=AsyncMock(return_value=TEST_READING_ID),
    ), patch(
        "backend.routers.reader.log_grammar_gaps", new=AsyncMock(return_value=0),
    ), patch(
        "backend.routers.reader.log_tutor_usage", new=AsyncMock(),
    ):
        resp = client.post(
            "/api/reader/generate",
            json={"language_id": TEST_LANGUAGE_ID, "language_code": "es",
                  "topic": "cats", "complexity": "B2"},
            headers=_auth_headers(),
        )
    assert resp.status_code == 200

    resp = client.post(
        "/api/reader/generate",
        json={"language_id": TEST_LANGUAGE_ID, "language_code": "es",
              "topic": "cats", "complexity": "Z9"},
        headers=_auth_headers(),
    )
    assert resp.status_code == 422


def test_system_prompt_carries_the_placement_result():
    """Owner: Read should have insight into test results. A reading text is
    the cheapest way to re-expose a structure someone got wrong."""
    from backend.services.reader import _system_prompt

    learner = {"level": "A1", "known_words": [], "learned_structures": []}
    assert "fell down at" not in _system_prompt("es", "en", learner)

    placed = {
        **learner,
        "placement": {
            "ceiling": "A2",
            "struggled_levels": ["B1"],
            "missed_structures": ["The subjunctive after querer"],
            "missed_words": ["aunque"],
        },
    }
    prompt = _system_prompt("es", "en", placed)
    assert "held A2" in prompt and "fell down at B1" in prompt
    assert "The subjunctive after querer" in prompt
    assert "aunque" in prompt


def test_placement_rule_stays_silent_without_evidence():
    """A placement that recorded only a level adds no instructions — an
    empty 'they missed: (none)' line is noise the model would still weigh."""
    from backend.services.reader import _placement_rule

    assert _placement_rule(None) == ""
    assert _placement_rule({"level": "B1", "struggled_levels": []}) == ""


def test_the_registers_sit_above_the_cefr_ladder():
    """Owner: "add more options — like a level higher than c2 — like
    university-level or academic".

    There is no C3, so the three additions are REGISTERS: the target stops
    being a rung and becomes a kind of prose, the cage is always open (no
    register above C2 fits inside a learner's cards), and each carries its
    own instruction. What this pins is that they are distinguishable — a
    dial where academic and literary produce the same prompt would be three
    chips and one behaviour.
    """
    from backend.services.reader import (
        BEYOND_CEFR,
        _system_prompt,
        pitch_label,
        resolve_dial,
    )

    assert set(BEYOND_CEFR) == {"native", "academic", "literary"}

    for mode in BEYOND_CEFR:
        target, open_cage = resolve_dial("B1", mode)
        assert target.startswith("C2+"), target
        # A register is above every learner by construction, so the cage
        # opens even for a C2 learner who picked it.
        assert open_cage is True
        assert resolve_dial("C2", mode)[1] is True

    learner = {"level": "B1"}
    academic = _system_prompt("es", "en", learner, {"complexity": "academic"})
    literary = _system_prompt("es", "en", learner, {"complexity": "literary"})
    native = _system_prompt("es", "en", learner, {"complexity": "native"})

    assert "university-level academic prose" in academic
    assert "nominalisation" in academic
    assert "literary prose" in literary and "nominalisation" not in literary
    assert "educated NATIVE" in native
    # The open cage still applies underneath the register.
    assert "FLOOR, not the limit" in academic

    # The shelf gets a short name, not the prompt's descriptive label.
    assert pitch_label("B1", "academic") == "Academic"
    assert pitch_label("B1", "stretch") == "B2"
    assert pitch_label("B1", "C1") == "C1"


def test_generate_accepts_a_register_above_c2(client):
    """The router's validation and the dial agree about what exists."""
    with patch(
        "backend.routers.reader.save_reading",
        new=AsyncMock(return_value=TEST_READING_ID),
    ), patch(
        "backend.routers.reader.log_grammar_gaps", new=AsyncMock(return_value=0),
    ), patch(
        "backend.routers.reader.log_tutor_usage", new=AsyncMock(),
    ):
        resp = client.post(
            "/api/reader/generate",
            json={"language_id": TEST_LANGUAGE_ID, "language_code": "es",
                  "topic": "quantum error correction",
                  "complexity": "academic"},
            headers=_auth_headers(),
        )
    assert resp.status_code == 200

    # A plausible-looking neighbour that does not exist is still a 422 —
    # the pattern is a whitelist, not a suggestion.
    resp = client.post(
        "/api/reader/generate",
        json={"language_id": TEST_LANGUAGE_ID, "language_code": "es",
              "topic": "cats", "complexity": "C3"},
        headers=_auth_headers(),
    )
    assert resp.status_code == 422
