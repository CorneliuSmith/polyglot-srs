"""Write tests — the handwriting reader and the endpoint flow.

The dev-mock path (tutor_dev_mock=True) exercises the whole round trip with
no API key, the same pattern as Speak.
"""

from __future__ import annotations

import io
import json
import time
from unittest.mock import AsyncMock, patch

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.repositories.write import habit_counts, readout
from backend.services.ink_method import compact, method_line, summarize_method
from backend.services.write_assess import (
    _system_prompt,
    assess_handwriting,
    normalize_assessment,
)
from backend.services.write_diff import misread_letters, same_text, units
from backend.tests.fakes import mock_conn

TEST_SECRET = "test-jwt-secret-for-unit-tests-32bytes"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
TEST_LANGUAGE_ID = "11111111-1111-1111-1111-111111111111"

# A 1×1 PNG plus padding past the "write something first" floor.
_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
) + b"\x00" * 120


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
    tutor_summary_model = "claude-haiku-4-5-20251001"
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
# The reader's brief and its output
# ---------------------------------------------------------------------------


class TestSystemPrompt:
    def test_transcribes_before_it_judges_and_never_corrects_toward_expected(self):
        prompt = _system_prompt("Russian", None, None)
        # The transcription is the calibration: a learner must be able to
        # see a misread as a misread.
        assert "First transcribe" in prompt
        assert "Never 'correct' the transcription" in prompt

    def test_cursive_is_judged_as_cursive(self):
        prompt = _system_prompt("Russian", None, "cursive")
        assert "joined cursive" in prompt
        assert "not as deviations from print" in prompt

    def test_notes_are_written_in_the_support_language(self):
        assert "Write every note in French" in _system_prompt("Arabic", "French", None)
        assert "Write every note in English" in _system_prompt("Arabic", None, None)


class TestNormalize:
    def test_clamps_and_defaults_malformed_fields(self):
        out = normalize_assessment({
            "transcription": " Я иду ",
            "legibility": 9,
            "confidence": "certain",
            "word_diffs": [{"expected": "домой", "written": "домои", "note": "й"}],
            "letterform_notes": [
                {"letter": "д", "note": "open"}, {"letter": "м", "note": "hook"},
                {"letter": "о", "note": "third is dropped"},
                {"letter": "х", "note": ""},
            ],
        })
        assert out["transcription"] == "Я иду"
        assert out["legibility"] == 5
        assert out["confidence"] == "low"
        # No boolean given: "matches" follows the diffs.
        assert out["matches_target"] is False
        assert len(out["letterform_notes"]) == 2

    def test_nothing_read_is_never_correct_or_confident(self):
        out = normalize_assessment({
            "transcription": "", "matches_target": True, "confidence": "high",
            "legibility": 5, "word_diffs": [], "letterform_notes": [],
        })
        assert out["matches_target"] is False
        assert out["confidence"] == "low"


