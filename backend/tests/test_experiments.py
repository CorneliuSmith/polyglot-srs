"""Rollouts: who sees what, and what happens when nothing is set up.

The mechanism is small and the consequences of getting it wrong are not:
a learner flipped between two looks on alternate page loads gives feedback
about neither, and a resolver that can raise takes down the endpoint the
whole app renders from.
"""

from __future__ import annotations

import time
from collections import Counter
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import asyncpg
import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.repositories.experiments import (
    assignment_counts,
    get_assignments,
    list_experiments,
    update_experiment,
)
from backend.services.experiments import (
    bucket_of,
    resolve,
    resolve_variants,
    variant_for_bucket,
)
from backend.tests.fakes import mock_conn

TEST_SECRET = "test-jwt-secret-for-unit-tests-32bytes"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"


class FakeSettings:
    supabase_jwt_secret = TEST_SECRET
    supabase_url = "https://fake.supabase.co"
    supabase_anon_key = "k"
    supabase_service_role_key = "sk"
    database_url = "postgresql://fake/db"
    environment = "test"
    cors_origins = []
    anthropic_api_key = ""


def _auth_headers() -> dict:
    token = pyjwt.encode(
        {"sub": TEST_USER_ID, "aud": "authenticated",
         "exp": int(time.time()) + 3600},
        TEST_SECRET, algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def _experiment(**over) -> dict:
    return {
        "key": "ui_skin",
        "name": "Visual direction",
        "description": None,
        "variants": [{"key": "classic", "label": "Classic"},
                     {"key": "flat", "label": "Flat"}],
        "default_variant": "classic",
        "rollout": {},
        "enabled": True,
        "learner_choice": True,
        **over,
    }


# ---------------------------------------------------------------------------
# Bucketing
# ---------------------------------------------------------------------------


class TestBucketing:
    def test_the_same_person_always_lands_in_the_same_bucket(self):
        """The property the whole design rests on. If this drifts, people
        change look on page loads and their feedback describes an app that
        never existed."""
        first = bucket_of(TEST_USER_ID, "ui_skin")
        assert all(bucket_of(TEST_USER_ID, "ui_skin") == first for _ in range(50))
        assert 0 <= first < 100

    def test_each_experiment_buckets_people_differently(self):
        """Without salting by key, the same unlucky cohort would be first
        into every change the app ever tries."""
        ids = [str(uuid4()) for _ in range(200)]
        a = [bucket_of(i, "ui_skin") for i in ids]
        b = [bucket_of(i, "new_study_page") for i in ids]
        assert a != b

    def test_the_spread_is_roughly_even(self):
        """A 25% rollout has to actually reach about a quarter of people."""
        ids = [str(uuid4()) for _ in range(4000)]
        in_first_quarter = sum(1 for i in ids if bucket_of(i, "ui_skin") < 25)
        assert 800 < in_first_quarter < 1200

    def test_shares_are_walked_in_the_variants_order(self):
        """Shares are allocated from bucket 0 upward, in the order the
        variants are declared — so "30% on flat" is buckets 0-29, and
        everything past the last share falls to the default."""
        exp = _experiment(rollout={"flat": 30})
        assert variant_for_bucket(exp, 0) == "flat"
        assert variant_for_bucket(exp, 29) == "flat"
        assert variant_for_bucket(exp, 30) == "classic"

    def test_whatever_is_left_over_goes_to_the_default(self):
        exp = _experiment(rollout={"flat": 10})
        assert variant_for_bucket(exp, 99) == "classic"

    def test_a_share_that_is_not_a_number_is_no_share(self):
        """An admin who typed something odd gets a rollout of zero, not a
        crash on every page load."""
        exp = _experiment(rollout={"flat": "lots"})
        assert variant_for_bucket(exp, 0) == "classic"


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------


class TestResolution:
    def test_an_explicit_assignment_beats_the_percentage(self):
        """Someone giving feedback about the new look must not be moved off
        it because a share changed underneath them."""
        exp = _experiment(rollout={"flat": 0})
        got = resolve(exp, TEST_USER_ID, {"variant": "flat", "source": "admin"})
        assert got == "flat"

    def test_switching_the_experiment_off_returns_everyone_to_the_default(self):
        exp = _experiment(enabled=False, rollout={"flat": 100})
        assert resolve(exp, TEST_USER_ID, None) == "classic"

    def test_off_beats_an_assignment_too(self):
        """Off is a kill switch, not a pause. A withdrawn look must not
        survive on the accounts that were pinned to it."""
        exp = _experiment(enabled=False)
        got = resolve(exp, TEST_USER_ID, {"variant": "flat", "source": "self"})
        assert got == "classic"

    def test_a_variant_that_no_longer_exists_does_not_strand_anyone(self):
        exp = _experiment()
        got = resolve(exp, TEST_USER_ID, {"variant": "brutalist", "source": "admin"})
        assert got == "classic"

    def test_a_full_rollout_reaches_everybody(self):
        exp = _experiment(rollout={"flat": 100})
        ids = [str(uuid4()) for _ in range(100)]
        assert {resolve(exp, i, None) for i in ids} == {"flat"}

    def test_raising_the_share_never_removes_anyone_already_in(self):
        """The reason buckets are a stable hash rather than a stored coin
        flip: 25% → 50% must be additive."""
        ids = [str(uuid4()) for _ in range(500)]
        quarter = _experiment(rollout={"flat": 25})
        half = _experiment(rollout={"flat": 50})
        was_in = {i for i in ids if resolve(quarter, i, None) == "flat"}
        still_in = {i for i in ids if resolve(half, i, None) == "flat"}
        assert was_in <= still_in
        assert len(still_in) > len(was_in)


class TestResolutionNeverBreaksThePage:
    """resolve_variants runs on the endpoint the whole app renders from."""

    async def test_no_experiments_is_not_an_error(self):
        conn = mock_conn()
        conn.fetch = AsyncMock(return_value=[])
        assert await resolve_variants(conn, TEST_USER_ID) == {}

    async def test_a_missing_table_serves_a_profile_anyway(self):
        conn = mock_conn()
        conn.fetch = AsyncMock(
            side_effect=asyncpg.exceptions.UndefinedTableError("no experiments")
        )
        assert await resolve_variants(conn, TEST_USER_ID) == {}

    async def test_a_database_falling_over_serves_a_profile_anyway(self):
        conn = mock_conn()
        conn.fetch = AsyncMock(side_effect=RuntimeError("pool is gone"))
        assert await resolve_variants(conn, TEST_USER_ID) == {}

    async def test_one_broken_experiment_does_not_take_the_others_with_it(self):
        """A row with no default_variant is malformed; the rest still
        resolve."""
        with patch("backend.services.experiments.list_experiments",
                   new=AsyncMock(return_value=[
                       {"key": "broken", "variants": [], "enabled": True},
                       _experiment(),
                   ])), \
             patch("backend.services.experiments.get_assignments",
                   new=AsyncMock(return_value={})):
            got = await resolve_variants(AsyncMock(), TEST_USER_ID)
        assert got == {"ui_skin": "classic"}


# ---------------------------------------------------------------------------
# Repository degradation
# ---------------------------------------------------------------------------


class TestRepositoryDegrades:
    """20260930 is applied by hand. Until it lands, every read answers
    'nothing running' rather than raising."""

    async def test_list_is_empty_without_the_table(self):
        conn = mock_conn()
        conn.fetch = AsyncMock(
            side_effect=asyncpg.exceptions.UndefinedTableError("nope")
        )
        assert await list_experiments(conn) == []
        assert await get_assignments(conn, TEST_USER_ID) == {}
        assert await assignment_counts(conn, "ui_skin") == []

    async def test_a_patch_with_no_fields_touches_nothing(self):
        """Turning nothing on must not issue an UPDATE that stamps
        updated_at and looks like a change in the audit trail."""
        conn = mock_conn()
        conn.execute = AsyncMock()
        assert await update_experiment(conn, "ui_skin") is True
        conn.execute.assert_not_awaited()

    async def test_only_the_named_fields_are_written(self):
        """Switching an experiment off must not also reset the percentage
        an admin spent a week arriving at."""
        conn = mock_conn()
        conn.execute = AsyncMock(return_value="UPDATE 1")
        await update_experiment(conn, "ui_skin", enabled=False)
        sql = conn.execute.await_args.args[0]
        assert "enabled" in sql
        assert "rollout" not in sql
        assert "default_variant" not in sql


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


def _conn() -> AsyncMock:
    conn = mock_conn()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchval = AsyncMock(return_value=None)
    conn.execute = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)
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
         patch("backend.routers.auth.rls_connection", fake_conn), \
         patch("backend.routers.auth.privileged_connection", fake_conn), \
         patch("backend.routers.contribute.rls_connection", fake_conn), \
         patch("backend.routers.contribute.privileged_connection", fake_conn):
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as c:
            c.fake_conn = conn
            yield c


