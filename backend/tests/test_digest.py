"""Weekly review digest: the email body, and the send sweeps."""
from contextlib import ExitStack
from unittest.mock import AsyncMock, patch

import pytest

from backend.services.digest import (
    DIGEST_HOUR_UTC,
    RECS_HOUR_UTC,
    digest_html,
    picks_html,
    sweep_weekly_digests,
    sweep_weekly_recommendations,
)

APP = "https://app.example"

RECOS = [
    {"type": "book", "title": "Cien años de soledad", "creator": "García Márquez",
     "year": "1967", "blurb": "A family saga in Macondo.",
     "why": "You said you like magical realism, and the prose sits at your B1."},
    {"type": "podcast", "title": "Radio Ambulante", "blurb": "Latin American stories.",
     "why": "Clear narration, 20 minutes an episode."},
]


class TestDigestBody:
    def test_leads_with_the_week_and_links_the_review_queue(self):
        html = digest_html(
            reviews=42, accuracy=88, learned=310, due=12,
            reco_items=[], app_url=APP,
        )
        assert "42" in html
        assert "88%" in html
        assert "310" in html
        assert f"{APP}/review" in html
        # The CTA names the actual work waiting, not a generic "open the app".
        assert "Review 12 cards" in html

    def test_an_empty_week_invites_rather_than_scolds(self):
        html = digest_html(
            reviews=0, accuracy=None, learned=100, due=0,
            reco_items=[], app_url=APP,
        )
        assert "completely fine" in html
        # No accuracy stat when there's nothing to be accurate about — a 0%
        # would be a false and discouraging number. (Matching the label, not
        # the digits: width="100%" lives in the table markup.)
        assert "accuracy" not in html
        assert "Open PolyglotSRS" in html

    def test_singular_review_reads_correctly(self):
        html = digest_html(
            reviews=1, accuracy=100, learned=5, due=1,
            reco_items=[], app_url=APP,
        )
        assert "1</b> review this week" in html
        assert "Review 1 card<" in html

    def test_recommendations_ride_along_with_their_why(self):
        html = digest_html(
            reviews=10, accuracy=70, learned=50, due=3,
            reco_items=RECOS, app_url=APP,
        )
        assert "Cien años de soledad" in html
        assert "Radio Ambulante" in html
        # The "why this fits you" line is the whole point of a recommendation.
        assert "magical realism" in html

    def test_no_recommendation_block_at_all_when_there_are_none(self):
        html = digest_html(
            reviews=10, accuracy=70, learned=50, due=3,
            reco_items=[], app_url=APP,
        )
        assert "read, watch or listen" not in html

    def test_caps_the_picks_so_the_email_stays_scannable(self):
        many = [{**RECOS[0], "title": f"Book {i}"} for i in range(10)]
        html = digest_html(
            reviews=5, accuracy=80, learned=20, due=0,
            reco_items=many, app_url=APP,
        )
        assert "Book 3" in html
        assert "Book 4" not in html

    def test_escapes_hostile_content_from_a_generated_pick(self):
        html = digest_html(
            reviews=5, accuracy=80, learned=20, due=0,
            reco_items=[{"type": "book", "title": "<script>alert(1)</script>",
                         "blurb": "", "why": ""}],
            app_url=APP,
        )
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_always_says_how_to_turn_it_off(self):
        html = digest_html(
            reviews=5, accuracy=80, learned=20, due=0,
            reco_items=[], app_url=APP,
        )
        assert "turn it off" in html.lower()
        assert f"{APP}/account" in html

    def test_survives_a_pick_with_only_a_title(self):
        html = digest_html(
            reviews=5, accuracy=80, learned=20, due=0,
            reco_items=[{"title": "Just A Title"}], app_url=APP,
        )
        assert "Just A Title" in html

    def test_skips_a_pick_with_no_title_rather_than_rendering_a_blank_row(self):
        html = digest_html(
            reviews=5, accuracy=80, learned=20, due=0,
            reco_items=[{"blurb": "orphaned"}], app_url=APP,
        )
        assert "orphaned" not in html