@pytest.mark.asyncio
class TestAssess:
    async def test_dev_mock_reads_back_the_expected_text(self):
        with patch("backend.services.write_assess.get_settings",
                   return_value=FakeSettings()):
            result, usage = await assess_handwriting(_PNG, "Russian", "Я иду домой")
        assert result["transcription"] == "Я иду домой"
        assert result["matches_target"] is True
        assert result["letterform_notes"], "the notes UI must have something to show"
        assert usage["input_tokens"] > 0

    async def test_the_image_and_the_expected_text_reach_the_model(self):
        class Block:
            type = "tool_use"
            input = {
                "transcription": "Я иду домой", "matches_target": True,
                "word_diffs": [], "legibility": 4, "letterform_notes": [],
                "confidence": "high",
            }

        class FakeResponse:
            content = [Block()]
            usage = None

        settings = FakeSettings()
        settings.tutor_dev_mock = False
        settings.anthropic_api_key = "sk-test"
        with patch("backend.services.write_assess.get_settings",
                   return_value=settings), \
             patch("backend.services.write_assess.AsyncAnthropic") as client_cls:
            create = AsyncMock(return_value=FakeResponse())
            client_cls.return_value.messages.create = create
            result, _ = await assess_handwriting(
                _PNG, "Russian", "Я иду домой", support_language="French",
                style="cursive", model="claude-sonnet-5",
            )
        kwargs = create.await_args.kwargs
        content = kwargs["messages"][0]["content"]
        assert content[0]["type"] == "image"
        assert content[0]["source"]["media_type"] == "image/png"
        assert "Я иду домой" in content[1]["text"]
        assert kwargs["tool_choice"]["name"] == "emit_assessment"
        # The notes' language is named in the schema too, not only the
        # prompt — a diff in Spanish beside notes in English was the result
        # of naming it once.
        assert "French" in json.dumps(kwargs["tools"][0])
        assert result["legibility"] == 4

    async def test_no_payload_is_an_error_not_a_verdict(self):
        class FakeResponse:
            content = []
            usage = None

        settings = FakeSettings()
        settings.tutor_dev_mock = False
        settings.anthropic_api_key = "sk-test"
        with patch("backend.services.write_assess.get_settings",
                   return_value=settings), \
             patch("backend.services.write_assess.AsyncAnthropic") as client_cls:
            client_cls.return_value.messages.create = AsyncMock(
                return_value=FakeResponse())
            with pytest.raises(ValueError):
                await assess_handwriting(_PNG, "Russian", "x")


class TestMethod:
    """How the ink was made, from the strokes alone."""

    def _bar(self, x, top=0, h=40, t0=0, n=10):
        return [{"x": x, "y": top + h * i / (n - 1), "t": t0 + i * 20} for i in range(n)]

    def test_three_lifted_strokes_running_down(self):
        st = [self._bar(10), self._bar(40, t0=300), self._bar(70, t0=600)]
        m = summarize_method(st)
        assert m["strokes"] == 3 and m["lifts"] == 2
        assert m["dominant_direction"] == "down"
        assert m["joined_runs"] == 0
        assert m["duration_ms"] == 780
        line = method_line(m)
        assert "3 strokes" in line and "lifted" in line and "down" in line

    def test_one_long_run_is_joined_writing(self):
        # A single stroke sweeping left across several letters' worth.
        run = [{"x": 300 - i * 10, "y": 20 + (i % 3) * 5, "t": i * 15} for i in range(40)]
        m = summarize_method([run, self._bar(320, t0=1000)])
        assert m["joined_runs"] == 1
        assert m["reads_right_to_left"] is True
        assert "without lifting" in method_line(m)

    def test_compact_resamples_and_drops_taps(self):
        long = [{"x": i, "y": i, "t": i} for i in range(500)]
        st = compact([long, [{"x": 1, "y": 1}], "garbage", [[3, 4, 5], [6, 7, 8]]])
        assert len(st) == 2
        assert len(st[0]) == 64 and st[0][0] == [0, 0, 0] and st[0][-1] == [499, 499, 499]
        assert st[1] == [[3, 4, 5], [6, 7, 8]]

    def test_nothing_from_nothing(self):
        assert summarize_method(None) == {} and method_line({}) == ""


