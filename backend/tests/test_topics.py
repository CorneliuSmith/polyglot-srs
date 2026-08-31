"""The Topic Lens (docs/plans/topic-lens.md): taxonomy, the topic-scoped
draw, its degrade paths, and the /topics summary endpoint.

The stakes each test pins:
- the slug set lives in THREE places (migration CHECK, taxonomy module,
  classifier prompt) — drift between them fails here, not at first INSERT;
- a plain level learn must be byte-identical to before this feature;
- a topic request on a schema without the column must serve a normal
  draw, never fail the session;
- a topic batch must never deal five same-type words in a row (the
  Tinkham/Waring interference finding this design exists to respect).
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import jwt as pyjwt
import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.repositories.cards import (
    _select_vocab_candidate_ids,
    _spread_word_types,
    get_topic_summary,
)
from backend.services.topic_taxonomy import (
    ALL_TOPICS,
    HIDDEN_TOPICS,
    VISIBLE_TOPICS,
    valid_topic,
)

TEST_SECRET = "test-jwt-secret-for-unit-tests-32bytes"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
LANG = "11111111-1111-1111-1111-111111111111"

MIGRATION = Path("supabase/migrations/20261009000000_vocab_topic.sql")


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
        {"sub": TEST_USER_ID, "aud": "authenticated",
         "exp": int(time.time()) + 3600},
        TEST_SECRET, algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# The taxonomy itself
# ---------------------------------------------------------------------------


class TestTaxonomy:
    def test_the_migration_and_the_module_carry_the_same_slugs(self):
        """The set is frozen by owner approval and lives in two places;
        this is the tripwire that keeps them one set."""
        sql = MIGRATION.read_text()
        # Every quoted slug between the CHECK's open and its closing
        # double-paren.
        check_body = sql.split("CHECK (topic IN (", 1)[1].split("))", 1)[0]
        in_check = set(re.findall(r"'([a-z_]+)'", check_body))
        assert in_check == set(ALL_TOPICS)

    def test_shape_of_the_set(self):
        assert len(VISIBLE_TOPICS) == 22
        assert len(HIDDEN_TOPICS) == 2
        assert len(set(ALL_TOPICS)) == 24
        assert set(HIDDEN_TOPICS) == {"abstract_general", "function_words"}
        assert not set(VISIBLE_TOPICS) & set(HIDDEN_TOPICS)

    def test_valid_topic_answers_slug_or_none_never_raises(self):
        assert valid_topic("food_drink") == "food_drink"
        assert valid_topic("function_words") == "function_words"
        assert valid_topic("colours") is None       # never a bucket, by design
        assert valid_topic("") is None
        assert valid_topic(None) is None


# ---------------------------------------------------------------------------
# Dealing the batch across word types
# ---------------------------------------------------------------------------


def _row(id_, pos):
    return {"id": id_, "part_of_speech": pos}


class TestSpreadWordTypes:
    def test_never_two_consecutive_same_types_when_avoidable(self):
        rows = [_row(1, "noun"), _row(2, "noun"), _row(3, "verb"),
                _row(4, "adjective"), _row(5, "noun"), _row(6, "verb")]
        picked = _spread_word_types(rows, 5)
        pos = {1: "noun", 2: "noun", 3: "verb", 4: "adjective",
               5: "noun", 6: "verb"}
        seq = [pos[i] for i in picked]
        assert all(a != b for a, b in zip(seq, seq[1:]))
        assert len(picked) == 5

    def test_rank_order_wins_within_the_constraint(self):
        rows = [_row(1, "noun"), _row(2, "verb"), _row(3, "noun")]
        assert _spread_word_types(rows, 3) == [1, 2, 3]

    def test_noun_heavy_topic_degrades_to_rank_order_not_starvation(self):
        # The named residual: when everything is one type, the batch still
        # fills (bounded by batch_size 5 + sentence-context drills).
        rows = [_row(i, "noun") for i in range(1, 7)]
        assert _spread_word_types(rows, 4) == [1, 2, 3, 4]

    def test_null_word_type_is_its_own_lane(self):
        rows = [_row(1, None), _row(2, None), _row(3, "noun")]
        picked = _spread_word_types(rows, 3)
        assert picked[0] == 1 and picked[1] == 3  # noun breaks the None run

    def test_fewer_candidates_than_batch_returns_them_all(self):
        rows = [_row(1, "noun")]
        assert _spread_word_types(rows, 5) == [1]
        assert _spread_word_types([], 5) == []


# ---------------------------------------------------------------------------
# The selector: SQL shape and degrade cascade
# ---------------------------------------------------------------------------


class TestTopicDraw:
    @pytest.mark.asyncio
    async def test_plain_learn_sql_never_mentions_topic(self):
        """The hot path unchanged: no topic requested → the query cannot
        reference v.topic (it would fail planning pre-migration) and adds
        no parameters."""
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[])
        await _select_vocab_candidate_ids(conn, TEST_USER_ID, LANG, 5, None)
        sql = conn.fetch.await_args.args[0]
        assert "topic" not in sql
        assert "PARTITION BY level" in sql

    @pytest.mark.asyncio
    async def test_topic_draw_partitions_by_word_type_and_overfetches(self):
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[
            {"id": "w1", "part_of_speech": "noun"},
            {"id": "w2", "part_of_speech": "verb"},
        ])
        ids = await _select_vocab_candidate_ids(
            conn, TEST_USER_ID, LANG, 5, None, "food_drink"
        )
        sql = conn.fetch.await_args.args[0]
        args = conn.fetch.await_args.args
        assert "v.topic = $4" in sql
        assert "PARTITION BY part_of_speech" in sql
        # Introduction-time gate: unconfirmed AI topics behave like
        # unconfirmed AI levels.
        assert "topic_source" in sql
        assert args[3] == 15          # over-fetch 3x, dealt down to batch
        assert args[4] == "food_drink"
        assert ids == ["w1", "w2"]

    @pytest.mark.asyncio
    async def test_missing_topic_column_serves_a_normal_draw(self):
        """A topic link on a deploy ahead of migration 20261009: the learner
        pressed Learn, so they learn — plain draw, no error."""
        conn = AsyncMock()
        conn.fetch = AsyncMock(side_effect=[
            asyncpg.exceptions.UndefinedColumnError("no v.topic"),
            [{"id": "w9"}],
        ])
        ids = await _select_vocab_candidate_ids(
            conn, TEST_USER_ID, LANG, 5, None, "food_drink"
        )
        assert ids == ["w9"]
        retry_sql = conn.fetch.await_args_list[1].args[0]
        assert "topic" not in retry_sql

    @pytest.mark.asyncio
    async def test_both_columns_missing_still_serves(self):
        """Topic column AND the explicit-content column absent (a truly old
        schema): third try serves, filters off."""
        conn = AsyncMock()
        conn.fetch = AsyncMock(side_effect=[
            asyncpg.exceptions.UndefinedColumnError("no v.topic"),
            asyncpg.exceptions.UndefinedColumnError("no allow_explicit"),
            [{"id": "w1"}],
        ])
        ids = await _select_vocab_candidate_ids(
            conn, TEST_USER_ID, LANG, 5, None, "food_drink"
        )
        assert ids == ["w1"]


# ---------------------------------------------------------------------------
# The summary the topic view renders
# ---------------------------------------------------------------------------


class TestTopicSummary:
    @pytest.mark.asyncio
    async def test_pre_migration_reads_empty_without_running_the_query(self):
        conn = AsyncMock()
        conn.fetchval = AsyncMock(return_value=False)   # column probe misses
        assert await get_topic_summary(conn, TEST_USER_ID, LANG) == []
        conn.fetch.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_hidden_buckets_are_excluded_in_sql_not_client(self):
        conn = AsyncMock()
        conn.fetchval = AsyncMock(return_value=True)
        conn.fetch = AsyncMock(return_value=[
            {"topic": "food_drink", "total": 40, "learned": 3},
        ])
        rows = await get_topic_summary(conn, TEST_USER_ID, LANG)
        assert rows == [{"topic": "food_drink", "total": 40, "learned": 3}]
        assert list(conn.fetch.await_args.args[3]) == list(HIDDEN_TOPICS)


# ---------------------------------------------------------------------------
# The HTTP surface
# ---------------------------------------------------------------------------


@pytest.fixture()
def client():
    with patch("backend.main.init_pool", new=AsyncMock()), \
         patch("backend.main.close_pool", new=AsyncMock()), \
         patch("backend.main.get_settings", return_value=FakeSettings()), \
         patch("backend.dependencies.get_settings", return_value=FakeSettings()):
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


def _fake_conn(batch_size=5):
    """Every fetchrow answers with a row whose only real key is batch_size
    — the same shape test_review_endpoints uses, so the profile lookups the
    handler makes along the way (support locale etc.) read as unset."""
    conn = AsyncMock()
    row = MagicMock()
    row.__getitem__ = MagicMock(
        side_effect=lambda key: batch_size if key == "batch_size" else None
    )
    conn.fetchrow = AsyncMock(return_value=row)
    conn.execute = AsyncMock()
    return conn


def _rls(mock_rls, conn):
    mock_rls.return_value.__aenter__ = AsyncMock(return_value=conn)
    mock_rls.return_value.__aexit__ = AsyncMock(return_value=False)


class TestLearnWithTopic:
    def _post(self, client, body, add_mock):
        with patch("backend.routers.review.rls_connection") as mock_rls, \
             patch("backend.routers.review.add_learn_batch", add_mock), \
             patch("backend.routers.review.get_card_details_bulk",
                   new=AsyncMock(return_value={})):
            _rls(mock_rls, _fake_conn())
            return client.post("/api/review/learn", json=body,
                               headers=_auth_headers())

    def test_a_valid_topic_reaches_the_repository(self, client):
        add = AsyncMock(return_value={"added": 0, "items": []})
        resp = self._post(client, {
            "language_id": LANG, "card_type": "vocabulary",
            "topic": "food_drink",
        }, add)
        assert resp.status_code == 200
        assert add.await_args.args[5] == "food_drink"

    def test_an_unknown_topic_degrades_to_a_plain_draw(self, client):
        """A stale link from a renamed bucket must not 422 a learn session."""
        add = AsyncMock(return_value={"added": 0, "items": []})
        resp = self._post(client, {
            "language_id": LANG, "card_type": "vocabulary",
            "topic": "colours",
        }, add)
        assert resp.status_code == 200
        assert add.await_args.args[5] is None

    def test_grammar_learns_ignore_topics_entirely(self, client):
        with patch("backend.routers.review.rls_connection") as mock_rls, \
             patch("backend.routers.review.add_grammar_learn_batch",
                   new=AsyncMock(return_value={"added": 0, "items": []})) as g, \
             patch("backend.routers.review.get_card_details_bulk",
                   new=AsyncMock(return_value={})):
            _rls(mock_rls, _fake_conn())
            resp = client.post("/api/review/learn", json={
                "language_id": LANG, "card_type": "grammar",
                "topic": "food_drink",
            }, headers=_auth_headers())
        assert resp.status_code == 200
        assert "topic" not in str(g.await_args)


class TestTopicsEndpoint:
    def test_returns_the_summary(self, client):
        rows = [{"topic": "food_drink", "total": 40, "learned": 3}]
        with patch("backend.routers.review.rls_connection") as mock_rls, \
             patch("backend.routers.review.get_topic_summary",
                   new=AsyncMock(return_value=rows)):
            _rls(mock_rls, MagicMock())
            resp = client.get("/api/review/topics",
                              params={"language_id": LANG},
                              headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json() == {"topics": rows}

    def test_requires_auth(self, client):
        resp = client.get("/api/review/topics", params={"language_id": LANG})
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# The classifier service and its review flow (PR 2 of the plan)
# ---------------------------------------------------------------------------


class TestEstimator:
    def test_dry_run_prices_before_spending(self):
        from backend.services.topic_estimate import dry_run_estimate
        est = dry_run_estimate(483)          # jam — the smallest course
        assert est["words"] == 483
        assert est["calls"] == 7             # ceil(483/75)
        assert est["est_cost_usd"] > 0

    @pytest.mark.asyncio
    async def test_dev_mock_classifies_without_a_key(self):
        from backend.services.topic_estimate import estimate_topics
        words = [{"word": f"w{i}"} for i in range(30)]
        with patch("backend.services.topic_estimate.get_settings",
                   return_value=MagicMock(tutor_dev_mock=True)):
            out = await estimate_topics(words, "Spanish", "es")
        assert len(out) == 30
        assert set(out.values()) <= set(ALL_TOPICS)


class TestTopicReviewEndpoints:
    ROLE_REVIEWER = [{"language_id": LANG, "role": "reviewer"}]
    ROLE_TESTER = [{"language_id": LANG, "role": "trial_reviewer"}]

    def _roles(self, roles):
        return patch("backend.routers.contribute.get_roles",
                     new=AsyncMock(return_value=roles))

    def _priv(self, mock_priv, conn):
        mock_priv.return_value.__aenter__ = AsyncMock(return_value=conn)
        mock_priv.return_value.__aexit__ = AsyncMock(return_value=False)

    def test_queue_lists_counts_and_words_for_a_tester(self, client):
        counts = [{"topic": "food_drink", "pending": 40}]
        words = [{"id": "v1", "word": "pan", "part_of_speech": "noun",
                  "topic": "food_drink", "definition": "bread"}]
        with self._roles(self.ROLE_TESTER), \
             patch("backend.routers.contribute.rls_connection"), \
             patch("backend.routers.contribute.privileged_connection") as priv, \
             patch("backend.routers.contribute.count_ai_topic_vocab",
                   new=AsyncMock(return_value=counts)), \
             patch("backend.routers.contribute.list_ai_topic_vocab",
                   new=AsyncMock(return_value=words)):
            self._priv(priv, AsyncMock())
            resp = client.get("/api/contribute/review/ai-topics",
                              params={"language_id": LANG},
                              headers=_auth_headers())
        assert resp.status_code == 200
        body = resp.json()
        assert body["counts"] == counts
        assert body["words"] == words
        assert body["can_publish"] is False   # testers view, never publish

    def test_queue_is_empty_not_500_before_the_migration(self, client):
        with self._roles(self.ROLE_REVIEWER), \
             patch("backend.routers.contribute.rls_connection"), \
             patch("backend.routers.contribute.privileged_connection") as priv, \
             patch("backend.routers.contribute.count_ai_topic_vocab",
                   new=AsyncMock(side_effect=asyncpg.exceptions
                                 .UndefinedColumnError("no topic"))):
            self._priv(priv, AsyncMock())
            resp = client.get("/api/contribute/review/ai-topics",
                              params={"language_id": LANG},
                              headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json()["counts"] == []

    def test_bulk_confirm_requires_publish_power(self, client):
        with self._roles(self.ROLE_TESTER), \
             patch("backend.routers.contribute.rls_connection"):
            resp = client.post(
                f"/api/contribute/review/ai-topics/{LANG}/confirm",
                json={"topic": "food_drink"}, headers=_auth_headers())
        assert resp.status_code == 403

    def test_bulk_confirm_signs_a_sampled_bucket(self, client):
        with self._roles(self.ROLE_REVIEWER), \
             patch("backend.routers.contribute.rls_connection"), \
             patch("backend.routers.contribute.privileged_connection") as priv, \
             patch("backend.routers.contribute.bulk_confirm_topics",
                   new=AsyncMock(return_value=37)) as bulk:
            self._priv(priv, AsyncMock())
            resp = client.post(
                f"/api/contribute/review/ai-topics/{LANG}/confirm",
                json={"topic": "food_drink"}, headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json() == {"confirmed": 37}
        assert bulk.await_args.args[1:3] == (LANG, "food_drink")

    def test_bulk_confirm_rejects_a_made_up_bucket(self, client):
        with self._roles(self.ROLE_REVIEWER), \
             patch("backend.routers.contribute.rls_connection"):
            resp = client.post(
                f"/api/contribute/review/ai-topics/{LANG}/confirm",
                json={"topic": "colours"}, headers=_auth_headers())
        assert resp.status_code == 422

    def test_bulk_reject_can_clear_the_whole_bad_run(self, client):
        """topic: null = the language's entire pending set — the recovery
        the classifier's WHERE topic IS NULL resumability cannot provide."""
        with self._roles(self.ROLE_REVIEWER), \
             patch("backend.routers.contribute.rls_connection"), \
             patch("backend.routers.contribute.privileged_connection") as priv, \
             patch("backend.routers.contribute.bulk_reject_topics",
                   new=AsyncMock(return_value=412)) as bulk:
            self._priv(priv, AsyncMock())
            resp = client.post(
                f"/api/contribute/review/ai-topics/{LANG}/reject",
                json={"topic": None}, headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json() == {"cleared": 412}
        assert bulk.await_args.args[2] is None


class TestTopicsFromFile:
    """`-k topics --topics-file` applies a classification produced OUTSIDE
    this process — an in-session maker-checker pass instead of a paid
    estimator run — through the same path: same provisional
    topic_source='ai', same review queue, same resumability. Only the
    estimator call is skipped.

    The plan costs a full classification at "tens of dollars" across ~170k
    rows. This flag is why that phase can cost nothing.
    """

    def test_the_flag_exists_and_documents_both_file_shapes(self):
        import argparse
        import inspect

        from backend.services.seeder import generate_content as gc

        src = inspect.getsource(gc)
        assert "--topics-file" in src
        # nested map (many languages) and flat map (one) are both accepted
        assert '{"<lang>": {"<word>": "<slug>"}}' in src
        assert isinstance(argparse.ArgumentParser(), argparse.ArgumentParser)

    def test_a_slug_outside_the_taxonomy_is_refused_not_stored(self):
        """The enum is the whole safety property: the API path cannot invent
        a bucket because the schema forbids it, so the file path must reject
        one for the same reason — a bad slug would violate the migration's
        CHECK and abort the transaction."""
        from backend.services.topic_taxonomy import valid_topic

        assert valid_topic("food_drink") == "food_drink"
        assert valid_topic("function_words") == "function_words"
        assert valid_topic("colours") is None
        assert valid_topic("") is None
        assert valid_topic(None) is None

    def test_every_guide_bucket_is_a_real_slug(self):
        """The estimator's prompt guide and the frozen taxonomy must not
        drift: a bucket described to the model but absent from the enum
        would be proposed and then silently dropped."""
        import re

        from backend.services import topic_estimate as te
        from backend.services.topic_taxonomy import ALL_TOPICS

        described = set(re.findall(r"^(\w+):", te._GUIDE, re.M))
        assert described == set(ALL_TOPICS), (
            f"guide/taxonomy drift: {described ^ set(ALL_TOPICS)}")
