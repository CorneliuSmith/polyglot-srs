"""refresh_recommendations: passive weekly draft vs the explicit
force=True "get new recommendations now" request.

The endpoint only runs the gates and STARTS the draft (the synchronous
shape 504'd at DigitalOcean's gateway); the model call runs in a
background task. _call drains that task inside its patch stack so every
assertion still sees the mocks.
"""
import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from backend.routers import recommendations as reco_router
from backend.routers.recommendations import refresh_recommendations


@pytest.fixture(autouse=True)
def _clean_registry():
    reco_router._DRAFTS.clear()
    reco_router._DRAFT_ERRORS.clear()
    yield
    reco_router._DRAFTS.clear()
    reco_router._DRAFT_ERRORS.clear()


async def _drain_drafts():
    """Run the draft the endpoint just spawned to completion — while the
    caller's patches are still active, as the server's own loop would."""
    tasks = list(reco_router._DRAFTS.values())
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

USER = {"id": "user-1"}
LANG_ID = "11111111-1111-1111-1111-111111111111"

ENABLED_PROFILE = {"enabled": True, "about": "", "genres": [], "media_types": []}
LANG_ROW = {"code": "es", "name": "Spanish", "tutor_model": None}
ENTITLED = {"tier": "plus", "unlimited": False, "entitled": True, "limit": 1000,
            "used": 0, "remaining": 1000, "resets_at": None}
NOT_ENTITLED = {"tier": "free", "unlimited": False, "entitled": False, "limit": 20,
                 "used": 0, "remaining": 20, "resets_at": None}


class FakeConn:
    def __init__(self, lang_row=LANG_ROW):
        self.lang_row = lang_row

    async def fetchrow(self, query, *args):
        return MagicMock(__getitem__=lambda self, k: self.data[k], data=self.lang_row) \
            if self.lang_row else None


@asynccontextmanager
async def _fake_rls(user_id: str):
    yield FakeConn()


def _allowing_limiter():
    """A limiter that always says yes.

    Patched in by DEFAULT rather than resetting the real module-level one:
    its window is a whole day, and under Redis (which the full suite uses)
    reset() is a deliberate no-op — so without this the force=True tests
    below burn each other's budget and fail only in a full-suite run, never
    alone. The one test that cares about the limit supplies its own stub.
    """
    limiter = AsyncMock()
    limiter.allow = AsyncMock(return_value=True)
    return limiter


def _patches(**overrides):
    base = {
        "backend.routers.recommendations.reco_refresh_limiter": _allowing_limiter(),
        "backend.routers.recommendations.rls_connection": _fake_rls,
        "backend.routers.recommendations.get_reco_profile":
            AsyncMock(return_value=ENABLED_PROFILE),
        "backend.routers.recommendations.get_study_stats":
            AsyncMock(return_value={"highest_level_reached": "A2", "learned_cards": 40}),
        "backend.routers.recommendations.get_allowance": AsyncMock(return_value=ENTITLED),
        "backend.routers.recommendations.generate_recommendations":
            AsyncMock(return_value=[{"type": "book", "title": "x"}]),
        "backend.routers.recommendations.insert_recommendation":
            AsyncMock(return_value={"id": "batch-1", "items": []}),
        "backend.routers.recommendations.log_tutor_usage": AsyncMock(),
        "backend.routers.recommendations._is_stale": AsyncMock(return_value=False),
        "backend.routers.recommendations.list_recommendations": AsyncMock(return_value=[]),
        "backend.routers.recommendations.recommended_titles": AsyncMock(return_value=[]),
        "backend.routers.recommendations.rated_titles": AsyncMock(return_value=[]),
        "backend.routers.recommendations._is_admin_user":
            AsyncMock(return_value=False),
    }
    base.update(overrides)
    return [patch(target, value) for target, value in base.items()]


async def _call(force=False, **overrides):
    patches = _patches(**overrides)
    for p in patches:
        p.start()
    try:
        result = await refresh_recommendations(LANG_ID, force=force, user=USER)
        await _drain_drafts()
        return result
    finally:
        for p in patches:
            p.stop()


@pytest.mark.asyncio
async def test_passive_call_is_a_no_op_when_not_stale():
    result = await _call(force=False)
    assert result["generated"] is False