@pytest.mark.asyncio
class TestReferences:
    async def test_the_writers_samples_and_known_forms_reach_the_reader(self):
        class Block:
            type = "tool_use"
            input = {"transcription": "أن", "matches_target": True, "word_diffs": [],
                     "legibility": 4, "letterform_notes": [], "confidence": "high"}

        class FakeResponse:
            content = [Block()]
            usage = None

        settings = FakeSettings()
        settings.tutor_dev_mock = False
        settings.anthropic_api_key = "sk-test"
        with patch("backend.services.write_assess.get_settings",
                   return_value=settings), \
             patch("backend.services.write_assess.AsyncAnthropic") as client_cls:
            create = AsyncMock(return_value=FakeResponse())
            client_cls.return_value.messages.create = create
            await assess_handwriting(
                _PNG, "Arabic", "أن",
                references=[{"text": "أنا", "image": _PNG,
                             "method": {"strokes": 3, "lifts": 2, "duration_ms": 900}}],
                known=["أ — hamza drawn as its own stroke, up and right of the alif"],
                method={"strokes": 3, "lifts": 2, "dominant_direction": "down",
                        "duration_ms": 1200},
            )
        kwargs = create.await_args.kwargs
        content = kwargs["messages"][0]["content"]
        images = [c for c in content if c["type"] == "image"]
        texts = [c["text"] for c in content if c["type"] == "text"]
        # The reference comes first, labelled with what it reads and how
        # it was made; the canvas comes last with its own method.
        assert len(images) == 2
        assert texts[0].startswith("Reference:") and "أنا" in texts[0] and "3 strokes" in texts[0]
        assert "Now the canvas" in texts[1] and "How it was made" in texts[1]
        assert "Known forms of THIS writer" in kwargs["system"]
        assert "hamza" in kwargs["system"]

    async def test_without_a_profile_the_call_is_phase_one(self):
        class FakeResponse:
            content = []
            usage = None

        settings = FakeSettings()
        settings.tutor_dev_mock = False
        settings.anthropic_api_key = "sk-test"
        with patch("backend.services.write_assess.get_settings",
                   return_value=settings), \
             patch("backend.services.write_assess.AsyncAnthropic") as client_cls:
            create = AsyncMock(return_value=FakeResponse())
            client_cls.return_value.messages.create = create
            with pytest.raises(ValueError):
                await assess_handwriting(_PNG, "Arabic", "أن")
        content = create.await_args.kwargs["messages"][0]["content"]
        assert [c["type"] for c in content] == ["image", "text"]
        assert "Known forms" not in create.await_args.kwargs["system"]


class TestMisread:
    """The writer's verdict, letter by letter — the ground truth (§12.1)."""

    def test_names_the_letter_the_reader_got_wrong(self):
        assert misread_letters("ين", "أن") == [{"wrote": "أ", "read": "ي"}]
        assert misread_letters("Я иду домои", "Я иду домой") == [{"wrote": "й", "read": "и"}]

    def test_marks_are_part_of_their_letter(self):
        # A hamza on an alif is one unit, so "alif without hamza" is one
        # misread, not a missing mark.
        assert units("أنا") == ["أ", "ن", "ا"]
        assert misread_letters("انا", "أنا") == [{"wrote": "أ", "read": "ا"}]

    def test_missed_and_invented_letters(self):
        assert misread_letters("لي", "أنا") == [
            {"wrote": "أ", "read": "ل"}, {"wrote": "ن", "read": "ي"}, {"wrote": "ا", "read": ""}]
        assert misread_letters("che", "de") == [{"wrote": "d", "read": "c"}, {"wrote": "", "read": "h"}]

    def test_same_text_ignores_spacing(self):
        assert same_text("Я иду домой", "Я  иду домой ")
        assert not same_text("Я иду домой", "Я иду домои")
        assert misread_letters("привет", "привет") == []


class TestReadout:
    def test_letters_to_watch_are_the_most_misread(self):
        r = readout({"right": 3, "wrong": 2,
                     "misread_letters": {"أ": 3, "ن": 1, "د": 2, "е": 1, "м": 1, "о": 1},
                     "legibility_mean": 3.4, "history": [3, 4]})
        assert r["total"] == 5 and r["right"] == 3
        # Most misread first; ties broken by code point so the list is stable.
        assert [x["letter"] for x in r["letters_to_watch"]] == ["أ", "د", "е", "м", "о"]
        assert r["history"] == [3, 4]
        assert readout({}) == {"right": 0, "wrong": 0, "total": 0, "letters_to_watch": [],
                               "legibility_mean": None, "history": []}

    def test_habit_counts_only_repeat_offenders(self):
        habits = [{"letter": "д", "count": 3}, {"letter": "е", "count": 1}]
        assert habit_counts(habits, ["д", "е", "х"]) == {"д": 3}


