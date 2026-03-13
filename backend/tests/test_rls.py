"""RLS integration tests — require a running Supabase with test users."""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set — skipping RLS integration tests",
)

# TODO: These tests require two Supabase auth users to be created.
# Setup: create user_a and user_b via Supabase Auth, insert test
# user_cards for each. Use rls_connection(user_a_id) and
# rls_connection(user_b_id) to verify cross-user isolation.

USER_A_ID = "00000000-0000-0000-0000-000000000001"
USER_B_ID = "00000000-0000-0000-0000-000000000002"


@pytest.mark.asyncio
async def test_user_cannot_see_other_user_cards():
    """User A should not see User B's cards via RLS."""
    from backend.repositories.pool import init_pool, close_pool, rls_connection

    await init_pool(os.environ["DATABASE_URL"])
    try:
        # Insert a card for user_b, then query as user_a
        async with rls_connection(USER_B_ID) as conn:
            # TODO: INSERT test card for USER_B
            pass

        async with rls_connection(USER_A_ID) as conn:
            rows = await conn.fetch(
                "SELECT * FROM user_cards WHERE user_id = $1", USER_B_ID
            )
            assert len(rows) == 0, "User A can see User B's cards — RLS failure"
    finally:
        await close_pool()


@pytest.mark.asyncio
async def test_user_cannot_insert_card_for_other_user():
    """INSERT with mismatched user_id should be rejected by RLS."""
    from backend.repositories.pool import init_pool, close_pool, rls_connection

    await init_pool(os.environ["DATABASE_URL"])
    try:
        async with rls_connection(USER_A_ID) as conn:
            # TODO: Attempt INSERT into user_cards with user_id = USER_B_ID
            # Should raise an exception due to RLS WITH CHECK
            pass
    finally:
        await close_pool()


@pytest.mark.asyncio
async def test_review_log_is_append_only():
    """UPDATE and DELETE on review_log should be blocked by RLS."""
    from backend.repositories.pool import init_pool, close_pool, rls_connection

    await init_pool(os.environ["DATABASE_URL"])
    try:
        async with rls_connection(USER_A_ID) as conn:
            # TODO: INSERT a review_log entry, then attempt UPDATE and DELETE
            # Both should fail due to append-only RLS policy
            pass
    finally:
        await close_pool()