class TestLearnerEndpoints:
    def test_settings_is_only_offered_experiments_you_may_switch(self, client):
        """A rollout still being decided internally must not appear on a
        learner's Settings page just because it is running."""
        with patch("backend.routers.auth.list_experiments",
                   new=AsyncMock(return_value=[
                       _experiment(),
                       _experiment(key="pricing", learner_choice=False),
                       _experiment(key="draft", enabled=False),
                   ])), \
             patch("backend.routers.auth.resolve_variants",
                   new=AsyncMock(return_value={"ui_skin": "flat"})):
            resp = client.get("/api/auth/experiments", headers=_auth_headers())
        assert resp.status_code == 200
        offered = resp.json()["experiments"]
        assert [e["key"] for e in offered] == ["ui_skin"]
        assert offered[0]["current"] == "flat"
        assert offered[0]["learner_choice"] is True

    def test_an_assigned_account_is_told_what_it_is_on(self, client):
        """The owner's mode — "I as admin choose for the account". No
        switch is offered, but an account placed on a non-default version
        must still see WHICH one, and have somewhere to say what they
        think; a tester restyled overnight with no explanation anywhere
        reports it as a bug."""
        with patch("backend.routers.auth.list_experiments",
                   new=AsyncMock(return_value=[
                       _experiment(learner_choice=False),
                   ])), \
             patch("backend.routers.auth.resolve_variants",
                   new=AsyncMock(return_value={"ui_skin": "flat"})):
            resp = client.get("/api/auth/experiments", headers=_auth_headers())
        offered = resp.json()["experiments"]
        assert [e["key"] for e in offered] == ["ui_skin"]
        assert offered[0]["current"] == "flat"
        assert offered[0]["learner_choice"] is False

    def test_an_assigned_experiment_stays_invisible_on_the_default(self, client):
        """Admin-chosen mode, account on Classic: nothing new to tell them
        about, so nothing renders — the section must not announce an
        experiment to the people it doesn't affect."""
        with patch("backend.routers.auth.list_experiments",
                   new=AsyncMock(return_value=[
                       _experiment(learner_choice=False),
                   ])), \
             patch("backend.routers.auth.resolve_variants",
                   new=AsyncMock(return_value={"ui_skin": "classic"})):
            resp = client.get("/api/auth/experiments", headers=_auth_headers())
        assert resp.json()["experiments"] == []

    def test_choosing_a_variant_records_it_as_their_own_choice(self, client):
        with patch("backend.routers.auth.get_experiment",
                   new=AsyncMock(return_value=_experiment())), \
             patch("backend.routers.auth.assign_variant",
                   new=AsyncMock(return_value=True)) as assigned:
            resp = client.post("/api/auth/experiment", headers=_auth_headers(),
                               json={"key": "ui_skin", "variant": "flat"})
        assert resp.status_code == 200
        assert resp.json()["variant"] == "flat"
        # Source matters: "42 on flat" reads differently when 40 chose it.
        assert assigned.await_args.kwargs["source"] == "self"

    def test_a_learner_cannot_switch_an_experiment_that_is_not_theirs(self, client):
        with patch("backend.routers.auth.get_experiment",
                   new=AsyncMock(return_value=_experiment(learner_choice=False))):
            resp = client.post("/api/auth/experiment", headers=_auth_headers(),
                               json={"key": "ui_skin", "variant": "flat"})
        assert resp.status_code == 403

    def test_a_learner_cannot_opt_into_a_withdrawn_experiment(self, client):
        """The kill switch has to hold from every direction, including a
        bookmarked request."""
        with patch("backend.routers.auth.get_experiment",
                   new=AsyncMock(return_value=_experiment(enabled=False))):
            resp = client.post("/api/auth/experiment", headers=_auth_headers(),
                               json={"key": "ui_skin", "variant": "flat"})
        assert resp.status_code == 403

    def test_an_unknown_variant_is_rejected(self, client):
        with patch("backend.routers.auth.get_experiment",
                   new=AsyncMock(return_value=_experiment())):
            resp = client.post("/api/auth/experiment", headers=_auth_headers(),
                               json={"key": "ui_skin", "variant": "brutalist"})
        assert resp.status_code == 422

    def test_clearing_puts_them_back_under_the_rollout(self, client):
        with patch("backend.routers.auth.get_experiment",
                   new=AsyncMock(return_value=_experiment())), \
             patch("backend.routers.auth.clear_assignment",
                   new=AsyncMock(return_value=True)) as cleared:
            resp = client.post("/api/auth/experiment", headers=_auth_headers(),
                               json={"key": "ui_skin", "variant": None})
        assert resp.status_code == 200
        assert resp.json()["variant"] is None
        cleared.assert_awaited()