class TestDiffWords:
    def test_the_models_asides_are_stripped_from_diff_words(self):
        out = normalize_assessment({
            "transcription": "ين", "matches_target": False, "legibility": 2,
            "confidence": "low", "letterform_notes": [],
            "word_diffs": [{"expected": "أن", "written": "(approx) ين", "note": "x"}],
        })
        assert out["word_diffs"][0]["written"] == "ين"
        # ...but a word that is nothing but an aside is left alone.
        out = normalize_assessment({
            "transcription": "x", "word_diffs": [{"expected": "a", "written": "(unclear)", "note": ""}],
        })
        assert out["word_diffs"][0]["written"] == "(unclear)"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


def _conn() -> AsyncMock:
    conn = mock_conn()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchval = AsyncMock(return_value=None)
    conn.execute = AsyncMock()

    async def fetchrow(sql, *args):
        if "FROM languages" in sql:
            return {"name": "Russian", "code": "ru", "tutor_model": None}
        return None

    conn.fetchrow = AsyncMock(side_effect=fetchrow)
    return conn


def _conn_with_hand_tables() -> AsyncMock:
    """The 20261019 tables present: to_regclass answers, the toggle row is
    absent (= on), one sample is kept."""
    conn = _conn()

    async def fetchval(sql, *args):
        if "to_regclass" in sql:
            return True
        if "count(*)" in sql:
            return 1
        return None

    conn.fetchval = AsyncMock(side_effect=fetchval)

    async def fetchrow(sql, *args):
        if "FROM languages" in sql:
            return {"name": "Arabic", "code": "ar", "tutor_model": None}
        if "count(*) AS n" in sql:
            return {"n": 1, "c": 1}
        return None

    conn.fetchrow = AsyncMock(side_effect=fetchrow)
    return conn


@pytest.fixture(params=["bare", "hand"])
def client(request):
    from contextlib import asynccontextmanager

    conn = _conn() if request.param == "bare" else _conn_with_hand_tables()

    @asynccontextmanager
    async def fake_conn(*args):
        yield conn

    with patch("backend.main.init_pool", new=AsyncMock()), \
         patch("backend.main.close_pool", new=AsyncMock()), \
         patch("backend.main.get_settings", return_value=FakeSettings()), \
         patch("backend.dependencies.get_settings", return_value=FakeSettings()), \
         patch("backend.routers.tutor.get_settings", return_value=FakeSettings()), \
         patch("backend.services.generate.get_settings",
               return_value=FakeSettings()), \
         patch("backend.services.write_assess.get_settings",
               return_value=FakeSettings()), \
         patch("backend.routers.write.rls_connection", fake_conn), \
         patch("backend.services.allowance.get_settings",
               return_value=FakeSettings()), \
         patch("backend.services.allowance.rls_connection", fake_conn), \
         patch("backend.routers.tutor.rls_connection", fake_conn):
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as c:
            c.fake_conn = conn
            c.hand = request.param == "hand"
            yield c


def _post(client, data: bytes = _PNG, content_type: str = "image/png", **form):
    return client.post(
        "/api/write/assess", headers=_auth_headers(),
        files={"image": ("ink.png", io.BytesIO(data), content_type)},
        data={"language_id": TEST_LANGUAGE_ID, **form},
    )


