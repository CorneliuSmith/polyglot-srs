"""Recommendations end to end, against a REAL server and a REAL database.

Every previous fix for this feature passed its tests and still failed in
production, because every one of those tests mocked away the part that
was broken. This one boots the actual app the way DigitalOcean does —
uvicorn in its own process, migrations applied, RLS on, a real JWT over
real HTTP — and drives the endpoints the page drives.

What it proves that the unit tests cannot:
  * the draft survives the HTTP response completing (the whole point of
    moving generation into a background task, and the mechanism the 504
    was hiding);
  * the poll contract the page depends on is what the server really
    sends: generating true, then a batch;
  * the batch is written and readable under RLS, with the usage row that
    shares its transaction.

The model call is the one thing stubbed, via TUTOR_DEV_MOCK — there is no
API key in CI. The schema/fallback path is covered separately in
test_recommendations_draft.py and test_recommend_service.py.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import jwt as pyjwt
import pytest

from .conftest import INTEGRATION_DSN, requires_db

pytestmark = requires_db

# Derived, never hardcoded: CI runs from a different checkout path with no
# virtualenv, so a literal path to this container's .venv fails there and
# only there — which is exactly the kind of "passes for me" gap the rest of
# this file exists to close.
REPO_ROOT = Path(__file__).resolve().parents[3]

JWT_SECRET = "e2e-jwt-secret-at-least-32-bytes-long!!"
BOOT_TIMEOUT_S = 60
DRAFT_TIMEOUT_S = 30


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _token(user_id: str) -> str:
    return pyjwt.encode(
        {"sub": user_id, "aud": "authenticated",
         "exp": int(time.time()) + 3600},
        JWT_SECRET, algorithm="HS256",
    )


@pytest.fixture(scope="module")
def server():
    """The real ASGI app under uvicorn, as deployed."""
    port = _free_port()
    env = {
        **os.environ,
        "DATABASE_URL": INTEGRATION_DSN,
        "SUPABASE_URL": "https://test.local",
        "SUPABASE_ANON_KEY": "test",
        "SUPABASE_SERVICE_ROLE_KEY": "test",
        "SUPABASE_JWT_SECRET": JWT_SECRET,
        "ENVIRONMENT": "test",
        # No API key in CI: the model call returns a deterministic batch.
        "TUTOR_DEV_MOCK": "true",
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:create_app",
         "--factory", "--host", "127.0.0.1", "--port", str(port)],
        env=env, cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + BOOT_TIMEOUT_S
    while time.time() < deadline:
        if proc.poll() is not None:
            pytest.fail(f"server died on boot:\n{proc.stdout.read()}")
        try:
            if httpx.get(f"{base}/api/health", timeout=2).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.3)
    else:
        proc.kill()
        pytest.fail("server never became healthy")
    yield base
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


async def _seed_learner(pool, email: str, code: str) -> tuple[str, str]:
    """A user with recommendations switched on, and a language to study."""
    async with pool.privileged_connection() as conn:
        user = str(await conn.fetchval(
            "INSERT INTO auth.users (email) VALUES ($1) RETURNING id", email))
        lang = str(await conn.fetchval(
            "INSERT INTO languages (code, name, rtl) VALUES ($1, $2, false) "
            "ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name RETURNING id",
            code, code.upper()))
        await conn.execute(
            "INSERT INTO user_profiles (id, active_language_id) VALUES ($1, $2) "
            "ON CONFLICT (id) DO UPDATE SET active_language_id = EXCLUDED.active_language_id",
            user, lang)
        await conn.execute(
            "INSERT INTO media_reco_profile (user_id, enabled, about, genres, "
            "media_types) VALUES ($1, true, 'history', ARRAY['History'], "
            "ARRAY['book']) ON CONFLICT (user_id) DO UPDATE SET enabled = true",
            user)
        # Admin, so the draft isn't turned away by the Plus gate — the same
        # bypass the owner's own account relies on.
        await conn.execute(
            "INSERT INTO contributor_roles (user_id, language_id, role) "
            "VALUES ($1, NULL, 'admin') ON CONFLICT DO NOTHING", user)
    return user, lang


async def test_get_my_picks_produces_a_batch_over_real_http(pool, server):
    """The owner's exact journey: press the button, wait, get picks."""
    user, lang = await _seed_learner(pool, "e2e@recs", "e1")
    headers = {"Authorization": f"Bearer {_token(user)}"}

    with httpx.Client(base_url=server, timeout=20) as client:
        # The page's first read: on, entitled, nothing yet.
        state = client.get(f"/api/recommendations/{lang}", headers=headers)
        assert state.status_code == 200, state.text
        body = state.json()
        assert body["enabled"] is True
        assert body["entitled"] is True, "admin must not be turned away"
        assert body["batches"] == []

        # "Get my picks" — answers immediately, does NOT hold the request
        # open through the model call (that is what 504'd at the gateway).
        started = time.time()
        resp = client.post(
            f"/api/recommendations/{lang}/refresh", params={"force": "true"},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["generating"] is True
        assert time.time() - started < 10, "refresh must return without waiting"

        # The page polls until the batch lands.
        deadline = time.time() + DRAFT_TIMEOUT_S
        batches, error = [], None
        while time.time() < deadline:
            body = client.get(
                f"/api/recommendations/{lang}", headers=headers).json()
            error = body.get("draft_error")
            batches = body["batches"]
            if batches or error:
                break
            time.sleep(0.5)

        assert error is None, f"the draft failed: {error}"
        assert batches, "no batch ever appeared — the draft never landed"
        items = batches[0]["items"]
        assert items and items[0]["title"], items
        # Polling stops once it's done.
        assert body["generating"] is False

    # And it really is in the database, with its usage row.
    async with pool.privileged_connection() as conn:
        stored = await conn.fetchval(
            "SELECT count(*) FROM media_recommendations WHERE user_id = $1", user)
        kinds = await conn.fetch(
            "SELECT kind FROM tutor_usage WHERE user_id = $1", user)
    assert stored == 1
    assert [r["kind"] for r in kinds] == ["recs"]


async def test_a_second_press_does_not_buy_a_second_batch(pool, server):
    """The page auto-refreshes on load and the button exists — two presses
    in flight must not double-charge the learner's allowance."""
    user, lang = await _seed_learner(pool, "e2e@recs2", "e2")
    headers = {"Authorization": f"Bearer {_token(user)}"}

    with httpx.Client(base_url=server, timeout=20) as client:
        first = client.post(f"/api/recommendations/{lang}/refresh",
                            params={"force": "true"}, headers=headers)
        second = client.post(f"/api/recommendations/{lang}/refresh",
                             params={"force": "true"}, headers=headers)
        assert first.status_code == second.status_code == 200
        deadline = time.time() + DRAFT_TIMEOUT_S
        while time.time() < deadline:
            body = client.get(
                f"/api/recommendations/{lang}", headers=headers).json()
            if body["batches"] or body.get("draft_error"):
                break
            time.sleep(0.5)

    async with pool.privileged_connection() as conn:
        count = await conn.fetchval(
            "SELECT count(*) FROM media_recommendations WHERE user_id = $1", user)
    assert count == 1, "a second press drafted (and charged for) a second batch"


async def test_recommendations_are_private_to_their_owner(pool, server):
    """RLS over real HTTP: one learner's picks are invisible to another."""
    owner, lang = await _seed_learner(pool, "e2e@owner", "e3")
    other, _ = await _seed_learner(pool, "e2e@other", "e3")

    with httpx.Client(base_url=server, timeout=20) as client:
        client.post(f"/api/recommendations/{lang}/refresh",
                    params={"force": "true"},
                    headers={"Authorization": f"Bearer {_token(owner)}"})
        deadline = time.time() + DRAFT_TIMEOUT_S
        while time.time() < deadline:
            mine = client.get(
                f"/api/recommendations/{lang}",
                headers={"Authorization": f"Bearer {_token(owner)}"}).json()
            if mine["batches"] or mine.get("draft_error"):
                break
            time.sleep(0.5)
        assert mine["batches"], f"owner got no batch: {mine.get('draft_error')}"

        theirs = client.get(
            f"/api/recommendations/{lang}",
            headers={"Authorization": f"Bearer {_token(other)}"}).json()
    assert theirs["batches"] == []
