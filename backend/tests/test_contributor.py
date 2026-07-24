"""Tests for contributor roles and the grammar authoring/approval API."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.repositories.contributor import can_contribute, is_admin

TEST_SECRET = "test-jwt-secret-for-unit-tests-32bytes"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
LANG = "11111111-1111-1111-1111-111111111111"
OTHER_LANG = "99999999-9999-9999-9999-999999999999"
POINT = "22222222-2222-2222-2222-222222222222"


# ── pure role logic ────────────────────────────────────────────────────────

class TestRoleLogic:
    def test_admin_can_contribute_any_language(self):
        roles = [{"language_id": None, "role": "admin"}]
        assert is_admin(roles)
        assert can_contribute(roles, LANG)

    def test_contributor_scoped_to_language(self):
        roles = [{"language_id": LANG, "role": "contributor"}]
        assert not is_admin(roles)
        assert can_contribute(roles, LANG)
        assert not can_contribute(roles, OTHER_LANG)

    def test_global_contributor(self):
        roles = [{"language_id": None, "role": "contributor"}]
        assert can_contribute(roles, OTHER_LANG)

    def test_no_roles(self):
        assert not can_contribute([], LANG)


# ── endpoint gating ─────────────────────────────────────────────────────────

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


@asynccontextmanager
async def _fake_priv():
    yield AsyncMock()


@pytest.fixture()
def client():
    with patch("backend.main.init_pool", new=AsyncMock()), \
         patch("backend.main.close_pool", new=AsyncMock()), \
         patch("backend.main.get_settings", return_value=FakeSettings()), \
         patch("backend.dependencies.get_settings", return_value=FakeSettings()), \
         patch("backend.routers.contribute.rls_connection", _fake_rls), \
         patch("backend.routers.contribute.privileged_connection", _fake_priv):
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


def _roles(roles):
    return patch("backend.routers.contribute.get_roles", new=AsyncMock(return_value=roles))


class TestContributeEndpoints:
    def test_roles_endpoint(self, client):
        with _roles([{"language_id": LANG, "role": "contributor"}]):
            resp = client.get("/api/contribute/roles", headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json()["is_admin"] is False
        assert len(resp.json()["roles"]) == 1

    def test_list_grammar_requires_role(self, client):
        with _roles([]):
            resp = client.get(
                "/api/contribute/grammar", params={"language_id": LANG},
                headers=_auth_headers(),
            )
        assert resp.status_code == 403

    def test_list_grammar_with_role(self, client):
        with _roles([{"language_id": LANG, "role": "contributor"}]), \
             patch("backend.routers.contribute.list_grammar_points",
                   new=AsyncMock(return_value=[{"id": POINT, "title": "Locative"}])), \
             patch("backend.routers.contribute.get_language_policy",
                   new=AsyncMock(return_value="strict")), \
             patch("backend.routers.contribute.get_language_tutor_model",
                   new=AsyncMock(return_value=None)):
            resp = client.get(
                "/api/contribute/grammar", params={"language_id": LANG},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json()["points"][0]["title"] == "Locative"

    def test_list_vocab_requires_role(self, client):
        with _roles([]):
            resp = client.get(
                "/api/contribute/vocab", params={"language_id": LANG},
                headers=_auth_headers(),
            )
        assert resp.status_code == 403

    def test_list_vocab_with_role(self, client):
        with _roles([{"language_id": LANG, "role": "reviewer"}]), \
             patch("backend.routers.contribute.list_vocab_items",
                   new=AsyncMock(return_value=[
                       {"id": POINT, "word": "hola", "definition": "hi",
                        "level": "A1", "example_count": 2}
                   ])):
            resp = client.get(
                "/api/contribute/vocab", params={"language_id": LANG},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json()["items"][0]["word"] == "hola"

    def test_update_grammar_gated_by_point_language(self, client):
        # contributor for OTHER_LANG editing a LANG point -> 403
        with _roles([{"language_id": OTHER_LANG, "role": "contributor"}]), \
             patch("backend.routers.contribute.get_point_language",
                   new=AsyncMock(return_value=LANG)):
            resp = client.put(
                f"/api/contribute/grammar/{POINT}",
                json={"explanation": "X"}, headers=_auth_headers(),
            )
        assert resp.status_code == 403

    def test_update_grammar_saves_pending(self, client):
        with _roles([{"language_id": LANG, "role": "contributor"}]), \
             patch("backend.routers.contribute.get_point_language",
                   new=AsyncMock(return_value=LANG)), \
             patch("backend.routers.contribute.save_explanation",
                   new=AsyncMock(return_value=True)) as mock_save:
            resp = client.put(
                f"/api/contribute/grammar/{POINT}",
                json={
                    "explanation": "The locative marks location.",
                    "references": [{"title": "Wiktionary", "url": "https://en.wiktionary.org/wiki/-de"}],
                },
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json() == {"saved": True, "reviewed": False}
        mock_save.assert_awaited_once()
        # references flow through to the repository layer
        assert mock_save.await_args.kwargs["references"][0]["url"].startswith("https://")

    def test_update_missing_point_404(self, client):
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.get_point_language",
                   new=AsyncMock(return_value=None)):
            resp = client.put(
                f"/api/contribute/grammar/{POINT}",
                json={"explanation": "X"}, headers=_auth_headers(),
            )
        assert resp.status_code == 404

    def test_approve_denied_to_contributor(self, client):
        # contributors draft; they don't hold the human approval gate
        with _roles([{"language_id": LANG, "role": "contributor"}]), \
             patch("backend.routers.contribute.get_point_language",
                   new=AsyncMock(return_value=LANG)):
            resp = client.post(
                f"/api/contribute/grammar/{POINT}/approve", headers=_auth_headers()
            )
        assert resp.status_code == 403

    def test_approve_as_reviewer_for_language(self, client):
        with _roles([{"language_id": LANG, "role": "reviewer"}]), \
             patch("backend.routers.contribute.get_point_language",
                   new=AsyncMock(return_value=LANG)), \
             patch("backend.routers.contribute.approve_explanation",
                   new=AsyncMock(return_value=True)):
            resp = client.post(
                f"/api/contribute/grammar/{POINT}/approve", headers=_auth_headers()
            )
        assert resp.status_code == 200
        assert resp.json() == {"approved": True}

    def test_approve_denied_to_reviewer_of_other_language(self, client):
        with _roles([{"language_id": OTHER_LANG, "role": "reviewer"}]), \
             patch("backend.routers.contribute.get_point_language",
                   new=AsyncMock(return_value=LANG)):
            resp = client.post(
                f"/api/contribute/grammar/{POINT}/approve", headers=_auth_headers()
            )
        assert resp.status_code == 403

    def test_approve_as_admin_records_reviewer(self, client):
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.get_point_language",
                   new=AsyncMock(return_value=LANG)), \
             patch("backend.routers.contribute.approve_explanation",
                   new=AsyncMock(return_value=True)) as mock_approve:
            resp = client.post(
                f"/api/contribute/grammar/{POINT}/approve", headers=_auth_headers()
            )
        assert resp.status_code == 200
        assert resp.json() == {"approved": True}
        # reviewer id is passed through to be stamped in the DB
        assert mock_approve.await_args.args[2] == TEST_USER_ID


class TestAiCheck:
    def test_requires_role(self, client):
        with _roles([]), \
             patch("backend.routers.contribute.ai_available", return_value=True), \
             patch("backend.routers.contribute.get_point_language_and_code",
                   new=AsyncMock(return_value=(LANG, "tr"))):
            resp = client.post(
                f"/api/contribute/grammar/{POINT}/ai-check", headers=_auth_headers()
            )
        assert resp.status_code == 403

    def test_runs_and_stores_verdict(self, client):
        verdict = {"status": "concerns", "notes": "Drill 2 answer should be 'evde'."}
        with _roles([{"language_id": LANG, "role": "contributor"}]), \
             patch("backend.routers.contribute.ai_available", return_value=True), \
             patch("backend.routers.contribute.get_point_language_and_code",
                   new=AsyncMock(return_value=(LANG, "tr"))), \
             patch("backend.routers.contribute.get_point_for_check",
                   new=AsyncMock(return_value={
                       "title": "Locative", "explanation": "...",
                       "language_code": "tr", "drills": [],
                   })), \
             patch("backend.routers.contribute.semantic_check_point",
                   new=AsyncMock(return_value=verdict)), \
             patch("backend.routers.contribute.save_ai_check",
                   new=AsyncMock()) as mock_save:
            resp = client.post(
                f"/api/contribute/grammar/{POINT}/ai-check", headers=_auth_headers()
            )
        assert resp.status_code == 200
        assert resp.json() == verdict
        mock_save.assert_awaited_once()

    def test_unconfigured_503(self, client):
        with patch("backend.routers.contribute.ai_available", return_value=False):
            resp = client.post(
                f"/api/contribute/grammar/{POINT}/ai-check", headers=_auth_headers()
            )
        assert resp.status_code == 503

    def test_rate_limited_429(self, client):
        from backend.services.rate_limit import ai_review_limiter
        with patch("backend.routers.contribute.ai_available", return_value=True), \
             patch.object(ai_review_limiter, "allow", new=AsyncMock(return_value=False)):
            resp = client.post(
                f"/api/contribute/grammar/{POINT}/ai-check", headers=_auth_headers()
            )
        assert resp.status_code == 429

    def test_grant_role_requires_admin(self, client):
        with _roles([{"language_id": LANG, "role": "contributor"}]):
            resp = client.post(
                "/api/contribute/roles",
                json={"user_id": "u", "role": "contributor"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 403

    def test_grant_role_as_admin(self, client):
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.grant_role", new=AsyncMock()) as mock_grant:
            resp = client.post(
                "/api/contribute/roles",
                json={"user_id": "u", "language_id": LANG, "role": "reviewer"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        mock_grant.assert_awaited_once()

    def test_grant_role_by_email(self, client):
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.find_user_by_email",
                   new=AsyncMock(return_value="resolved-id")), \
             patch("backend.routers.contribute.grant_role", new=AsyncMock()) as mock_grant:
            resp = client.post(
                "/api/contribute/roles",
                json={"email": "linguist@example.com", "role": "reviewer"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json()["user_id"] == "resolved-id"
        assert mock_grant.await_args.args[1] == "resolved-id"

    def test_grant_role_unknown_email_404(self, client):
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.find_user_by_email",
                   new=AsyncMock(return_value=None)):
            resp = client.post(
                "/api/contribute/roles",
                json={"email": "ghost@example.com", "role": "contributor"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 404

    def test_grant_invalid_role_422(self, client):
        with _roles([{"language_id": None, "role": "admin"}]):
            resp = client.post(
                "/api/contribute/roles",
                json={"user_id": "u", "role": "superuser"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 422

    def test_revoke_role(self, client):
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.revoke_role",
                   new=AsyncMock(return_value=True)) as mock_revoke:
            resp = client.post(
                "/api/contribute/roles/revoke",
                json={"user_id": "u", "language_id": LANG, "role": "contributor"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json()["revoked"] is True
        mock_revoke.assert_awaited_once()

    def test_list_all_roles_admin_only(self, client):
        with _roles([{"language_id": LANG, "role": "reviewer"}]):
            resp = client.get("/api/contribute/roles/all", headers=_auth_headers())
        assert resp.status_code == 403

    def test_list_all_roles(self, client):
        grants = [{"user_id": "u", "email": "a@b.c", "language_id": None,
                   "language_code": None, "role": "admin", "created_at": None}]
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.list_all_roles",
                   new=AsyncMock(return_value=grants)):
            resp = client.get("/api/contribute/roles/all", headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json()["grants"][0]["email"] == "a@b.c"


class TestReviewNotes:
    def test_flag_issue_requires_role(self, client):
        with _roles([]), \
             patch("backend.routers.contribute.get_point_language",
                   new=AsyncMock(return_value=LANG)):
            resp = client.post(
                f"/api/contribute/grammar/{POINT}/notes",
                json={"note": "tone marks look off"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 403

    def test_flag_issue_as_contributor(self, client):
        with _roles([{"language_id": LANG, "role": "contributor"}]), \
             patch("backend.routers.contribute.get_point_language",
                   new=AsyncMock(return_value=LANG)), \
             patch("backend.routers.contribute.add_review_note",
                   new=AsyncMock(return_value="note-1")) as mock_add:
            resp = client.post(
                f"/api/contribute/grammar/{POINT}/notes",
                json={"note": "drill 4 uses the Ibadan form"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json() == {"id": "note-1"}
        assert mock_add.await_args.args[3] == "drill 4 uses the Ibadan form"

    def test_flag_issue_missing_point_404(self, client):
        with _roles([{"language_id": LANG, "role": "reviewer"}]), \
             patch("backend.routers.contribute.get_point_language",
                   new=AsyncMock(return_value=None)):
            resp = client.post(
                f"/api/contribute/grammar/{POINT}/notes",
                json={"note": "hello there"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 404

    def test_list_notes_role_gated(self, client):
        with _roles([]):
            resp = client.get(
                "/api/contribute/notes", params={"language_id": LANG},
                headers=_auth_headers(),
            )
        assert resp.status_code == 403

    def test_list_notes(self, client):
        notes = [{"id": "n1", "grammar_point_id": POINT,
                  "point_title": "Locative", "level": "A1",
                  "note": "check the -ta variants", "status": "open",
                  "author_email": "linguist@x.com", "created_at": None}]
        with _roles([{"language_id": LANG, "role": "reviewer"}]), \
             patch("backend.routers.contribute.list_review_notes",
                   new=AsyncMock(return_value=notes)):
            resp = client.get(
                "/api/contribute/notes", params={"language_id": LANG},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json()["notes"][0]["point_title"] == "Locative"

    def test_resolve_requires_reviewer_for_language(self, client):
        with _roles([{"language_id": OTHER_LANG, "role": "reviewer"}]), \
             patch("backend.routers.contribute.get_note_language",
                   new=AsyncMock(return_value=LANG)):
            resp = client.post(
                "/api/contribute/notes/n1/resolve", headers=_auth_headers()
            )
        assert resp.status_code == 403

    def test_resolve_as_reviewer(self, client):
        with _roles([{"language_id": LANG, "role": "reviewer"}]), \
             patch("backend.routers.contribute.get_note_language",
                   new=AsyncMock(return_value=LANG)), \
             patch("backend.routers.contribute.resolve_review_note",
                   new=AsyncMock(return_value=True)):
            resp = client.post(
                "/api/contribute/notes/n1/resolve", headers=_auth_headers()
            )
        assert resp.status_code == 200
        assert resp.json() == {"resolved": True}


class TestReviewPolicy:
    def test_set_requires_admin(self, client):
        with _roles([{"language_id": LANG, "role": "contributor"}]):
            resp = client.post(
                "/api/contribute/language-policy",
                json={"language_id": LANG, "policy": "ai_ok"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 403

    def test_set_as_admin(self, client):
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.set_language_policy",
                   new=AsyncMock(return_value=True)) as mock_set:
            resp = client.post(
                "/api/contribute/language-policy",
                json={"language_id": LANG, "policy": "ai_ok"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json() == {"policy": "ai_ok"}
        mock_set.assert_awaited_once()

    def test_invalid_policy_422(self, client):
        resp = client.post(
            "/api/contribute/language-policy",
            json={"language_id": LANG, "policy": "whatever"},
            headers=_auth_headers(),
        )
        assert resp.status_code == 422

    def test_grammar_listing_includes_policy(self, client):
        with _roles([{"language_id": LANG, "role": "contributor"}]), \
             patch("backend.routers.contribute.list_grammar_points",
                   new=AsyncMock(return_value=[])), \
             patch("backend.routers.contribute.get_language_policy",
                   new=AsyncMock(return_value="ai_ok")), \
             patch("backend.routers.contribute.get_language_tutor_model",
                   new=AsyncMock(return_value="claude-sonnet-5")):
            resp = client.get(
                "/api/contribute/grammar", params={"language_id": LANG},
                headers=_auth_headers(),
            )
        assert resp.json()["review_policy"] == "ai_ok"
        assert resp.json()["tutor_model"] == "claude-sonnet-5"


class TestTutorModelPicker:
    def test_set_requires_admin(self, client):
        with _roles([{"language_id": LANG, "role": "reviewer"}]):
            resp = client.post(
                "/api/contribute/language-tutor-model",
                json={"language_id": LANG, "model": "claude-sonnet-5"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 403

    def test_set_as_admin(self, client):
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.set_language_tutor_model",
                   new=AsyncMock()) as mock_set:
            resp = client.post(
                "/api/contribute/language-tutor-model",
                json={"language_id": LANG, "model": "claude-haiku-4-5-20251001"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json() == {"tutor_model": "claude-haiku-4-5-20251001"}
        mock_set.assert_awaited_once()

    def test_reset_to_default_with_null(self, client):
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.set_language_tutor_model",
                   new=AsyncMock()) as mock_set:
            resp = client.post(
                "/api/contribute/language-tutor-model",
                json={"language_id": LANG, "model": None},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert mock_set.await_args.args[2] is None

    def test_unknown_model_422(self, client):
        with _roles([{"language_id": None, "role": "admin"}]):
            resp = client.post(
                "/api/contribute/language-tutor-model",
                json={"language_id": LANG, "model": "gpt-9000"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 422


class TestTutorUsageOverview:
    """WP9b: the admin cost view — token rollups priced at list rates."""

    def test_requires_admin(self, client):
        with _roles([{"language_id": LANG, "role": "reviewer"}]):
            resp = client.get(
                "/api/contribute/tutor-usage", headers=_auth_headers()
            )
        assert resp.status_code == 403

    def test_admin_gets_priced_rollup(self, client):
        rows = [
            {
                "language_id": LANG, "language_name": "Turkish",
                "model": "claude-sonnet-5", "kind": "chat", "messages": 40,
                "input_tokens": 1_000_000, "output_tokens": 100_000,
                "cache_write_tokens": 100_000, "cache_read_tokens": 1_000_000,
            },
            {
                "language_id": LANG, "language_name": "Turkish",
                "model": "claude-sonnet-4-6", "kind": "summary", "messages": 5,
                "input_tokens": 200_000, "output_tokens": 10_000,
                "cache_write_tokens": 0, "cache_read_tokens": 0,
            },
        ]
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.aggregate_tutor_usage",
                   new=AsyncMock(return_value=rows)) as mock_agg:
            resp = client.get(
                "/api/contribute/tutor-usage",
                params={"days": 30},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["days"] == 30
        # sonnet-5 at $3/$15 per Mtok: 3.0 input + 1.5 output
        #   + 0.375 cache write (1.25x) + 0.3 cache read (0.1x) = 5.175
        assert body["rows"][0]["est_cost_usd"] == pytest.approx(5.175)
        # summarizer: 0.2 * 3 + 0.01 * 15 = 0.75
        assert body["rows"][1]["est_cost_usd"] == pytest.approx(0.75)
        assert body["total_est_cost_usd"] == pytest.approx(5.925)
        # only chat rows are messages a learner spent
        assert body["total_messages"] == 40
        mock_agg.assert_awaited_once()

    def test_days_window_clamped(self, client):
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.aggregate_tutor_usage",
                   new=AsyncMock(return_value=[])):
            resp = client.get(
                "/api/contribute/tutor-usage",
                params={"days": 9999},
                headers=_auth_headers(),
            )
        assert resp.json()["days"] == 365


class TestEngagement:
    """Admin engagement snapshot — active users, feature usage, study time."""

    def test_requires_admin(self, client):
        with _roles([{"language_id": LANG, "role": "reviewer"}]):
            resp = client.get(
                "/api/contribute/engagement", headers=_auth_headers()
            )
        assert resp.status_code == 403

    def test_admin_gets_snapshot(self, client):
        snapshot = {
            "days": 30, "total_users": 12, "new_users": 4,
            "active_users": {"d1": 3, "d7": 7, "d30": 9},
            "reviews": 186, "review_hours": 9.4, "tutor_messages": 35,
            "readings": 3, "cards_started": 325,
            "feature_users": {"review": 6, "tutor": 4, "reader": 2},
            "top_languages": [
                {"code": "es", "name": "Spanish", "learners": 4, "cards": 120},
            ],
        }
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.admin_engagement",
                   new=AsyncMock(return_value=snapshot)) as mock_eng:
            resp = client.get(
                "/api/contribute/engagement",
                params={"days": 30},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json() == snapshot
        mock_eng.assert_awaited_once()

    def test_days_window_clamped(self, client):
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.admin_engagement",
                   new=AsyncMock(return_value={})) as mock_eng:
            client.get(
                "/api/contribute/engagement",
                params={"days": 9999},
                headers=_auth_headers(),
            )
        assert mock_eng.await_args.args[1] == 365


class TestSuggestions:
    """Contributor-proposed card edits: propose → queue → approve/reject."""

    def _payload(self, **over):
        p = {"entity_type": "vocabulary", "entity_id": POINT,
             "proposed": {"definition": "to; at"}, "note": "was 'bishop'"}
        p.update(over)
        return p

    def test_submit_requires_contributor(self, client):
        with _roles([]), \
             patch("backend.routers.contribute.entity_language",
                   new=AsyncMock(return_value=LANG)):
            resp = client.post("/api/contribute/suggestions",
                               json=self._payload(), headers=_auth_headers())
        assert resp.status_code == 403

    def test_submit_unknown_card_404(self, client):
        with _roles([{"language_id": LANG, "role": "contributor"}]), \
             patch("backend.routers.contribute.entity_language",
                   new=AsyncMock(return_value=None)):
            resp = client.post("/api/contribute/suggestions",
                               json=self._payload(), headers=_auth_headers())
        assert resp.status_code == 404

    def test_submit_success(self, client):
        with _roles([{"language_id": LANG, "role": "contributor"}]), \
             patch("backend.routers.contribute.entity_language",
                   new=AsyncMock(return_value=LANG)), \
             patch("backend.routers.contribute.submit_suggestion",
                   new=AsyncMock(return_value="sug-1")) as mock_sub:
            resp = client.post("/api/contribute/suggestions",
                               json=self._payload(), headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json()["id"] == "sug-1"
        mock_sub.assert_awaited_once()

    def test_queue_requires_reviewer(self, client):
        # a contributor (not reviewer) cannot see the queue
        with _roles([{"language_id": LANG, "role": "contributor"}]):
            resp = client.get("/api/contribute/suggestions",
                              params={"language_id": LANG}, headers=_auth_headers())
        assert resp.status_code == 403

    def test_queue_success(self, client):
        rows = [{"id": "s1", "entity_type": "vocabulary", "card_title": "a",
                 "current": {"definition": "bishop"},
                 "proposed": {"definition": "to; at"}}]
        with _roles([{"language_id": LANG, "role": "reviewer"}]), \
             patch("backend.routers.contribute.list_suggestions",
                   new=AsyncMock(return_value=rows)):
            resp = client.get("/api/contribute/suggestions",
                              params={"language_id": LANG}, headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json()["suggestions"][0]["card_title"] == "a"

    def test_approve_applies(self, client):
        with _roles([{"language_id": LANG, "role": "reviewer"}]), \
             patch("backend.routers.contribute.get_suggestion",
                   new=AsyncMock(return_value={"language_id": LANG, "status": "pending"})), \
             patch("backend.routers.contribute.approve_suggestion",
                   new=AsyncMock(return_value=True)) as mock_ap:
            resp = client.post("/api/contribute/suggestions/s1/approve",
                               headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json()["approved"] is True
        mock_ap.assert_awaited_once()

    def test_approve_requires_reviewer_for_that_language(self, client):
        with _roles([{"language_id": OTHER_LANG, "role": "reviewer"}]), \
             patch("backend.routers.contribute.get_suggestion",
                   new=AsyncMock(return_value={"language_id": LANG, "status": "pending"})):
            resp = client.post("/api/contribute/suggestions/s1/approve",
                               headers=_auth_headers())
        assert resp.status_code == 403

    def test_reject_success(self, client):
        with _roles([{"language_id": LANG, "role": "reviewer"}]), \
             patch("backend.routers.contribute.get_suggestion",
                   new=AsyncMock(return_value={"language_id": LANG, "status": "pending"})), \
             patch("backend.routers.contribute.reject_suggestion",
                   new=AsyncMock(return_value=True)) as mock_rej:
            resp = client.post("/api/contribute/suggestions/s1/reject",
                               json={"review_note": "wrong sense"},
                               headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json()["rejected"] is True
        mock_rej.assert_awaited_once()


class TestCreatePoint:
    def test_create_requires_role(self, client):
        with _roles([]):
            resp = client.post(
                "/api/contribute/grammar",
                json={"language_id": LANG, "title": "New point"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 403

    def test_create_succeeds(self, client):
        with _roles([{"language_id": LANG, "role": "contributor"}]), \
             patch("backend.routers.contribute.create_grammar_point",
                   new=AsyncMock(return_value=POINT)):
            resp = client.post(
                "/api/contribute/grammar",
                json={"language_id": LANG, "title": "New point", "level": "A1"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json() == {"id": POINT}

    def test_duplicate_title_409(self, client):
        with _roles([{"language_id": LANG, "role": "contributor"}]), \
             patch("backend.routers.contribute.create_grammar_point",
                   new=AsyncMock(return_value=None)):
            resp = client.post(
                "/api/contribute/grammar",
                json={"language_id": LANG, "title": "Dup"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 409


class TestDrills:
    def test_list_drills_role_gated(self, client):
        with _roles([]), \
             patch("backend.routers.contribute.get_point_language_and_code",
                   new=AsyncMock(return_value=(LANG, "tr"))):
            resp = client.get(
                f"/api/contribute/grammar/{POINT}/drills", headers=_auth_headers()
            )
        assert resp.status_code == 403

    def test_add_drill_validates_answerability(self, client):
        # validate_drill returns False -> 422, no write
        with _roles([{"language_id": LANG, "role": "contributor"}]), \
             patch("backend.routers.contribute.get_point_language_and_code",
                   new=AsyncMock(return_value=(LANG, "tr"))), \
             patch("backend.routers.contribute.validate_drill",
                   new=AsyncMock(return_value=False)), \
             patch("backend.routers.contribute.add_drill", new=AsyncMock()) as mock_add:
            resp = client.post(
                f"/api/contribute/grammar/{POINT}/drills",
                json={"sentence": "no blank", "answer": "x"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 422
        mock_add.assert_not_awaited()

    def test_add_drill_succeeds_when_answerable(self, client):
        with _roles([{"language_id": LANG, "role": "contributor"}]), \
             patch("backend.routers.contribute.get_point_language_and_code",
                   new=AsyncMock(return_value=(LANG, "tr"))), \
             patch("backend.routers.contribute.validate_drill",
                   new=AsyncMock(return_value=True)), \
             patch("backend.routers.contribute.add_drill",
                   new=AsyncMock(return_value="drill-1")) as mock_add:
            resp = client.post(
                f"/api/contribute/grammar/{POINT}/drills",
                json={"sentence": "Kitap {{answer}}.", "answer": "masada",
                      "translation": "The book is on the table."},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json() == {"id": "drill-1"}
        mock_add.assert_awaited_once()

    def test_add_drill_unknown_point_404(self, client):
        with _roles([{"language_id": LANG, "role": "contributor"}]), \
             patch("backend.routers.contribute.get_point_language_and_code",
                   new=AsyncMock(return_value=None)):
            resp = client.post(
                f"/api/contribute/grammar/{POINT}/drills",
                json={"sentence": "Kitap {{answer}}.", "answer": "masada"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 404

    def test_delete_drill(self, client):
        with _roles([{"language_id": LANG, "role": "contributor"}]), \
             patch("backend.routers.contribute.get_point_language_and_code",
                   new=AsyncMock(return_value=(LANG, "tr"))), \
             patch("backend.routers.contribute.delete_drill",
                   new=AsyncMock(return_value=True)) as mock_del:
            resp = client.delete(
                f"/api/contribute/grammar/{POINT}/drills/drill-1",
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        mock_del.assert_awaited_once()


class TestEditDrill:
    """PUT drill edits: reviewer/admin only, guard-railed, change_note required."""

    def _put(self, client, body, roles=None):
        with _roles(roles or [{"language_id": LANG, "role": "reviewer"}]), \
             patch("backend.routers.contribute.get_point_language_and_code",
                   new=AsyncMock(return_value=(LANG, "tr"))), \
             patch("backend.routers.contribute.validate_drill",
                   new=AsyncMock(return_value=True)), \
             patch("backend.routers.contribute.update_drill",
                   new=AsyncMock(return_value=True)) as mock_update, \
             patch("backend.routers.contribute.add_review_note",
                   new=AsyncMock(return_value="note-1")) as mock_note:
            resp = client.put(
                f"/api/contribute/grammar/{POINT}/drills/drill-1",
                json=body,
                headers=_auth_headers(),
            )
        return resp, mock_update, mock_note

    def test_contributor_cannot_edit(self, client):
        resp, mock_update, _ = self._put(
            client,
            {"sentence": "Kitap {{answer}}.", "answer": "masada",
             "change_note": "fix a wrong case ending"},
            roles=[{"language_id": LANG, "role": "contributor"}],
        )
        assert resp.status_code == 403
        mock_update.assert_not_awaited()

    def test_change_note_required(self, client):
        resp, mock_update, _ = self._put(
            client,
            {"sentence": "Kitap {{answer}}.", "answer": "masada",
             "change_note": "short"},
        )
        assert resp.status_code == 422  # min_length=10 friction
        mock_update.assert_not_awaited()

    def test_answer_leak_rejected(self, client):
        resp, mock_update, _ = self._put(
            client,
            {"sentence": "Masada kitap {{answer}}.", "answer": "masada",
             "change_note": "attempting a leaky frame"},
        )
        assert resp.status_code == 422
        mock_update.assert_not_awaited()

    def test_hint_reveal_rejected(self, client):
        resp, mock_update, _ = self._put(
            client,
            {"sentence": "Kitap {{answer}}.", "answer": "masada",
             "hint": "the word is masada",
             "change_note": "attempting a revealing hint"},
        )
        assert resp.status_code == 422
        mock_update.assert_not_awaited()

    def test_multiword_answer_rejected(self, client):
        resp, mock_update, _ = self._put(
            client,
            {"sentence": "Kitap {{answer}}.", "answer": "iki kelime",
             "change_note": "two-word answers break grading"},
        )
        assert resp.status_code == 422
        mock_update.assert_not_awaited()

    def test_reviewer_edit_saves_and_files_note(self, client):
        resp, mock_update, mock_note = self._put(
            client,
            {"sentence": "Kitap {{answer}} duruyor.", "answer": "masada",
             "translation": "The book is on the table.",
             "change_note": "clarified the frame with a verb"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"saved": True, "reviewed": False}
        mock_update.assert_awaited_once()
        mock_note.assert_awaited_once()
        note_text = mock_note.await_args.args[3]
        assert note_text.startswith("[card edit]")


class TestSelfApprovalGuard:
    def test_editor_cannot_approve_own_change(self, client):
        conn = AsyncMock()
        conn.fetchval = AsyncMock(return_value=TEST_USER_ID)  # last editor = caller

        @asynccontextmanager
        async def _priv():
            yield conn

        with _roles([{"language_id": LANG, "role": "reviewer"}]), \
             patch("backend.routers.contribute.get_point_language",
                   new=AsyncMock(return_value=LANG)), \
             patch("backend.routers.contribute.privileged_connection", _priv):
            resp = client.post(
                f"/api/contribute/grammar/{POINT}/approve",
                headers=_auth_headers(),
            )
        assert resp.status_code == 403
        assert "different reviewer" in resp.json()["detail"]


class _FakeHttpxResp:
    def __init__(self, status_code, text="", payload=None):
        self.status_code = status_code
        self.text = text
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


def _fake_httpx(resp=None, exc=None):
    class _C:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, *a, **k):
            if exc:
                raise exc
            return resp

    return lambda *a, **k: _C()


class TestCreateAccount:
    """The invite-only beta path: admin mints accounts via the Supabase API."""

    _body = {"email": "friend@example.com", "password": "0123456789"}

    def test_requires_admin(self, client):
        with _roles([{"language_id": LANG, "role": "reviewer"}]):
            resp = client.post("/api/contribute/users", json=self._body,
                               headers=_auth_headers())
        assert resp.status_code == 403

    def test_success_via_sql_first(self, client):
        # DB first: no HTTP call at all on the happy path (this deploy's
        # egress to the auth API hangs — the old API-first order 504'd).
        def boom(*a, **k):
            raise AssertionError("httpx must not be used when SQL succeeds")
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("httpx.AsyncClient", boom), \
             patch("backend.routers.contribute.create_auth_user",
                   new=AsyncMock(return_value="db-uid-1")) as mock_sql:
            resp = client.post("/api/contribute/users", json=self._body,
                               headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json() == {"id": "db-uid-1", "email": "friend@example.com"}
        mock_sql.assert_awaited_once()

    def test_duplicate_email_409(self, client):
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.create_auth_user",
                   new=AsyncMock(side_effect=ValueError("email already registered"))):
            resp = client.post("/api/contribute/users", json=self._body,
                               headers=_auth_headers())
        assert resp.status_code == 409

    def test_sql_down_falls_back_to_api(self, client):
        resp_ok = _FakeHttpxResp(200, payload={"id": "api-1", "email": "friend@example.com"})
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("httpx.AsyncClient", _fake_httpx(resp=resp_ok)), \
             patch("backend.routers.contribute.create_auth_user",
                   new=AsyncMock(side_effect=RuntimeError("db hiccup"))):
            resp = client.post("/api/contribute/users", json=self._body,
                               headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json()["id"] == "api-1"

    def test_sql_down_api_duplicate_409(self, client):
        dup = _FakeHttpxResp(422, text='{"error_code":"email_exists","msg":"already registered"}')
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("httpx.AsyncClient", _fake_httpx(resp=dup)), \
             patch("backend.routers.contribute.create_auth_user",
                   new=AsyncMock(side_effect=RuntimeError("db hiccup"))):
            resp = client.post("/api/contribute/users", json=self._body,
                               headers=_auth_headers())
        assert resp.status_code == 409

    def test_both_paths_down_is_502(self, client):
        import httpx
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("httpx.AsyncClient", _fake_httpx(exc=httpx.ConnectError("down"))), \
             patch("backend.routers.contribute.create_auth_user",
                   new=AsyncMock(side_effect=RuntimeError("db down too"))):
            resp = client.post("/api/contribute/users", json=self._body,
                               headers=_auth_headers())
        assert resp.status_code == 502
        assert "both paths" in resp.json()["detail"]

    def test_sql_down_and_no_key_503(self, client):
        class NoKey(FakeSettings):
            supabase_service_role_key = ""
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.dependencies.get_settings", return_value=NoKey()), \
             patch("backend.routers.contribute.create_auth_user",
                   new=AsyncMock(side_effect=RuntimeError("db down"))):
            resp = client.post("/api/contribute/users", json=self._body,
                               headers=_auth_headers())
        assert resp.status_code == 503
        assert "SUPABASE_SERVICE_ROLE_KEY" in resp.json()["detail"]


class TestEngagementUsers:
    """Per-user drill-down behind the engagement tiles."""

    def test_requires_admin(self, client):
        with _roles([{"language_id": LANG, "role": "reviewer"}]):
            resp = client.get("/api/contribute/engagement/users",
                              headers=_auth_headers())
        assert resp.status_code == 403

    def test_admin_gets_user_rows(self, client):
        rows = [{"id": "u1", "email": "a@b.c", "joined": None,
                 "last_active": "2026-07-19T00:00:00+00:00", "reviews": 12,
                 "review_minutes": 8, "tutor_messages": 2, "readings": 1,
                 "cards_started": 5, "cards_total": 40, "languages": ["es"]}]
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.admin_engagement_users",
                   new=AsyncMock(return_value=rows)) as mock_users:
            resp = client.get("/api/contribute/engagement/users",
                              params={"days": 9999}, headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json() == {"users": rows}
        assert mock_users.await_args.args[1] == 365  # days clamped


class TestAnalytics:
    """WP26 a+b: time-series and cohort endpoints (admin only)."""

    def test_timeseries_requires_admin(self, client):
        with _roles([{"language_id": LANG, "role": "reviewer"}]):
            resp = client.get("/api/contribute/analytics/timeseries",
                              headers=_auth_headers())
        assert resp.status_code == 403

    def test_timeseries_clamps_days(self, client):
        series = [{"date": "2026-07-19", "active_users": 2, "reviews": 10,
                   "minutes": 5, "new_users": 1}]
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.admin_timeseries",
                   new=AsyncMock(return_value=series)) as mock_ts:
            resp = client.get("/api/contribute/analytics/timeseries",
                              params={"days": 9999}, headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json() == {"days": 90, "series": series}
        assert mock_ts.await_args.args[1] == 90

    def test_cohorts_endpoint(self, client):
        grid = [{"cohort_week": "2026-07-06", "size": 4,
                 "returned": [4, 2, 1, 0, 0, 0, 0, 0]}]
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.admin_cohorts",
                   new=AsyncMock(return_value=grid)):
            resp = client.get("/api/contribute/analytics/cohorts",
                              headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json() == {"cohorts": grid}

    def test_cohort_grid_math(self):
        from backend.repositories.contributor import compute_cohort_grid

        signups = [("u1", "2026-07-06"), ("u2", "2026-07-06"),
                   ("u3", "2026-07-13")]
        activity = {
            ("u1", "2026-07-06"), ("u1", "2026-07-13"),  # active w0 + w1
            ("u2", "2026-07-06"),                          # w0 only
            ("u3", "2026-07-13"),                          # later cohort, w0
        }
        grid = compute_cohort_grid(signups, activity)
        assert grid[0]["cohort_week"] == "2026-07-06"
        assert grid[0]["size"] == 2
        assert grid[0]["returned"][:3] == [2, 1, 0]
        assert grid[1]["cohort_week"] == "2026-07-13"
        assert grid[1]["returned"][0] == 1


class TestEngagementUserDetail:
    """Per-language breakdown behind one row of the users table."""

    UID = "550e8400-e29b-41d4-a716-446655440042"

    def test_requires_admin(self, client):
        with _roles([{"language_id": LANG, "role": "reviewer"}]):
            resp = client.get(f"/api/contribute/engagement/users/{self.UID}",
                              headers=_auth_headers())
        assert resp.status_code == 403

    def test_invalid_uuid_422(self, client):
        with _roles([{"language_id": None, "role": "admin"}]):
            resp = client.get("/api/contribute/engagement/users/not-a-uuid",
                              headers=_auth_headers())
        assert resp.status_code == 422

    def test_admin_gets_language_rows(self, client):
        rows = [{"code": "ru", "name": "Russian", "cards_total": 80,
                 "reviews": 50, "review_minutes": 30, "tutor_messages": 0,
                 "readings": 0, "last_review": "2026-07-19T00:00:00+00:00"}]
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.admin_engagement_user_detail",
                   new=AsyncMock(return_value=rows)) as mock_detail:
            resp = client.get(f"/api/contribute/engagement/users/{self.UID}",
                              params={"days": 9999}, headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json() == {"languages": rows}
        assert mock_detail.await_args.args[1] == self.UID
        assert mock_detail.await_args.args[2] == 365  # days clamped


class TestTranslationReviews:
    """The AI maker-checker's reject queue: list, approve (applies), reject."""

    def test_requires_admin(self, client):
        with _roles([{"language_id": LANG, "role": "reviewer"}]):
            resp = client.get("/api/contribute/translation-reviews",
                              headers=_auth_headers())
        assert resp.status_code == 403

    def test_admin_lists_queue(self, client):
        items = [{"id": "r1", "locale": "nl", "word": "cat", "proposed": "kat",
                  "reason": "unsure", "current_definition": "small feline",
                  "created_at": None}]
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.list_translation_reviews",
                   new=AsyncMock(return_value=items)):
            resp = client.get("/api/contribute/translation-reviews",
                              headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json() == {"reviews": items}

    def test_approve_applies(self, client):
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.resolve_translation_review",
                   new=AsyncMock(return_value="ok")) as mock_resolve:
            resp = client.post("/api/contribute/translation-reviews/r1/approve",
                               headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json() == {"approved": True}
        assert mock_resolve.await_args.args[2] is True

    def test_approve_without_proposal_422(self, client):
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.resolve_translation_review",
                   new=AsyncMock(return_value="empty")):
            resp = client.post("/api/contribute/translation-reviews/r1/approve",
                               headers=_auth_headers())
        assert resp.status_code == 422

    def test_reject_resolved_is_409(self, client):
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.resolve_translation_review",
                   new=AsyncMock(return_value="not_pending")):
            resp = client.post("/api/contribute/translation-reviews/r1/reject",
                               headers=_auth_headers())
        assert resp.status_code == 409