class TestWriteEndpoints:
    def test_requires_auth(self, client):
        assert client.get(
            f"/api/write/status?language_id={TEST_LANGUAGE_ID}"
        ).status_code == 401

    def test_status_reports_availability_and_the_meter(self, client):
        resp = client.get(
            f"/api/write/status?language_id={TEST_LANGUAGE_ID}",
            headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json()["available"] is True
        assert resp.json()["allowance"]["unlimited"] is True

    def test_prompts_rejects_an_unknown_kind(self, client):
        resp = client.get(
            f"/api/write/prompts?language_id={TEST_LANGUAGE_ID}&kind=poem",
            headers=_auth_headers())
        assert resp.status_code == 422

    def test_prompts_returns_the_repository_rows(self, client):
        rows = [{"prompt": "I am going home.", "answer": "Я иду домой",
                 "source": "own"}]
        with patch("backend.routers.write.sentence_prompts",
                   new=AsyncMock(return_value=rows)):
            resp = client.get(
                f"/api/write/prompts?language_id={TEST_LANGUAGE_ID}",
                headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json() == {"kind": "sentence", "items": rows}

    def test_an_assessment_reads_the_ink_logs_usage_and_returns_the_meter(self, client):
        resp = _post(client, expected="  Я иду домой ", style="cursive")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["transcription"] == "Я иду домой"
        assert body["matches_target"] is True
        assert body["expected"] == "Я иду домой"
        assert body["allowance"]["unlimited"] is True
        # One assessment is one message on the allowance, kind='write'.
        inserts = [c.args for c in client.fake_conn.execute.await_args_list
                   if "INSERT INTO tutor_usage" in c.args[0]]
        assert len(inserts) == 1 and inserts[0][4] == "write"

    def test_free_writing_needs_no_expected_text(self, client):
        resp = _post(client, kind="free")
        assert resp.status_code == 200
        assert resp.json()["expected"] is None

    def test_a_photo_sized_upload_is_refused(self, client):
        resp = _post(client, data=b"\x89PNG" + b"\x00" * 1_600_000)
        assert resp.status_code == 413

    def test_an_empty_canvas_is_refused_before_it_costs_anything(self, client):
        resp = _post(client, data=b"\x89PNG\r\n")
        assert resp.status_code == 422
        assert not [c for c in client.fake_conn.execute.await_args_list
                    if "INSERT INTO tutor_usage" in c.args[0]]

    def test_only_images_are_accepted(self, client):
        assert _post(client, content_type="application/pdf").status_code == 422

    def test_an_unknown_style_is_rejected(self, client):
        assert _post(client, style="gothic").status_code == 422

    def test_a_blocked_account_is_refused(self, client):
        blocked = {"tier": "blocked", "unlimited": False, "entitled": False,
                   "limit": 0, "used": 0, "remaining": 0, "resets_at": None}
        with patch("backend.routers.write._get_allowance",
                   new=AsyncMock(return_value=blocked)):
            resp = _post(client, expected="x")
        assert resp.status_code in (402, 403, 429), resp.text

    def test_the_ink_is_stored_only_as_the_writers_sample(self, client):
        """The attempt log keeps the verdict, never the handwriting — the
        rule Speak follows for audio. The ONE place ink goes is the
        writer's own sample table, and only with their toggle on (which the
        tables being present implies, since no row means on)."""
        _post(client, expected="Я иду домой")
        for call in client.fake_conn.execute.await_args_list:
            has_bytes = any(isinstance(a, (bytes, bytearray)) for a in call.args[1:])
            if has_bytes:
                assert client.hand and "INSERT INTO writing_samples" in call.args[0]
        if not client.hand:
            assert not _executed(client, "INSERT INTO writing_samples")


def _executed(client, needle: str) -> list:
    return [c.args for c in client.fake_conn.execute.await_args_list
            if needle in c.args[0]]


class TestHandProfile:
    def test_profile_says_whether_the_tables_exist(self, client):
        resp = client.get(
            f"/api/write/profile?language_id={TEST_LANGUAGE_ID}",
            headers=_auth_headers())
        assert resp.status_code == 200
        body = resp.json()
        assert body["available"] is client.hand
        assert body["adapt"] is client.hand   # on by default once the tables exist
        if client.hand:
            assert body["samples"] == 1 and body["confirmed"] == 1

    def test_confirm_keeps_the_sample_with_its_method_and_marks_the_forms_fine(self, client):
        strokes = json.dumps([[[10, 0, 0], [10, 40, 200]], [[40, 0, 300], [40, 40, 500]],
                              [[70, 0, 600], [70, 40, 800]]])
        resp = client.post(
            "/api/write/confirm", headers=_auth_headers(),
            files={"image": ("ink.png", io.BytesIO(_PNG), "image/png")},
            data={"language_id": TEST_LANGUAGE_ID, "text": " أن ", "letters": "أ, ن",
                  "strokes": strokes},
        )
        assert resp.status_code == 200, resp.text
        if not client.hand:
            assert resp.json() == {"kept": False, "reason": "adapt_off", "samples": 0}
            assert not _executed(client, "INSERT INTO writing_samples")
            return
        assert resp.json()["kept"] is True and resp.json()["samples"] == 1
        inserts = _executed(client, "INSERT INTO writing_samples")
        assert len(inserts) == 1
        args = inserts[0]
        assert args[3] == "أن" and args[4] == _PNG and args[7] is True
        # The method rides along: the strokes, compacted, and their summary.
        assert json.loads(args[5])[0][0] == [10, 0, 0]
        assert json.loads(args[6])["strokes"] == 3
        # ...and the flagged letters become known-fine habits.
        profiles = _executed(client, "INSERT INTO writing_profiles")
        assert len(profiles) == 1
        habits = json.loads(profiles[0][3])
        assert {h["letter"] for h in habits} == {"أ", "ن"}
        assert all(h["confirmed_ok"] for h in habits)

    def test_confirm_records_the_writers_verdict(self, client):
        """No + correction: the misread letters count against the letters
        the writer actually wrote, and the readout says N of M."""
        resp = client.post(
            "/api/write/confirm", headers=_auth_headers(),
            files={"image": ("ink.png", io.BytesIO(_PNG), "image/png")},
            data={"language_id": TEST_LANGUAGE_ID, "text": "أنا", "read": "لي"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        if not client.hand:
            assert "right" not in body
            return
        assert body["right"] is False
        assert [m["wrote"] for m in body["misread"]] == ["أ", "ن", "ا"]
        assert body["readout"]["wrong"] == 1 and body["readout"]["total"] == 1
        assert [x["letter"] for x in body["readout"]["letters_to_watch"]] == ["أ", "ا", "ن"]
        # Yes on a reading that matched: a right read, nothing misread.
        resp = client.post(
            "/api/write/confirm", headers=_auth_headers(),
            files={"image": ("ink.png", io.BytesIO(_PNG), "image/png")},
            data={"language_id": TEST_LANGUAGE_ID, "text": "أنا", "read": "أنا"},
        )
        assert resp.json()["right"] is True and resp.json()["misread"] == []

    def test_a_sure_matching_check_counts_as_a_right_read_and_repeats_are_counted(self, client):
        with patch("backend.routers.write.assess_handwriting",
                   new=AsyncMock(return_value=({
                       "transcription": "أن", "matches_target": True, "word_diffs": [],
                       "legibility": 4, "letterform_notes": [{"letter": "أ", "note": "n"}],
                       "confidence": "high"}, {}))), \
             patch("backend.routers.write.hand_profile",
                   new=AsyncMock(return_value={
                       "habits": [{"letter": "أ", "count": 2, "confirmed_ok": False}],
                       "adapt": True, "available": True, "stats": {}, "samples": 0,
                       "confirmed": 0, "readout": readout({})})):
            resp = _post(client, expected="أن")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        if client.hand:
            assert body["again"] == {"أ": 2}
            profiles = _executed(client, "INSERT INTO writing_profiles")
            # note_habits, then record_verdict — the last save carries right = 1.
            assert json.loads(profiles[-1][4])["right"] == 1
        else:
            assert body["again"] == {}

    def test_confirm_needs_text(self, client):
        resp = client.post(
            "/api/write/confirm", headers=_auth_headers(),
            files={"image": ("ink.png", io.BytesIO(_PNG), "image/png")},
            data={"language_id": TEST_LANGUAGE_ID, "text": "  "},
        )
        assert resp.status_code == 422

    def test_a_check_with_the_toggle_on_shows_the_reader_the_writers_hand(self, client):
        refs = [{"text": "أنا", "image": _PNG, "method": {"strokes": 2, "lifts": 1, "duration_ms": 500}}]
        with patch("backend.routers.write.reference_samples",
                   new=AsyncMock(return_value=refs)) as ref_fn, \
             patch("backend.routers.write.assess_handwriting",
                   new=AsyncMock(return_value=({
                       "transcription": "أن", "matches_target": True, "word_diffs": [],
                       "legibility": 4, "letterform_notes": [{"letter": "أ", "note": "n"}],
                       "confidence": "high"}, {}))) as assess_fn:
            resp = _post(client, expected="أن",
                         strokes=json.dumps([[[0, 0, 0], [0, 30, 100]]]))
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["adapt"] is client.hand
        kwargs = assess_fn.await_args.kwargs
        if client.hand:
            ref_fn.assert_awaited_once()
            assert kwargs["references"] == refs
            assert kwargs["method"]["strokes"] == 1
            # A sure, matching read is kept as an (unconfirmed) sample, and
            # the note counts against its letter.
            kept = _executed(client, "INSERT INTO writing_samples")
            assert len(kept) == 1 and kept[0][7] is False
            assert _executed(client, "INSERT INTO writing_profiles")
        else:
            ref_fn.assert_not_awaited()
            assert kwargs["references"] == []
            assert not _executed(client, "INSERT INTO writing_samples")

    def test_turning_the_toggle_off_deletes_everything(self, client):
        resp = client.put("/api/write/profile", headers=_auth_headers(),
                          json={"adapt": False})
        assert resp.status_code == 200 and resp.json() == {"adapt": False}
        deletes = _executed(client, "DELETE FROM writing_samples")
        if client.hand:
            assert _executed(client, "INSERT INTO writing_settings")
            assert deletes and "language_id" not in deletes[0][0]
        else:
            assert not deletes

    def test_reset_forgets_one_language_or_all(self, client):
        client.post("/api/write/profile/reset", headers=_auth_headers(),
                    json={"language_id": TEST_LANGUAGE_ID})
        client.post("/api/write/profile/reset", headers=_auth_headers(), json={})
        deletes = _executed(client, "DELETE FROM writing_samples")
        if client.hand:
            assert len(deletes) == 2
            assert "language_id" in deletes[0][0] and "language_id" not in deletes[1][0]
        else:
            assert not deletes


class TestAdminHandwriting:
    def test_requires_admin(self, client):
        with patch("backend.routers.contribute._require_admin",
                   new=AsyncMock(side_effect=__import__("fastapi").HTTPException(403))):
            resp = client.get("/api/contribute/analytics/handwriting", headers=_auth_headers())
        assert resp.status_code == 403

    def test_aggregates_per_language(self, client):
        rows = [{"code": "ar", "language": "Arabic", "writers": 2, "right": 6, "wrong": 2,
                 "accuracy": 0.75, "legibility_mean": 3.2,
                 "letters_to_watch": [{"letter": "أ", "count": 3}]}]
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def fake_priv(*a, **k):
            yield client.fake_conn

        with patch("backend.routers.contribute._require_admin", new=AsyncMock()), \
             patch("backend.routers.contribute.privileged_connection", fake_priv), \
             patch("backend.repositories.write.admin_hand_accuracy",
                   new=AsyncMock(return_value=rows)):
            resp = client.get("/api/contribute/analytics/handwriting", headers=_auth_headers())
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"languages": rows}