@pytest.mark.asyncio
async def test_force_drafts_in_the_background_even_when_not_stale():
    # This is the whole point: "ask for a recommendation immediately", not
    # wait for the weekly window. The request itself answers at once — the
    # batch lands from the background task and the page polls GET for it.
    insert = AsyncMock(return_value={"id": "batch-1", "items": []})
    result = await _call(force=True, **{
        "backend.routers.recommendations.insert_recommendation": insert,
    })
    assert result == {"generated": False, "generating": True, "batch": None}
    insert.assert_awaited_once()


@pytest.mark.asyncio
async def test_force_still_grounds_the_draft_in_current_progress():
    stats = AsyncMock(return_value={"highest_level_reached": "B1", "learned_cards": 250})
    generate = AsyncMock(return_value=[{"type": "book", "title": "x"}])
    await _call(force=True, **{
        "backend.routers.recommendations.get_study_stats": stats,
        "backend.routers.recommendations.generate_recommendations": generate,
    })
    kwargs = generate.await_args.kwargs
    assert kwargs["level"] == "B1"
    assert kwargs["learned_count"] == 250


@pytest.mark.asyncio
async def test_force_is_rate_limited_independently_of_staleness():
    limiter = AsyncMock()
    limiter.allow = AsyncMock(return_value=False)
    with pytest.raises(HTTPException) as exc:
        await _call(force=True, **{
            "backend.routers.recommendations.reco_refresh_limiter": limiter,
        })
    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_passive_call_never_touches_the_rate_limiter():
    # The weekly draft is already self-limiting; it must not share (and
    # silently exhaust) the on-demand button's budget.
    limiter = AsyncMock()
    limiter.allow = AsyncMock(return_value=True)
    result = await _call(force=False, **{
        "backend.routers.recommendations.reco_refresh_limiter": limiter,
        "backend.routers.recommendations._is_stale": AsyncMock(return_value=True),
    })
    assert result["generating"] is True
    limiter.allow.assert_not_called()


@pytest.mark.asyncio
async def test_force_still_requires_the_feature_be_turned_on():
    with pytest.raises(HTTPException) as exc:
        await _call(force=True, **{
            "backend.routers.recommendations.get_reco_profile":
                AsyncMock(return_value={**ENABLED_PROFILE, "enabled": False}),
        })
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_force_still_requires_entitlement():
    with pytest.raises(HTTPException) as exc:
        await _call(force=True, **{
            "backend.routers.recommendations.get_allowance":
                AsyncMock(return_value=NOT_ENTITLED),
        })
    assert exc.value.status_code == 402


@pytest.mark.asyncio
async def test_an_exhausted_month_gets_a_clear_402():
    """Batches spend from the monthly AI pool (owner: 'a plus feature that
    will use some of their monthly ai') — an entitled learner whose month
    is spent waits for the reset, with the same allowance_exhausted error
    the tutor gives."""
    drained = {**ENTITLED, "used": 1000, "remaining": 0}
    with pytest.raises(HTTPException) as exc:
        await _call(
            force=True,
            **{"backend.routers.recommendations.get_allowance":
               AsyncMock(return_value=drained)},
        )
    assert exc.value.status_code == 402
    assert exc.value.detail["code"] == "allowance_exhausted"


@pytest.mark.asyncio
async def test_the_draft_never_repeats_and_reads_the_ratings():
    """Owner: "it should try not to generate things previously recommended"
    — every earlier title is passed as an exclusion, and the learner's
    ratings ride along to steer the taste."""
    gen = AsyncMock(return_value=[{"type": "book", "title": "fresh"}])
    result = await _call(
        force=True,
        **{
            "backend.routers.recommendations.generate_recommendations": gen,
            "backend.routers.recommendations.recommended_titles":
                AsyncMock(return_value=["Old Pick", "Older Pick"]),
            "backend.routers.recommendations.rated_titles":
                AsyncMock(return_value=[
                    {"title": "Old Pick", "rating": 5, "done": True}]),
        },
    )
    assert result["generating"] is True
    assert gen.await_args.kwargs["exclude_titles"] == ["Old Pick", "Older Pick"]
    assert gen.await_args.kwargs["reactions"][0]["rating"] == 5