class TestAdminEndpoints:
    def test_only_an_admin_can_see_the_rollouts(self, client):
        with patch("backend.routers.contribute.get_roles",
                   new=AsyncMock(return_value=[])):
            resp = client.get("/api/contribute/experiments",
                              headers=_auth_headers())
        assert resp.status_code == 403

    def test_shares_over_a_hundred_percent_are_refused(self, client):
        """Silently starving the last variant would show the admin a number
        that does not mean what it says."""
        with patch("backend.routers.contribute.get_roles",
                   new=AsyncMock(return_value=[{"role": "admin"}])), \
             patch("backend.routers.contribute.is_admin", return_value=True), \
             patch("backend.routers.contribute.get_experiment",
                   new=AsyncMock(return_value=_experiment())):
            resp = client.post("/api/contribute/experiment",
                               headers=_auth_headers(),
                               json={"key": "ui_skin",
                                     "rollout": {"classic": 80, "flat": 40}})
        assert resp.status_code == 422
        assert "100" in resp.json()["detail"]

    def test_a_negative_share_is_refused(self, client):
        with patch("backend.routers.contribute.get_roles",
                   new=AsyncMock(return_value=[{"role": "admin"}])), \
             patch("backend.routers.contribute.is_admin", return_value=True), \
             patch("backend.routers.contribute.get_experiment",
                   new=AsyncMock(return_value=_experiment())):
            resp = client.post("/api/contribute/experiment",
                               headers=_auth_headers(),
                               json={"key": "ui_skin", "rollout": {"flat": -5}})
        assert resp.status_code == 422

    def test_a_share_for_a_variant_that_does_not_exist_is_refused(self, client):
        with patch("backend.routers.contribute.get_roles",
                   new=AsyncMock(return_value=[{"role": "admin"}])), \
             patch("backend.routers.contribute.is_admin", return_value=True), \
             patch("backend.routers.contribute.get_experiment",
                   new=AsyncMock(return_value=_experiment())):
            resp = client.post("/api/contribute/experiment",
                               headers=_auth_headers(),
                               json={"key": "ui_skin", "rollout": {"neon": 10}})
        assert resp.status_code == 422

    def test_the_missing_migration_is_named_rather_than_guessed_at(self, client):
        """Same idiom as the visibility switch: the 503 says which migration,
        because 'unknown experiment' would send an admin hunting."""
        with patch("backend.routers.contribute.get_roles",
                   new=AsyncMock(return_value=[{"role": "admin"}])), \
             patch("backend.routers.contribute.is_admin", return_value=True), \
             patch("backend.routers.contribute.get_experiment",
                   new=AsyncMock(return_value=None)):
            resp = client.post("/api/contribute/experiment",
                               headers=_auth_headers(),
                               json={"key": "ui_skin", "enabled": True})
        assert resp.status_code == 503
        assert "20260930" in resp.json()["detail"]

    def test_assigning_someone_who_has_no_account_is_a_404(self, client):
        with patch("backend.routers.contribute.get_roles",
                   new=AsyncMock(return_value=[{"role": "admin"}])), \
             patch("backend.routers.contribute.is_admin", return_value=True), \
             patch("backend.routers.contribute.get_experiment",
                   new=AsyncMock(return_value=_experiment())), \
             patch("backend.routers.contribute.find_user_by_email",
                   new=AsyncMock(return_value=None)):
            resp = client.post("/api/contribute/experiment-assign",
                               headers=_auth_headers(),
                               json={"key": "ui_skin", "email": "nobody@example.com",
                                     "variant": "flat"})
        assert resp.status_code == 404

    def test_an_admin_pins_someone_by_email(self, client):
        # find_user_by_email is mocked with a BARE ID STRING because that is
        # what the real function returns. It was once mocked as a dict, which
        # agreed with a router bug (target["id"] on a string → TypeError) and
        # let every production assignment 500 with "Could not assign that."
        # The integration test drives the real seam; this mock must match it.
        with patch("backend.routers.contribute.get_roles",
                   new=AsyncMock(return_value=[{"role": "admin"}])), \
             patch("backend.routers.contribute.is_admin", return_value=True), \
             patch("backend.routers.contribute.get_experiment",
                   new=AsyncMock(return_value=_experiment())), \
             patch("backend.routers.contribute.find_user_by_email",
                   new=AsyncMock(return_value=TEST_USER_ID)), \
             patch("backend.routers.contribute.assign_variant",
                   new=AsyncMock(return_value=True)) as assigned:
            resp = client.post("/api/contribute/experiment-assign",
                               headers=_auth_headers(),
                               json={"key": "ui_skin", "email": "kate@example.com",
                                     "variant": "flat", "note": "beta group"})
        assert resp.status_code == 200
        assert resp.json()["variant"] == "flat"
        assert assigned.await_args.kwargs["source"] == "admin"
        assert assigned.await_args.kwargs["note"] == "beta group"


class TestDistribution:
    def test_a_half_and_half_split_really_is_about_half(self):
        """The number an admin types has to be the number they get."""
        exp = _experiment(rollout={"flat": 50})
        seen = Counter(
            resolve(exp, str(uuid4()), None) for _ in range(2000)
        )
        assert 900 < seen["flat"] < 1100
        assert seen["classic"] + seen["flat"] == 2000
