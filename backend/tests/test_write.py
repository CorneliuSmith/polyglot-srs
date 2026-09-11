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
from backend.services.write_assess import (
    _system_prompt,
    assess_handwriting,
    normalize_assessment,
)
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


@pytest.fixture()
def client():
    from contextlib import asynccontextmanager

    conn = _conn()

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

    def test_the_ink_is_never_stored(self, client):
        """The log keeps the verdict, not the handwriting — the same rule
        Speak follows for audio."""
        _post(client, expected="Я иду домой")
        for call in client.fake_conn.execute.await_args_list:
            for arg in call.args[1:]:
                assert not (isinstance(arg, (bytes, bytearray)))
