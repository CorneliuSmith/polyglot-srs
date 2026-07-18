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
