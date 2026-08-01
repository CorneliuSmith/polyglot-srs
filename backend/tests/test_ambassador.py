"""Ambassador: may create accounts, and may do nothing else.

The role exists because invite-only signup made one admin the bottleneck on
every new learner. Its value depends entirely on the boundary holding, so
most of this file is about what an ambassador CANNOT do — a role that only
adds accounts is useful; one that turns out to add accounts *and* read the
roster is a quiet data leak, and one that can grant roles is an admin with
extra steps.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

from backend.repositories.contributor import (
    can_add_accounts,
    can_contribute,
    can_review,
    can_trial_review,
    is_admin,
)


@asynccontextmanager
async def _fake_priv():
    yield AsyncMock()


LANG = "11111111-1111-1111-1111-111111111111"
OTHER = "22222222-2222-2222-2222-222222222222"

AMBASSADOR = [{"language_id": None, "role": "ambassador"}]
ADMIN = [{"language_id": None, "role": "admin"}]
CONTRIBUTOR = [{"language_id": LANG, "role": "contributor"}]
REVIEWER = [{"language_id": LANG, "role": "reviewer"}]
TRIAL = [{"language_id": LANG, "role": "trial_reviewer"}]


class TestWhatItGrants:
    def test_an_ambassador_may_add_accounts(self):
        assert can_add_accounts(AMBASSADOR)

    def test_an_admin_may_too(self):
        assert can_add_accounts(ADMIN)

    def test_a_plain_learner_may_not(self):
        assert not can_add_accounts([])

    def test_the_grant_scope_is_ignored(self):
        """An account belongs to no language, so "ambassador for Spanish"
        cannot mean "may create Spanish accounts" — there is no such object.
        A scoped grant confers exactly the same power as a global one, and
        the Roles panel says so where an admin picks the scope."""
        scoped = [{"language_id": LANG, "role": "ambassador"}]
        assert can_add_accounts(scoped)


class TestWhatItDoesNotGrant:
    """Each of these is a separate way the role could quietly become admin."""

    def test_it_is_not_admin(self):
        assert not is_admin(AMBASSADOR)

    def test_it_cannot_edit_content(self):
        assert not can_contribute(AMBASSADOR, LANG)
        assert not can_contribute(AMBASSADOR, OTHER)

    def test_it_cannot_publish(self):
        assert not can_review(AMBASSADOR, LANG)

    def test_it_cannot_even_open_the_review_queue(self):
        assert not can_trial_review(AMBASSADOR, LANG)


class TestItIsASiblingNotARung:
    """Contributor, tester and ambassador grant unrelated powers — recruit,
    write, check. Collapsing them into a ladder is the tempting refactor and
    would be wrong in both directions."""

    def test_content_roles_cannot_mint_accounts(self):
        assert not can_add_accounts(CONTRIBUTOR)
        assert not can_add_accounts(TRIAL)

    def test_not_even_a_reviewer_can(self):
        # Approving content has never implied creating logins, and a reviewer
        # is trusted for one and not asked about the other.
        assert not can_add_accounts(REVIEWER)

    def test_an_ambassador_can_do_something_a_reviewer_cannot(self):
        assert can_add_accounts(AMBASSADOR) and not can_add_accounts(REVIEWER)

    def test_a_reviewer_can_do_something_an_ambassador_cannot(self):
        assert can_review(REVIEWER, LANG) and not can_review(AMBASSADOR, LANG)

    def test_holding_both_grants_both(self):
        both = AMBASSADOR + REVIEWER
        assert can_add_accounts(both)
        assert can_review(both, LANG)


class TestRoleIsGrantable:
    def test_it_is_in_the_grantable_set(self):
        from backend.routers.contribute import VALID_ROLES

        assert "ambassador" in VALID_ROLES

    def test_the_check_constraint_lists_it(self):
        """The migration and the API must agree, or a grant the UI offers
        fails at the database with a constraint violation."""
        from pathlib import Path

        sql = Path(
            "supabase/migrations/20260912000000_ambassador_role.sql"
        ).read_text(encoding="utf-8")
        from backend.routers.contribute import VALID_ROLES

        for role in VALID_ROLES:
            assert f"'{role}'" in sql, role


class TestTheMigrationWindow:
    """Code ships before `supabase db push` runs. In that window the UI
    offers a role the CHECK constraint rejects, and the owner saw a bare
    "Something went wrong" with nothing naming the cause.
    """

    def test_a_rejected_role_explains_the_missing_migration(self):
        from unittest.mock import AsyncMock, patch

        import asyncpg
        import pytest
        from fastapi import HTTPException

        from backend.routers import contribute as mod

        async def _boom(*a, **k):
            raise asyncpg.exceptions.CheckViolationError("constraint")

        async def _run():
            with patch.object(mod, "_require_admin", new=AsyncMock()), \
                 patch.object(mod, "_resolve_role_target",
                              new=AsyncMock(return_value="uid")), \
                 patch.object(mod, "privileged_connection", _fake_priv), \
                 patch.object(mod, "grant_role", _boom):
                await mod.grant_contributor_role(
                    mod.RoleGrant(user_id="uid", role="ambassador"),
                    user={"id": "admin-id"},
                )

        import asyncio

        with pytest.raises(HTTPException) as exc:
            asyncio.run(_run())
        assert exc.value.status_code == 503
        detail = exc.value.detail
        # It must name the fix, not just fail politely.
        assert "supabase db push" in detail
        assert "ambassador" in detail

    def test_the_validation_error_lists_the_real_roles(self):
        """The hardcoded message still said "contributor, reviewer, or
        admin" two roles after that stopped being true."""
        import asyncio

        import pytest
        from fastapi import HTTPException

        from backend.routers import contribute as mod

        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                mod._resolve_role_target(
                    mod.RoleGrant(user_id="uid", role="wizard")
                )
            )
        assert exc.value.status_code == 422
        for role in mod.VALID_ROLES:
            assert role in exc.value.detail
