"""General app feedback: submit, read your own, triage."""
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from backend.routers.feedback import (
    FeedbackCreate,
    FeedbackTriage,
    all_feedback,
    create_feedback,
    my_feedback,
    triage_feedback,
)
from backend.tests.fakes import mock_conn


@asynccontextmanager
async def _fake_rls(user_id: str):
    yield mock_conn()


@asynccontextmanager
async def _fake_priv():
    yield mock_conn()


@pytest.fixture(autouse=True)
def _no_pool():
    """Every endpoint opens a connection; the repository calls are patched
    per-test, so the connections themselves just need to exist."""
    with patch("backend.routers.feedback.rls_connection", _fake_rls), \
         patch("backend.routers.feedback.privileged_connection", _fake_priv):
        yield


USER = {"id": "user-1"}
ADMIN_ROLES = [{"role": "admin", "language_id": None}]
CONTRIBUTOR_ROLES = [{"role": "contributor", "language_id": "lang-es"}]


@pytest.mark.asyncio
async def test_feedback_is_recorded_with_its_context():
    with patch(
        "backend.routers.feedback.submit_feedback",
        new=AsyncMock(return_value="fb-1"),
    ) as submit:
        result = await create_feedback(
            FeedbackCreate(
                category="bug",
                message="The keyboard is cut off on my phone",
                language_id="lang-ar",
                page="learn",
            ),
            user=USER,
        )
    assert result == {"id": "fb-1"}
    kwargs = submit.await_args.kwargs
    # Page and language ride along so nobody has to ask "where were you?".
    assert kwargs["page"] == "learn"
    assert kwargs["language_id"] == "lang-ar"
    assert kwargs["category"] == "bug"


@pytest.mark.asyncio
async def test_feedback_about_the_app_needs_no_language():
    with patch(
        "backend.routers.feedback.submit_feedback",
        new=AsyncMock(return_value="fb-2"),
    ) as submit:
        await create_feedback(
            FeedbackCreate(category="idea", message="Add a dark map view"),
            user=USER,
        )
    assert submit.await_args.kwargs["language_id"] is None


@pytest.mark.asyncio
async def test_an_invented_category_is_rejected():
    with pytest.raises(HTTPException) as exc:
        await create_feedback(
            FeedbackCreate.model_construct(
                category="urgent", message="hello", language_id=None, page=None
            ),
            user=USER,
        )
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_a_missing_table_says_so_instead_of_500ing():
    # The repository returns None when migration 20260906 has not been applied.
    with patch(
        "backend.routers.feedback.submit_feedback", new=AsyncMock(return_value=None)
    ):
        with pytest.raises(HTTPException) as exc:
            await create_feedback(
                FeedbackCreate(category="bug", message="broken"), user=USER
            )
    assert exc.value.status_code == 503
    assert "20260906" in exc.value.detail


@pytest.mark.asyncio
async def test_you_can_read_your_own_feedback_without_a_role():
    with patch(
        "backend.routers.feedback.list_my_feedback",
        new=AsyncMock(return_value=[{"id": "fb-1", "message": "hi"}]),
    ):
        result = await my_feedback(user=USER)
    assert result["feedback"][0]["id"] == "fb-1"


@pytest.mark.asyncio
async def test_a_plain_learner_cannot_read_everyone_elses():
    with patch(
        "backend.routers.feedback.get_roles", new=AsyncMock(return_value=[])
    ):
        with pytest.raises(HTTPException) as exc:
            await all_feedback(user=USER)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_a_contributor_can_read_the_queue():
    # Most feedback is a content complaint; contributors are who fixes those.
    with patch(
        "backend.routers.feedback.get_roles",
        new=AsyncMock(return_value=CONTRIBUTOR_ROLES),
    ), patch(
        "backend.routers.feedback.list_feedback", new=AsyncMock(return_value=[])
    ), patch(
        "backend.routers.feedback.count_open_feedback", new=AsyncMock(return_value=3)
    ):
        result = await all_feedback(user=USER)
    assert result["open_count"] == 3


@pytest.mark.asyncio
async def test_only_an_admin_can_triage():
    with patch(
        "backend.routers.feedback.get_roles",
        new=AsyncMock(return_value=CONTRIBUTOR_ROLES),
    ):
        with pytest.raises(HTTPException) as exc:
            await triage_feedback(
                "fb-1", FeedbackTriage(status="closed"), user=USER
            )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_triage_moves_an_item_and_keeps_the_note():
    with patch(
        "backend.routers.feedback.get_roles", new=AsyncMock(return_value=ADMIN_ROLES)
    ), patch(
        "backend.routers.feedback.set_feedback_status",
        new=AsyncMock(return_value=True),
    ) as setter:
        result = await triage_feedback(
            "fb-1",
            FeedbackTriage(status="triaged", admin_note="Reproduced on iOS"),
            user=USER,
        )
    assert result == {"updated": True}
    assert setter.await_args.kwargs["admin_note"] == "Reproduced on iOS"


@pytest.mark.asyncio
async def test_an_unknown_status_is_rejected():
    with patch(
        "backend.routers.feedback.get_roles", new=AsyncMock(return_value=ADMIN_ROLES)
    ):
        with pytest.raises(HTTPException) as exc:
            await triage_feedback(
                "fb-1", FeedbackTriage.model_construct(status="wontfix"), user=USER
            )
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_triaging_something_that_is_gone_is_a_404():
    with patch(
        "backend.routers.feedback.get_roles", new=AsyncMock(return_value=ADMIN_ROLES)
    ), patch(
        "backend.routers.feedback.set_feedback_status",
        new=AsyncMock(return_value=False),
    ):
        with pytest.raises(HTTPException) as exc:
            await triage_feedback(
                "gone", FeedbackTriage(status="closed"), user=USER
            )
    assert exc.value.status_code == 404


class TestUnassignedScope:
    """"Not about one language" is a scope of its own in the triage panel —
    the reports about the app as a whole, not the course the sender
    happened to have open."""

    async def test_the_filter_reaches_the_sql(self):
        from backend.repositories.feedback import list_feedback

        conn = mock_conn()
        conn.fetch = AsyncMock(return_value=[])
        await list_feedback(conn, unassigned=True)
        sql, *args = conn.fetch.await_args.args
        assert "language_id IS NULL" in sql
        assert args[-1] is True

    async def test_off_by_default_so_existing_callers_see_everything(self):
        from backend.repositories.feedback import list_feedback

        conn = mock_conn()
        conn.fetch = AsyncMock(return_value=[])
        await list_feedback(conn)
        assert conn.fetch.await_args.args[-1] is False