@pytest.mark.asyncio
async def test_feedback_saves_done_and_rating():
    from backend.routers.recommendations import FeedbackBody, put_feedback

    saved = AsyncMock(return_value=True)
    with patch("backend.routers.recommendations.rls_connection", _fake_rls), \
         patch("backend.routers.recommendations.set_reco_feedback", saved):
        result = await put_feedback(
            "22222222-2222-2222-2222-222222222222",
            FeedbackBody(item_index=1, done=True, rating=4),
            user=USER,
        )
    assert result == {"saved": True}
    assert saved.await_args.kwargs == {"done": True, "rating": 4}
    assert saved.await_args.args[3] == 1  # the item index


@pytest.mark.asyncio
async def test_feedback_503s_before_the_migration():
    from backend.routers.recommendations import FeedbackBody, put_feedback

    with patch("backend.routers.recommendations.rls_connection", _fake_rls), \
         patch("backend.routers.recommendations.set_reco_feedback",
               AsyncMock(return_value=False)):
        with pytest.raises(HTTPException) as exc:
            await put_feedback(
                "22222222-2222-2222-2222-222222222222",
                FeedbackBody(item_index=0, done=True, rating=None),
                user=USER,
            )
    assert exc.value.status_code == 503
    assert "20260922" in exc.value.detail


@pytest.mark.asyncio
async def test_an_admin_is_always_entitled():
    """The owner runs the API key — the Plus paywall gating their own
    testing surface meant the person building the feature could never see
    the generate button (reported twice). Admins bypass both the
    entitlement and the exhaustion gate."""
    drained_free = {**NOT_ENTITLED, "remaining": 0}
    insert = AsyncMock(return_value={"id": "batch-1", "items": []})
    result = await _call(
        force=True,
        **{
            "backend.routers.recommendations.get_allowance":
                AsyncMock(return_value=drained_free),
            "backend.routers.recommendations._is_admin_user":
                AsyncMock(return_value=True),
            "backend.routers.recommendations.insert_recommendation": insert,
        },
    )
    assert result["generating"] is True
    insert.assert_awaited_once()


@pytest.mark.asyncio
async def test_a_failed_draft_is_recorded_with_the_reason_for_admins():
    """A crashed model call must land somewhere visible — the failure is
    stored per (user, language) and served by GET as draft_error, with the
    actual exception named for admins (the owner reads it on the page)."""
    boom = AsyncMock(side_effect=RuntimeError("model exploded"))
    result = await _call(
        force=True,
        **{
            "backend.routers.recommendations.generate_recommendations": boom,
            "backend.routers.recommendations._is_admin_user":
                AsyncMock(return_value=True),
        },
    )
    assert result["generating"] is True
    error = reco_router._DRAFT_ERRORS[(USER["id"], LANG_ID)]
    assert "RuntimeError: model exploded" in error


@pytest.mark.asyncio
async def test_a_failed_draft_stays_vague_for_learners():
    boom = AsyncMock(side_effect=RuntimeError("model exploded"))
    await _call(
        force=True,
        **{
            "backend.routers.recommendations.generate_recommendations": boom,
        },
    )
    error = reco_router._DRAFT_ERRORS[(USER["id"], LANG_ID)]
    assert "model exploded" not in error
    assert "try again" in error


@pytest.mark.asyncio
async def test_a_second_request_joins_the_draft_already_running():
    """The page fires a passive refresh on load AND has a button — an
    impatient second click must join the running draft, not buy another
    model call."""
    release = asyncio.Event()
    calls = 0

    async def slow_generate(**kwargs):
        nonlocal calls
        calls += 1
        await release.wait()
        return [{"type": "book", "title": "x"}]

    patches = _patches(**{
        "backend.routers.recommendations.generate_recommendations": slow_generate,
    })
    for p in patches:
        p.start()
    try:
        first = await refresh_recommendations(LANG_ID, force=True, user=USER)
        await asyncio.sleep(0)  # let the draft reach the model call
        second = await refresh_recommendations(LANG_ID, force=True, user=USER)
        assert first["generating"] and second["generating"]
        release.set()
        await _drain_drafts()
        assert calls == 1
    finally:
        for p in patches:
            p.stop()
