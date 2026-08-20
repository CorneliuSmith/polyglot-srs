"""The Learn tile counts lessons finished today — not rows created today.

The owner's report: five lessons done, "1 / 20 learned today". Four of the
five were re-teaches. An unfinished walkthrough stays suspended and is
re-taught by the next batch (by design), but the re-teach reuses the
original row, and the row remembers the day it was first OFFERED. The tile
was counting user_cards.created_at, so finishing those four scored nothing.

The same column was wrong in the other direction too: a card offered today
and then abandoned counted as learned.

Real Postgres, because every one of those distinctions is a column and a
predicate.
"""
from __future__ import annotations

from backend.repositories.cards import confirm_learn_batch
from backend.repositories.dashboard import get_dashboard_stats

from .conftest import requires_db

pytestmark = requires_db


async def _lang(pool, code: str) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO languages (code, name, rtl) VALUES ($1, $2, false) "
            "ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name RETURNING id",
            code, code.upper(),
        ))


async def _user(pool, email: str) -> str:
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            "INSERT INTO auth.users (email) VALUES ($1) RETURNING id", email
        ))


async def _offer(pool, user: str, lang: str, card_id: str, *, days_ago: int = 0):
    """What a learn batch does: insert the card SUSPENDED. `days_ago` backdates
    created_at, standing in for a walkthrough offered on an earlier day."""
    async with pool.privileged_connection() as conn:
        return str(await conn.fetchval(
            """
            INSERT INTO user_cards
                (user_id, language_id, card_type, card_id,
                 ease_factor, interval, repetitions, streak, lapses,
                 next_review, is_suspended, created_at)
            VALUES ($1, $2, 'vocabulary', $3, 2.5, 0, 0, 0, 0,
                    now(), true, now() - ($4 || ' days')::interval)
            RETURNING id
            """,
            user, lang, card_id, str(days_ago),
        ))


async def _learned_today(pool, user: str, lang: str) -> int:
    async with pool.rls_connection(user) as conn:
        stats = await get_dashboard_stats(conn, user, lang, "UTC")
    return stats["learned_today"]


async def test_finishing_a_re_taught_lesson_counts_today(pool):
    """The owner's exact case: four cards first offered days ago, one new,
    all five finished today. The tile said 1."""
    lang = await _lang(pool, "lt1")
    user = await _user(pool, "relearn@lt1")

    old = [
        await _offer(pool, user, lang, f"1111111{i}-0000-0000-0000-00000000000{i}",
                     days_ago=3)
        for i in range(1, 5)
    ]
    fresh = await _offer(pool, user, lang,
                         "22222222-0000-0000-0000-000000000000")

    async with pool.rls_connection(user) as conn:
        confirmed = await confirm_learn_batch(conn, user, [*old, fresh])

    assert confirmed == 5
    assert await _learned_today(pool, user, lang) == 5


async def test_an_abandoned_walkthrough_counts_for_nothing(pool):
    """Offered today, never answered, still suspended. It used to count: the
    number could be too high and too low in the same session."""
    lang = await _lang(pool, "lt2")
    user = await _user(pool, "abandon@lt2")

    await _offer(pool, user, lang, "33333333-0000-0000-0000-000000000000")

    assert await _learned_today(pool, user, lang) == 0


async def test_a_lesson_finished_yesterday_does_not_count_today(pool):
    """The counter still resets with the learner's day — the whole point of
    a daily goal."""
    lang = await _lang(pool, "lt3")
    user = await _user(pool, "yesterday@lt3")

    card = await _offer(pool, user, lang,
                        "44444444-0000-0000-0000-000000000000", days_ago=1)
    async with pool.rls_connection(user) as conn:
        await confirm_learn_batch(conn, user, [card])
    # Backdate the activation itself: learned yesterday, not offered yesterday.
    async with pool.privileged_connection() as conn:
        await conn.execute(
            "UPDATE user_cards SET learned_at = now() - interval '1 day' "
            "WHERE id = $1",
            card,
        )

    assert await _learned_today(pool, user, lang) == 0


async def test_a_card_created_already_active_still_counts(pool):
    """A grammar point added from the path browser, or a personal cloze from
    your own text, enters the queue at creation and carries no learned_at.
    COALESCE keeps those counted rather than silently dropping them."""
    lang = await _lang(pool, "lt4")
    user = await _user(pool, "direct@lt4")

    async with pool.privileged_connection() as conn:
        await conn.execute(
            """
            INSERT INTO user_cards
                (user_id, language_id, card_type, card_id,
                 ease_factor, interval, repetitions, streak, lapses, next_review)
            VALUES ($1, $2, 'grammar', $3, 2.5, 0, 0, 0, 0, now())
            """,
            user, lang, "55555555-0000-0000-0000-000000000000",
        )

    assert await _learned_today(pool, user, lang) == 1