class TestAccountAdmin:
    """Admin account management: list, plan override, deletion guards."""

    def test_accounts_list_requires_admin(self, client):
        with _roles([{"language_id": LANG, "role": "reviewer"}]):
            resp = client.get("/api/contribute/users", headers=_auth_headers())
        assert resp.status_code == 403

    def test_accounts_list_as_admin(self, client):
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.list_accounts",
                   new=AsyncMock(return_value=[{"id": "u2", "email": "a@b.c"}])):
            resp = client.get("/api/contribute/users", headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json() == {"users": [{"id": "u2", "email": "a@b.c"}]}

    def test_admin_cannot_delete_self(self, client):
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.delete_account",
                   new=AsyncMock()) as mock_del:
            resp = client.delete(
                f"/api/contribute/users/{TEST_USER_ID}", headers=_auth_headers()
            )
        assert resp.status_code == 403
        mock_del.assert_not_awaited()

    def test_admin_deletes_other_account(self, client):
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.delete_account",
                   new=AsyncMock(return_value=True)) as mock_del:
            resp = client.delete(
                "/api/contribute/users/99999999-aaaa-bbbb-cccc-000000000001",
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json() == {"deleted": True}
        mock_del.assert_awaited_once()

    def test_delete_requires_admin(self, client):
        with _roles([{"language_id": LANG, "role": "reviewer"}]), \
             patch("backend.routers.contribute.delete_account",
                   new=AsyncMock()) as mock_del:
            resp = client.delete(
                "/api/contribute/users/99999999-aaaa-bbbb-cccc-000000000001",
                headers=_auth_headers(),
            )
        assert resp.status_code == 403
        mock_del.assert_not_awaited()

    def test_plan_override_single_needs_language(self, client):
        with _roles([{"language_id": None, "role": "admin"}]):
            resp = client.put(
                "/api/contribute/users/99999999-aaaa-bbbb-cccc-000000000001/plan",
                json={"plan_scope": "single"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 422

    def test_plan_override_saves(self, client):
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.set_account_plan",
                   new=AsyncMock(return_value=True)) as mock_set:
            resp = client.put(
                "/api/contribute/users/99999999-aaaa-bbbb-cccc-000000000001/plan",
                json={"plan_scope": "all"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        mock_set.assert_awaited_once()

    def test_tutor_override_saves(self, client):
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.set_tutor_access",
                   new=AsyncMock()) as mock_set:
            resp = client.put(
                "/api/contribute/users/99999999-aaaa-bbbb-cccc-000000000001/tutor",
                json={"access": "enabled", "daily_cap": 10},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json() == {"access": "enabled", "daily_cap": 10}
        assert mock_set.await_args.args[2:] == ("enabled", 10)

    def test_tutor_override_requires_admin(self, client):
        with _roles([{"language_id": LANG, "role": "reviewer"}]):
            resp = client.put(
                "/api/contribute/users/99999999-aaaa-bbbb-cccc-000000000001/tutor",
                json={"access": "blocked"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 403

    def test_tutor_override_validates_access(self, client):
        with _roles([{"language_id": None, "role": "admin"}]):
            resp = client.put(
                "/api/contribute/users/99999999-aaaa-bbbb-cccc-000000000001/tutor",
                json={"access": "sometimes"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 422

    def test_create_account_requires_admin(self, client):
        with _roles([{"language_id": LANG, "role": "reviewer"}]):
            resp = client.post(
                "/api/contribute/users",
                json={"email": "friend@beta.test", "password": "kea-tui-1234"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 403

    def test_create_account_rejects_short_password(self, client):
        with _roles([{"language_id": None, "role": "admin"}]):
            resp = client.post(
                "/api/contribute/users",
                json={"email": "friend@beta.test", "password": "short"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 422


class TestChangeRequests:
    CR = "44444444-4444-4444-4444-444444444444"

    def test_create_requires_a_staff_role(self, client):
        with _roles([]):  # a plain learner
            resp = client.post(
                "/api/contribute/change-requests",
                json={"language_id": LANG, "field": "sentence", "issue": "wrong gender"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 403

    def test_reviewer_can_create(self, client):
        with _roles([{"language_id": LANG, "role": "reviewer"}]), \
             patch("backend.routers.contribute.create_request",
                   new=AsyncMock(return_value=self.CR)) as mock_create:
            resp = client.post(
                "/api/contribute/change-requests",
                json={
                    "language_id": LANG, "target_type": "drill", "field": "sentence",
                    "target_label": "El meva cotxe és nou.",
                    "issue": "meva should be meu (cotxe is masculine)",
                    "suggestion": "El meu cotxe és nou.",
                },
                headers=_auth_headers(),
            )
        assert resp.status_code == 201
        assert resp.json()["id"] == self.CR
        assert mock_create.await_args.args[6] == "sentence"

    def test_contributor_can_create_too(self, client):
        # "Contributors have all reviewer permissions" — can_contribute gate.
        with _roles([{"language_id": LANG, "role": "contributor"}]), \
             patch("backend.routers.contribute.create_request",
                   new=AsyncMock(return_value=self.CR)):
            resp = client.post(
                "/api/contribute/change-requests",
                json={"language_id": LANG, "field": "hint", "issue": "hint leaks the answer"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 201

    def test_invalid_field_422(self, client):
        with _roles([{"language_id": LANG, "role": "reviewer"}]):
            resp = client.post(
                "/api/contribute/change-requests",
                json={"language_id": LANG, "field": "nonsense", "issue": "x"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 422

    def test_board_lists_and_reports_resolve_permission(self, client):
        reqs = [{"id": self.CR, "field": "sentence", "issue": "x", "score": 2,
                 "my_vote": 1, "status": "open"}]
        with _roles([{"language_id": LANG, "role": "reviewer"}]), \
             patch("backend.routers.contribute.list_requests",
                   new=AsyncMock(return_value=reqs)):
            resp = client.get(
                "/api/contribute/change-requests",
                params={"language_id": LANG}, headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json()["requests"] == reqs
        assert resp.json()["can_resolve"] is False  # reviewer, not admin

    def test_vote_requires_staff(self, client):
        with _roles([]), \
             patch("backend.routers.contribute.get_request_language",
                   new=AsyncMock(return_value=LANG)):
            resp = client.post(
                f"/api/contribute/change-requests/{self.CR}/vote",
                json={"vote": 1}, headers=_auth_headers(),
            )
        assert resp.status_code == 403

    def test_vote_ok(self, client):
        with _roles([{"language_id": LANG, "role": "contributor"}]), \
             patch("backend.routers.contribute.get_request_language",
                   new=AsyncMock(return_value=LANG)), \
             patch("backend.routers.contribute.cast_vote",
                   new=AsyncMock(return_value=True)) as mock_vote:
            resp = client.post(
                f"/api/contribute/change-requests/{self.CR}/vote",
                json={"vote": -1}, headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert mock_vote.await_args.args[3] == -1

    def test_only_admin_resolves(self, client):
        with _roles([{"language_id": LANG, "role": "reviewer"}]):
            resp = client.post(
                f"/api/contribute/change-requests/{self.CR}/resolve",
                json={"status": "accepted"}, headers=_auth_headers(),
            )
        assert resp.status_code == 403

    def test_admin_resolves(self, client):
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.resolve_request",
                   new=AsyncMock(return_value=True)):
            resp = client.post(
                f"/api/contribute/change-requests/{self.CR}/resolve",
                json={"status": "accepted"}, headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "accepted"


# ── admin content-generation panel (WP42) ──────────────────────────────────

from contextlib import asynccontextmanager as _acm  # noqa: E402

LANG_ID = "11111111-1111-1111-1111-111111111111"


def _priv_yielding(conn):
    @_acm
    async def _cm():
        yield conn
    return patch("backend.routers.contribute.privileged_connection", _cm)


_COVERAGE_ROWS = [
    {"language_id": LANG_ID, "language_code": "sw", "language_name": "Swahili",
     "vocab_total": 100, "vocab_no_examples": 80, "grammar_total": 20,
     "grammar_no_drills": 5, "ai_examples": 0, "pending_examples": 0,
     "ai_drills": 0},
    {"language_id": "22222222-2222-2222-2222-222222222222", "language_code": "es",
     "language_name": "Spanish", "vocab_total": 500, "vocab_no_examples": 10,
     "grammar_total": 40, "grammar_no_drills": 0, "ai_examples": 3,
     "pending_examples": 2, "ai_drills": 1},
]


class TestGenerationCoverage:
    def test_requires_admin(self, client):
        with _roles([{"language_id": LANG_ID, "role": "contributor"}]):
            resp = client.get(
                "/api/contribute/admin/generation/coverage", headers=_auth_headers()
            )
        assert resp.status_code == 403

    def test_admin_gets_recs_and_ranked_next(self, client):
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.generation_coverage",
                   new=AsyncMock(return_value=[dict(r) for r in _COVERAGE_ROWS])):
            resp = client.get(
                "/api/contribute/admin/generation/coverage", headers=_auth_headers()
            )
        assert resp.status_code == 200
        body = resp.json()
        # every language row carries its resolved models + low-resource flag
        sw = next(r for r in body["coverage"] if r["language_code"] == "sw")
        assert sw["low_resource"] is True
        assert sw["sentence_model"] and sw["grammar_model"]
        assert sw["unfilled"] == 85  # 80 vocab + 5 grammar
        # Swahili (85 unfilled) ranks ahead of Spanish (10) in "do next"
        assert body["recommended_next"][0]["language_code"] == "sw"
        assert body["limits"]["max_per_item"] >= 1


class TestGenerationRun:
    def test_requires_admin(self, client):
        with _roles([{"language_id": LANG_ID, "role": "reviewer"}]):
            resp = client.post(
                "/api/contribute/admin/generation/run",
                json={"language_id": LANG_ID, "language_code": "sw", "kind": "vocab"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 403

    def test_dry_run_previews_without_generating(self, client):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={"code": "sw", "name": "Swahili"})
        plan = {"kind": "vocab", "model": "claude-x", "target_per_item": 3,
                "items_to_process": 40, "sentences_to_attempt": 120,
                "est_cost_usd": 0.42, "_items": [1, 2, 3]}
        with _roles([{"language_id": None, "role": "admin"}]), \
             _priv_yielding(conn), \
             patch("backend.routers.contribute.plan_run",
                   new=AsyncMock(return_value=dict(plan))) as mock_plan, \
             patch("backend.routers.contribute.run_generation",
                   new=AsyncMock()) as mock_run:
            resp = client.post(
                "/api/contribute/admin/generation/run",
                json={"language_id": LANG_ID, "language_code": "sw",
                      "kind": "vocab", "dry_run": True},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["dry_run"] is True
        assert body["est_cost_usd"] == 0.42
        assert "_items" not in body            # internal work-list is stripped
        mock_run.assert_not_awaited()          # nothing generated on a dry run
        mock_plan.assert_awaited_once()

    def test_real_run_503_when_key_absent(self, client):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={"code": "sw", "name": "Swahili"})
        with _roles([{"language_id": None, "role": "admin"}]), \
             _priv_yielding(conn), \
             patch("backend.routers.contribute.generation_available",
                   return_value=False):
            resp = client.post(
                "/api/contribute/admin/generation/run",
                json={"language_id": LANG_ID, "language_code": "sw",
                      "kind": "vocab", "dry_run": False},
                headers=_auth_headers(),
            )
        assert resp.status_code == 503

    def test_real_run_reports_analysis(self, client):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={"code": "sw", "name": "Swahili"})
        analysis = {"kind": "vocab", "language_code": "sw", "model": "claude-x",
                    "items_processed": 25, "sentences_accepted": 70,
                    "sentences_persisted": 68, "duplicates_skipped": 2,
                    "est_cost_usd": 0.31}
        with _roles([{"language_id": None, "role": "admin"}]), \
             _priv_yielding(conn), \
             patch("backend.routers.contribute.generation_available",
                   return_value=True), \
             patch("backend.routers.contribute.run_generation",
                   new=AsyncMock(return_value=dict(analysis))):
            resp = client.post(
                "/api/contribute/admin/generation/run",
                json={"language_id": LANG_ID, "language_code": "sw",
                      "kind": "vocab", "dry_run": False},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["dry_run"] is False
        assert body["sentences_persisted"] == 68

    def test_unknown_language_404(self, client):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value=None)
        with _roles([{"language_id": None, "role": "admin"}]), \
             _priv_yielding(conn):
            resp = client.post(
                "/api/contribute/admin/generation/run",
                json={"language_id": LANG_ID, "language_code": "sw",
                      "kind": "vocab", "dry_run": True},
                headers=_auth_headers(),
            )
        assert resp.status_code == 404

    def test_rejects_bad_kind(self, client):
        with _roles([{"language_id": None, "role": "admin"}]):
            resp = client.post(
                "/api/contribute/admin/generation/run",
                json={"language_id": LANG_ID, "language_code": "sw",
                      "kind": "nonsense", "dry_run": True},
                headers=_auth_headers(),
            )
        assert resp.status_code == 422


class TestGenerationRecheck:
    def test_requires_admin(self, client):
        with _roles([{"language_id": LANG_ID, "role": "reviewer"}]):
            resp = client.post(
                "/api/contribute/admin/generation/recheck",
                json={"language_id": LANG_ID, "language_code": "sw", "kind": "grammar"},
                headers=_auth_headers(),
            )
        assert resp.status_code == 403

    def test_dry_run_previews_drills_normalized(self, client):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={"code": "sw", "name": "Swahili"})
        plan = {"kind": "recheck_drills", "model": "claude-x",
                "points_to_audit": 12, "drills_to_audit": 48,
                "est_cost_usd": 0.19, "_items": [1, 2]}
        with _roles([{"language_id": None, "role": "admin"}]), \
             _priv_yielding(conn), \
             patch("backend.routers.contribute.plan_recheck_drills",
                   new=AsyncMock(return_value=dict(plan))) as mock_plan, \
             patch("backend.routers.contribute.recheck_drills",
                   new=AsyncMock()) as mock_run:
            resp = client.post(
                "/api/contribute/admin/generation/recheck",
                json={"language_id": LANG_ID, "language_code": "sw",
                      "kind": "grammar", "dry_run": True},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["dry_run"] is True
        # Normalized keys map from the drill-specific plan.
        assert body["items_to_audit"] == 12
        assert body["units_to_audit"] == 48
        assert "_items" not in body
        mock_run.assert_not_awaited()
        mock_plan.assert_awaited_once()

    def test_real_recheck_reports_flags_and_alternatives(self, client):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={"code": "sw", "name": "Swahili"})
        result = {"kind": "recheck_drills", "model": "claude-x",
                  "points_audited": 12, "drills_flagged": 3,
                  "alternatives_generated": 7, "est_cost_usd": 0.21}
        with _roles([{"language_id": None, "role": "admin"}]), \
             _priv_yielding(conn), \
             patch("backend.routers.contribute.generation_available",
                   return_value=True), \
             patch("backend.routers.contribute.recheck_drills",
                   new=AsyncMock(return_value=dict(result))):
            resp = client.post(
                "/api/contribute/admin/generation/recheck",
                json={"language_id": LANG_ID, "language_code": "sw",
                      "kind": "grammar", "dry_run": False},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["dry_run"] is False
        assert body["items_audited"] == 12
        assert body["flagged"] == 3
        assert body["alternatives_generated"] == 7

    def test_vocab_recheck_dispatches_examples(self, client):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={"code": "sw", "name": "Swahili"})
        result = {"kind": "recheck", "model": "claude-x",
                  "words_audited": 30, "sentences_flagged": 4,
                  "alternatives_generated": 9, "est_cost_usd": 0.15}
        with _roles([{"language_id": None, "role": "admin"}]), \
             _priv_yielding(conn), \
             patch("backend.routers.contribute.generation_available",
                   return_value=True), \
             patch("backend.routers.contribute.recheck_examples",
                   new=AsyncMock(return_value=dict(result))) as mock_ex, \
             patch("backend.routers.contribute.recheck_drills",
                   new=AsyncMock()) as mock_dr:
            resp = client.post(
                "/api/contribute/admin/generation/recheck",
                json={"language_id": LANG_ID, "language_code": "sw",
                      "kind": "vocab", "dry_run": False},
                headers=_auth_headers(),
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["items_audited"] == 30 and body["flagged"] == 4
        mock_ex.assert_awaited_once()
        mock_dr.assert_not_awaited()

    def test_real_recheck_503_when_key_absent(self, client):
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={"code": "sw", "name": "Swahili"})
        with _roles([{"language_id": None, "role": "admin"}]), \
             _priv_yielding(conn), \
             patch("backend.routers.contribute.generation_available",
                   return_value=False):
            resp = client.post(
                "/api/contribute/admin/generation/recheck",
                json={"language_id": LANG_ID, "language_code": "sw",
                      "kind": "grammar", "dry_run": False},
                headers=_auth_headers(),
            )
        assert resp.status_code == 503


class TestGenerationReviewGate:
    EX = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

    def test_pending_requires_admin(self, client):
        with _roles([{"language_id": LANG_ID, "role": "contributor"}]):
            resp = client.get(
                "/api/contribute/admin/generation/pending",
                params={"language_id": LANG_ID}, headers=_auth_headers(),
            )
        assert resp.status_code == 403

    def test_admin_lists_pending(self, client):
        rows = [{"id": EX_ID, "sentence": "Mbwa anakimbia.",
                 "translation": "The dog runs.", "origin_detail": "claude-x",
                 "word": "mbwa", "vocabulary_id": "v-1"}
                for EX_ID in ("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",)]
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.list_pending_examples",
                   new=AsyncMock(return_value=rows)):
            resp = client.get(
                "/api/contribute/admin/generation/pending",
                params={"language_id": LANG_ID}, headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json()["pending"][0]["word"] == "mbwa"

    def test_approve_marks_reviewed(self, client):
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.review_example",
                   new=AsyncMock(return_value=True)) as mock_rev:
            resp = client.post(
                f"/api/contribute/admin/generation/examples/{self.EX}/review",
                json={"approve": True}, headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json()["approved"] is True
        assert mock_rev.await_args.args[2] is True  # approve flag

    def test_reject_deletes(self, client):
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.review_example",
                   new=AsyncMock(return_value=True)) as mock_rev:
            resp = client.post(
                f"/api/contribute/admin/generation/examples/{self.EX}/review",
                json={"approve": False}, headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json()["approved"] is False
        assert mock_rev.await_args.args[2] is False

    def test_review_404_when_not_pending(self, client):
        with _roles([{"language_id": None, "role": "admin"}]), \
             patch("backend.routers.contribute.review_example",
                   new=AsyncMock(return_value=False)):
            resp = client.post(
                f"/api/contribute/admin/generation/examples/{self.EX}/review",
                json={"approve": True}, headers=_auth_headers(),
            )
        assert resp.status_code == 404

    def test_review_requires_admin(self, client):
        with _roles([{"language_id": LANG_ID, "role": "reviewer"}]):
            resp = client.post(
                f"/api/contribute/admin/generation/examples/{self.EX}/review",
                json={"approve": True}, headers=_auth_headers(),
            )
        assert resp.status_code == 403


def _rls_yielding(conn):
    @_acm
    async def _cm(user_id):
        yield conn
    return patch("backend.routers.contribute.rls_connection", _cm)


class TestGeneratedDrillReview:
    DRILL = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

    def test_pending_requires_reviewer(self, client):
        with _roles([{"language_id": LANG_ID, "role": "contributor"}]):
            resp = client.get(
                "/api/contribute/review/generated-drills",
                params={"language_id": LANG_ID}, headers=_auth_headers(),
            )
        assert resp.status_code == 403

    def test_reviewer_lists_pending(self, client):
        rows = [{"id": "d1", "sentence": "x {{answer}}", "answer": "y",
                 "translation": None, "hint": "h", "cell": "yo",
                 "origin_detail": "m", "point_title": "P", "point_id": "p1"}]
        with _roles([{"language_id": LANG_ID, "role": "reviewer"}]), \
             patch("backend.routers.contribute.list_pending_drills",
                   new=AsyncMock(return_value=rows)):
            resp = client.get(
                "/api/contribute/review/generated-drills",
                params={"language_id": LANG_ID}, headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json()["pending"][0]["cell"] == "yo"

    def test_approve_drill(self, client):
        conn = AsyncMock()
        conn.fetchval = AsyncMock(return_value=LANG_ID)
        with _roles([{"language_id": LANG_ID, "role": "reviewer"}]), \
             _rls_yielding(conn), \
             patch("backend.routers.contribute.review_drill",
                   new=AsyncMock(return_value=True)) as mock_rev:
            resp = client.post(
                f"/api/contribute/review/generated-drills/{self.DRILL}/review",
                json={"approve": True}, headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert resp.json()["approved"] is True
        assert mock_rev.await_args.args[2] is True

    def test_reject_drill(self, client):
        conn = AsyncMock()
        conn.fetchval = AsyncMock(return_value=LANG_ID)
        with _roles([{"language_id": LANG_ID, "role": "reviewer"}]), \
             _rls_yielding(conn), \
             patch("backend.routers.contribute.review_drill",
                   new=AsyncMock(return_value=True)) as mock_rev:
            resp = client.post(
                f"/api/contribute/review/generated-drills/{self.DRILL}/review",
                json={"approve": False}, headers=_auth_headers(),
            )
        assert resp.status_code == 200
        assert mock_rev.await_args.args[2] is False

    def test_review_404_when_drill_missing(self, client):
        conn = AsyncMock()
        conn.fetchval = AsyncMock(return_value=None)   # no such drill
        with _roles([{"language_id": None, "role": "admin"}]), _rls_yielding(conn):
            resp = client.post(
                f"/api/contribute/review/generated-drills/{self.DRILL}/review",
                json={"approve": True}, headers=_auth_headers(),
            )
        assert resp.status_code == 404

    def test_review_403_for_non_reviewer(self, client):
        conn = AsyncMock()
        conn.fetchval = AsyncMock(return_value=LANG_ID)
        with _roles([{"language_id": LANG_ID, "role": "contributor"}]), \
             _rls_yielding(conn):
            resp = client.post(
                f"/api/contribute/review/generated-drills/{self.DRILL}/review",
                json={"approve": True}, headers=_auth_headers(),
            )
        assert resp.status_code == 403
