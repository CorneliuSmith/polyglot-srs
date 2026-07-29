"""Weekly review digest: the email body, and the send sweep."""
from unittest.mock import AsyncMock, patch

import pytest

from backend.services.digest import DIGEST_HOUR_UTC, digest_html, sweep_weekly_digests

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