class TestSweep:
    @pytest.mark.asyncio
    async def test_sends_nothing_when_email_is_not_configured(self):
        conn = AsyncMock()
        with patch("backend.services.digest.email_configured", return_value=False):
            assert await sweep_weekly_digests(conn) == 0
        # Crucially it must not have burned anyone's last-sent stamp.
        conn.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_only_runs_at_the_digest_hour(self):
        conn = AsyncMock()
        with patch("backend.services.digest.email_configured", return_value=True), \
             patch("backend.services.digest.datetime") as dt:
            dt.now.return_value.hour = (DIGEST_HOUR_UTC + 1) % 24
            assert await sweep_weekly_digests(conn) == 0
        conn.fetch.assert_not_called()

    @pytest.mark.asyncio
    async def test_stamps_only_on_an_accepted_send(self):
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[
            {"id": "u1", "email": "a@t", "reviews": 10, "correct": 8,
             "learned": 40, "due": 2, "reco_items": []},
        ])
        with patch("backend.services.digest.email_configured", return_value=True), \
             patch("backend.services.digest.datetime") as dt, \
             patch("backend.services.digest.send_email",
                   new=AsyncMock(return_value=False)):
            dt.now.return_value.hour = DIGEST_HOUR_UTC
            assert await sweep_weekly_digests(conn) == 0
        # A refused send must retry next hour, not be recorded as delivered.
        conn.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_a_successful_send_is_stamped_and_counted(self):
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[
            {"id": "u1", "email": "a@t", "reviews": 10, "correct": 8,
             "learned": 40, "due": 2, "reco_items": RECOS},
        ])
        with patch("backend.services.digest.email_configured", return_value=True), \
             patch("backend.services.digest.datetime") as dt, \
             patch("backend.services.digest.send_email",
                   new=AsyncMock(return_value=True)) as send:
            dt.now.return_value.hour = DIGEST_HOUR_UTC
            assert await sweep_weekly_digests(conn) == 1
        conn.execute.assert_awaited_once()
        # 8 of 10 correct → 80%, and the picks made it into the body.
        body = send.await_args.args[2]
        assert "80%" in body
        assert "Cien años de soledad" in body

    @pytest.mark.asyncio
    async def test_reco_items_stored_as_json_text_still_render(self):
        # asyncpg hands JSONB back as a str unless a codec is registered.
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[
            {"id": "u1", "email": "a@t", "reviews": 3, "correct": 3,
             "learned": 9, "due": 0,
             "reco_items": '[{"type":"book","title":"From JSON","blurb":"","why":""}]'},
        ])
        with patch("backend.services.digest.email_configured", return_value=True), \
             patch("backend.services.digest.datetime") as dt, \
             patch("backend.services.digest.send_email",
                   new=AsyncMock(return_value=True)) as send:
            dt.now.return_value.hour = DIGEST_HOUR_UTC
            await sweep_weekly_digests(conn)
        assert "From JSON" in send.await_args.args[2]

    @pytest.mark.asyncio
    async def test_an_account_with_no_email_is_skipped(self):
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[
            {"id": "u1", "email": None, "reviews": 5, "correct": 5,
             "learned": 10, "due": 1, "reco_items": []},
        ])
        with patch("backend.services.digest.email_configured", return_value=True), \
             patch("backend.services.digest.datetime") as dt, \
             patch("backend.services.digest.send_email",
                   new=AsyncMock(return_value=True)) as send:
            dt.now.return_value.hour = DIGEST_HOUR_UTC
            assert await sweep_weekly_digests(conn) == 0
        send.assert_not_called()

    @pytest.mark.asyncio
    async def test_a_zero_review_week_still_gets_its_digest(self):
        # Unlike the daily reminder (which stays quiet when nothing is due),
        # the weekly digest is a check-in — going silent on the person who
        # lapsed is exactly backwards.
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[
            {"id": "u1", "email": "a@t", "reviews": 0, "correct": 0,
             "learned": 40, "due": 5, "reco_items": []},
        ])
        with patch("backend.services.digest.email_configured", return_value=True), \
             patch("backend.services.digest.datetime") as dt, \
             patch("backend.services.digest.send_email",
                   new=AsyncMock(return_value=True)) as send:
            dt.now.return_value.hour = DIGEST_HOUR_UTC
            assert await sweep_weekly_digests(conn) == 1
        assert "completely fine" in send.await_args.args[2]


class TestWeeklyRecsSweep:
    """The server-side engine. Batches used to be drafted only when the
    learner OPENED the page (the client fired the refresh), so anyone who
    didn't visit got nothing new and no email ever arrived. The sweep now
    drafts the week's picks itself and mails them, spending one unit of the
    learner's monthly allowance per batch."""

    ROW = {
        "user_id": "u1", "language_id": "l1", "email": "kate@t",
        "language_code": "ca", "language_name": "Catalan",
        "tutor_model": None,
    }
    ALLOWED = {"entitled": True, "unlimited": False, "remaining": 50}

    def _stack(self, conn, *, allowance, items):
        """The full patch set for one sweep run at the right hour."""
        stack = ExitStack()
        p = stack.enter_context
        p(patch("backend.services.digest.datetime")).now.return_value.hour = (
            RECS_HOUR_UTC
        )
        p(patch("backend.services.allowance.get_allowance",
                new=AsyncMock(return_value=allowance)))
        # Not an admin unless a test says so — the admin bypass must not
        # mask the entitlement gates these tests exercise.
        p(patch("backend.repositories.contributor.get_roles",
                new=AsyncMock(return_value=[])))
        p(patch("backend.repositories.recommendations.get_reco_profile",
                new=AsyncMock(return_value={
                    "enabled": True, "about": "crime shows",
                    "genres": ["True crime"], "media_types": ["series"]})))
        p(patch("backend.repositories.tutor.get_study_stats",
                new=AsyncMock(return_value={
                    "highest_level_reached": "B1", "learned_cards": 300})))
        self.generate = p(patch(
            "backend.services.recommend.generate_recommendations",
            new=AsyncMock(return_value=items)))
        self.insert = p(patch(
            "backend.repositories.recommendations.insert_recommendation",
            new=AsyncMock(return_value={"id": "b1"})))
        p(patch("backend.repositories.recommendations.recommended_titles",
                new=AsyncMock(return_value=["Old Pick"])))
        p(patch("backend.repositories.recommendations.rated_titles",
                new=AsyncMock(return_value=[])))
        self.usage = p(patch(
            "backend.repositories.tutor.log_tutor_usage", new=AsyncMock()))
        p(patch("backend.services.digest.email_configured", return_value=True))
        self.send = p(patch("backend.services.digest.send_email",
                            new=AsyncMock(return_value=True)))
        return stack

    def _conn(self, rows, lock=True):
        conn = AsyncMock()
        conn.fetchval = AsyncMock(return_value=lock)  # the advisory lock
        conn.fetch = AsyncMock(return_value=rows)
        return conn

    @pytest.mark.asyncio
    async def test_drafts_spends_and_emails_with_the_reasons(self):
        conn = self._conn([self.ROW])
        with self._stack(conn, allowance=self.ALLOWED, items=RECOS):
            assert await sweep_weekly_recommendations(conn) == 1
        # Grounded in the learner's CURRENT level each week, and never
        # repeating an earlier pick.
        assert self.generate.await_args.kwargs["level"] == "B1"
        assert self.generate.await_args.kwargs["exclude_titles"] == ["Old Pick"]
        self.insert.assert_awaited_once()
        # One unit of the monthly pool, under the counted 'recs' kind.
        assert self.usage.await_args.kwargs["kind"] == "recs"
        # The email names the language and carries every pick's WHY.
        subject, body = self.send.await_args.args[1:3]
        assert "Catalan" in subject
        assert "magical realism" in body
        assert "/recommendations" in body

    @pytest.mark.asyncio
    async def test_runs_only_at_its_hour(self):
        conn = self._conn([self.ROW])
        with patch("backend.services.digest.datetime") as dt:
            dt.now.return_value.hour = (RECS_HOUR_UTC + 1) % 24
            assert await sweep_weekly_recommendations(conn) == 0
        conn.fetch.assert_not_called()

    @pytest.mark.asyncio
    async def test_an_unentitled_learner_costs_nothing(self):
        conn = self._conn([self.ROW])
        with self._stack(conn,
                         allowance={"entitled": False, "unlimited": False,
                                    "remaining": 0},
                         items=RECOS):
            assert await sweep_weekly_recommendations(conn) == 0
        self.generate.assert_not_called()
        self.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_an_admin_drafts_without_a_plan(self):
        # The router's admin bypass, mirrored here — without it the sweep
        # silently skipped the owner every week ("the recommendations never
        # come through"): admin accounts aren't Plus-entitled.
        conn = self._conn([self.ROW])
        with self._stack(conn,
                         allowance={"entitled": False, "unlimited": False,
                                    "remaining": 0},
                         items=RECOS):
            with patch("backend.repositories.contributor.get_roles",
                       new=AsyncMock(return_value=[
                           {"language_id": None, "role": "admin"}])):
                assert await sweep_weekly_recommendations(conn) == 1
        self.insert.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_an_exhausted_month_waits_for_the_reset(self):
        conn = self._conn([self.ROW])
        with self._stack(conn,
                         allowance={"entitled": True, "unlimited": False,
                                    "remaining": 0},
                         items=RECOS):
            assert await sweep_weekly_recommendations(conn) == 0
        self.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_only_one_worker_runs_the_pass(self):
        # Every uvicorn worker runs the loop; the advisory lock makes sure
        # only one of them drafts (and pays for) a given week.
        conn = self._conn([self.ROW], lock=False)
        with self._stack(conn, allowance=self.ALLOWED, items=RECOS):
            assert await sweep_weekly_recommendations(conn) == 0
        conn.fetch.assert_not_called()

    @pytest.mark.asyncio
    async def test_the_batch_lands_even_when_email_is_down(self):
        # Log-only email must not stop the app itself getting fresh picks.
        conn = self._conn([self.ROW])
        with self._stack(conn, allowance=self.ALLOWED, items=RECOS):
            with patch("backend.services.digest.email_configured",
                       return_value=False):
                assert await sweep_weekly_recommendations(conn) == 1
        self.insert.assert_awaited_once()
        self.send.assert_not_called()


class TestPicksEmail:
    def test_names_the_language_and_shows_every_why(self):
        html = picks_html(language_name="Catalan", items=RECOS, app_url=APP)
        assert "Your weekly Catalan picks" in html
        assert "Cien años de soledad" in html
        assert "magical realism" in html
        assert f"{APP}/recommendations" in html
        # And how to turn it off — every recurring email owes people that.
        assert "turn them off" in html
