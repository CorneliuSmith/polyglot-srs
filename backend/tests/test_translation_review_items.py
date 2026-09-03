"""The non-vocabulary translation review queue (brief item 5.2).

Until 3 Sep 2026 only word glosses had a reject queue. A drill line,
explanation, grammar title or example meaning the checker refused was
simply not written and waited for the attempt ledger's backoff — nobody
could see it, and nothing a human did could resolve it. These pin the
lane end to end: the writers queue a reject WITH the maker's proposal, the
queue is empty (not an error) before the owner applies the migration, and
approving writes the row's own layer, reviewed, so the learner reads the
locale instead of the English fallback.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from backend.repositories import contributor
from backend.services import auto_translate as at
from backend.services import translate

PAIR = {"language_id": "L1", "locale": "fr", "locale_name": "French",
        "language_code": "es"}


def _reject(proposed="", note="unsure"):
    return {"verdict": "reject", "translation": "", "proposed": proposed,
            "note": note}


class TestTheLanesKeepTheProposal:
    """The sentence and text lanes used to return only the final to store —
    empty on a reject — so a queue fed by them would have had nothing to
    approve. Same lesson maker_check_batch learned for glosses."""

    async def test_a_reject_carries_the_makers_rendering(self):
        with patch.object(translate, "make_sentence_translations",
                          new=AsyncMock(return_value={0: "Je lis"})), \
             patch.object(translate, "check_glosses",
                          new=AsyncMock(return_value={
                              0: {"verdict": "reject", "final": "", "note": "bad"}})):
            out = await translate.generate_sentence_translations(
                "French", [{"i": 0, "sentence": "I read"}], locale="fr")
        assert out[0]["translation"] == ""
        assert out[0]["proposed"] == "Je lis"
        assert out[0]["note"] == "bad"

    async def test_the_checkers_correction_wins_when_it_offered_one(self):
        with patch.object(translate, "make_text_translations",
                          new=AsyncMock(return_value={0: "Présent"})), \
             patch.object(translate, "check_glosses",
                          new=AsyncMock(return_value={
                              0: {"verdict": "reject", "final": "Le présent",
                                  "note": "needs the article"}})):
            out = await translate.generate_text_translations(
                "French", [{"i": 0, "sentence": "Present tense"}], kind="label",
                locale="fr")
        assert out[0]["proposed"] == "Le présent"


class TestTheWriter:
    async def test_a_pass_is_not_queued(self):
        conn = AsyncMock()
        with patch.object(at, "table_present", new=AsyncMock(return_value=True)):
            await at._queue_review_item(
                conn, PAIR, "drill", "hint", "d1", "a verb",
                {"verdict": "ok", "translation": "un verbe", "note": ""})
        conn.execute.assert_not_awaited()

    async def test_without_the_migration_nothing_is_written(self):
        # Owner-applied migrations: an unmigrated deploy must behave exactly
        # as before — the row stays unwritten and the ledger paces a retry.
        conn = AsyncMock()
        with patch.object(at, "table_present",
                          new=AsyncMock(return_value=False)) as probe:
            await at._queue_review_item(
                conn, PAIR, "drill", "hint", "d1", "a verb", _reject("un verbe"))
        probe.assert_awaited_once_with(conn, "translation_review_items")
        conn.execute.assert_not_awaited()

    async def test_a_reject_lands_with_the_proposal_and_the_reason(self):
        conn = AsyncMock()
        with patch.object(at, "table_present", new=AsyncMock(return_value=True)):
            await at._queue_review_item(
                conn, PAIR, "drill", "hint", "d1", "a verb",
                _reject("un verbe", "gate: answer leak"))
        conn.execute.assert_awaited_once()
        sql, *args = conn.execute.await_args.args
        assert "INSERT INTO translation_review_items" in sql
        assert "ON CONFLICT (kind, target_id, locale, field) DO NOTHING" in sql
        assert args == ["drill", "hint", "d1", "L1", "fr", "a verb",
                        "un verbe", "gate: answer leak"]

    async def test_an_empty_proposal_is_stored_as_null(self):
        conn = AsyncMock()
        with patch.object(at, "table_present", new=AsyncMock(return_value=True)):
            await at._queue_review_item(
                conn, PAIR, "explanation", "explanation", "g1", "text",
                _reject("", ""))
        args = conn.execute.await_args.args
        assert args[7] is None and args[8] is None


class TestTheHooks:
    """Each layer's translator queues what it did not write, per field."""

    async def test_a_rejected_drill_field_is_queued_and_the_other_still_lands(self):
        conn = AsyncMock()
        rows = [{"id": "d1", "translation": "I read a book", "hint": "a verb",
                 "answer": "leo"}]

        async def lanes(_lang, items, **_kw):
            out = []
            for it in items:
                if it["sentence"] == "I read a book":
                    out.append({"i": it["i"], "sentence": it["sentence"],
                                **_reject("Je lis un livre", "unsure")})
                else:
                    out.append({"i": it["i"], "sentence": it["sentence"],
                                "translation": "un verbe", "proposed": "un verbe",
                                "verdict": "ok", "note": ""})
            return out

        with patch.object(at, "generate_sentence_translations", new=lanes), \
             patch.object(at, "table_present", new=AsyncMock(return_value=True)):
            applied = await at._translate_drills(conn, PAIR, rows)
        assert applied == 1
        sqls = [c.args[0] for c in conn.execute.await_args_list]
        assert any("INSERT INTO translation_review_items" in s for s in sqls)
        assert any("INSERT INTO drill_hint_translations" in s for s in sqls)
        queued = next(c.args for c in conn.execute.await_args_list
                      if "translation_review_items" in c.args[0])
        assert queued[1:4] == ("drill", "translation", "d1")
        assert queued[7] == "Je lis un livre"

    async def test_a_rejected_grammar_title_is_queued_per_field(self):
        conn = AsyncMock()
        rows = [{"id": "g1", "title": "Present tense", "culture_note": None,
                 "function_note": None}]
        lane = AsyncMock(return_value=[
            {"i": 0, "sentence": "Present tense", **_reject("Présent", "nope")}])
        with patch.object(at, "generate_text_translations", new=lane), \
             patch.object(at, "table_present", new=AsyncMock(return_value=True)):
            applied = await at._translate_grammar_meta(conn, PAIR, rows)
        assert applied == 0  # nothing came back → no grammar_point_translations row
        conn.execute.assert_awaited_once()
        args = conn.execute.await_args.args
        assert "translation_review_items" in args[0]
        assert args[1:4] == ("grammar_meta", "title", "g1")
        assert args[6] == "Present tense" and args[7] == "Présent"

    async def test_a_rejected_explanation_is_queued(self):
        conn = AsyncMock()
        rows = [{"id": "g1", "explanation": "Use ser for identity."}]
        lane = AsyncMock(return_value=[
            {"i": 0, "sentence": rows[0]["explanation"],
             **_reject("Utilisez ser…", "mistranslates estar")}])
        with patch.object(at, "generate_text_translations", new=lane), \
             patch.object(at, "table_present", new=AsyncMock(return_value=True)):
            applied = await at._translate_explanations(conn, PAIR, rows)
        assert applied == 0
        args = conn.execute.await_args.args
        assert args[1:4] == ("explanation", "explanation", "g1")

    async def test_a_rejected_example_meaning_is_queued(self):
        conn = AsyncMock()
        rows = [{"id": "e1", "vocabulary_id": "v1", "language_id": "L1",
                 "sentence": "Leo un libro.", "translation": "I read a book."}]
        lane = AsyncMock(return_value=[
            {"i": 0, "sentence": "I read a book.",
             **_reject("Je lis un livre.", "unsure")}])
        with patch.object(at, "generate_sentence_translations", new=lane), \
             patch.object(at, "table_present", new=AsyncMock(return_value=True)), \
             patch.object(contributor, "add_example_sentence", new=AsyncMock()) as add:
            applied = await at._translate_examples(conn, PAIR, rows)
        assert applied == 0
        add.assert_not_awaited()
        args = conn.execute.await_args.args
        assert args[1:4] == ("example", "translation", "e1")
        assert args[6] == "I read a book."


class _Row(dict):
    """asyncpg.Record look-alike: subscriptable, truthy."""


class TestResolve:
    def _present(self, found=True):
        return patch.object(
            contributor, "_present",
            new=AsyncMock(return_value={"translation_review_items"} if found else set()))

    async def test_list_is_empty_not_an_error_before_the_migration(self):
        conn = AsyncMock()
        with self._present(False):
            assert await contributor.list_translation_review_items(conn) == []
        conn.fetch.assert_not_awaited()

    async def test_list_types_each_row_for_the_card_loader(self):
        conn = AsyncMock()
        conn.fetch.return_value = [_Row(
            id="i1", kind="grammar_meta", field="title", target_id="g1",
            locale="fr", source_text="Present tense", proposed="Présent",
            reason="nope", status="pending", created_at=None, label="Present tense")]
        with self._present():
            rows = await contributor.list_translation_review_items(conn, language_id="L1")
        assert rows[0]["target_type"] == "grammar_point"
        assert rows[0]["target_id"] == "g1"
        assert rows[0]["label"] == "Present tense"
        assert conn.fetch.await_args.args[1:] == ("pending", "L1")

    @pytest.mark.parametrize("kind,field,table,column", [
        ("drill", "hint", "drill_hint_translations", "hint"),
        ("drill", "translation", "drill_hint_translations", "translation"),
        ("explanation", "explanation", "explanation_translations", "explanation"),
        ("grammar_meta", "culture_note", "grammar_point_translations", "culture_note"),
    ])
    async def test_approve_writes_the_rows_own_layer_reviewed(
            self, kind, field, table, column):
        conn = AsyncMock()
        conn.fetchrow.return_value = _Row(
            id="i1", kind=kind, field=field, target_id="t1", locale="fr",
            proposed=" Le texte ", status="pending")
        with self._present():
            assert await contributor.resolve_translation_review_item(
                conn, "i1", approve=True) == "ok"
        write, status = [c.args for c in conn.execute.await_args_list]
        assert f"INSERT INTO {table}" in write[0]
        assert f"{column} = EXCLUDED.{column}" in write[0]
        assert "reviewed = true" in write[0]
        assert write[1:] == ("t1", "fr", "Le texte")
        assert status[1:] == ("i1", "approved")

    async def test_a_field_the_layer_does_not_have_is_refused(self):
        # `field` is interpolated into SQL: it comes from the table, but the
        # allow-list is what makes that safe, so a stray value must not reach
        # the query.
        conn = AsyncMock()
        conn.fetchrow.return_value = _Row(
            id="i1", kind="drill", field="sentence", target_id="t1",
            locale="fr", proposed="x", status="pending")
        with self._present():
            assert await contributor.resolve_translation_review_item(
                conn, "i1", approve=True) == "empty"
        conn.execute.assert_not_awaited()

    async def test_approve_of_an_example_adds_a_locale_row(self):
        conn = AsyncMock()
        conn.fetchrow.side_effect = [
            _Row(id="i1", kind="example", field="translation", target_id="e1",
                 locale="fr", proposed="Je lis un livre.", status="pending"),
            _Row(vocabulary_id="v1", language_id="L1", sentence="Leo un libro."),
        ]
        with self._present(), \
             patch.object(contributor, "add_example_sentence",
                          new=AsyncMock(return_value="e2")) as add:
            assert await contributor.resolve_translation_review_item(
                conn, "i1", approve=True) == "ok"
        assert add.await_args.args[1:] == ("v1", "L1", "Leo un libro.", "Je lis un livre.")
        assert add.await_args.kwargs["translation_locale"] == "fr"
        assert add.await_args.kwargs["reviewed"] is True

    async def test_approve_of_a_deleted_example_says_gone(self):
        conn = AsyncMock()
        conn.fetchrow.side_effect = [
            _Row(id="i1", kind="example", field="translation", target_id="e1",
                 locale="fr", proposed="x", status="pending"),
            None,
        ]
        with self._present():
            assert await contributor.resolve_translation_review_item(
                conn, "i1", approve=True) == "gone"
        conn.execute.assert_not_awaited()  # still pending: dismiss is the way out

    async def test_reject_only_clears_the_row(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = _Row(
            id="i1", kind="drill", field="hint", target_id="t1", locale="fr",
            proposed="x", status="pending")
        with self._present():
            assert await contributor.resolve_translation_review_item(
                conn, "i1", approve=False) == "ok"
        conn.execute.assert_awaited_once()
        assert conn.execute.await_args.args[1:] == ("i1", "rejected")

    async def test_an_empty_proposal_cannot_be_approved(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = _Row(
            id="i1", kind="drill", field="hint", target_id="t1", locale="fr",
            proposed=None, status="pending")
        with self._present():
            assert await contributor.resolve_translation_review_item(
                conn, "i1", approve=True) == "empty"

    async def test_resolved_rows_are_not_resolved_twice(self):
        conn = AsyncMock()
        conn.fetchrow.return_value = _Row(
            id="i1", kind="drill", field="hint", target_id="t1", locale="fr",
            proposed="x", status="approved")
        with self._present():
            assert await contributor.resolve_translation_review_item(
                conn, "i1", approve=True) == "not_pending"


class TestTheInboxFold:
    """One panel, one tile, one number: the items are counted on their own
    (their table can be missing on its own) and folded into the gloss
    queue's key on the way out."""

    def test_the_folded_key_never_reaches_the_client(self):
        assert "ai_translation_items" not in contributor.INBOX_QUEUE_KEYS
        assert "ai_translations" in contributor.INBOX_QUEUE_KEYS

    def test_items_add_into_ai_translations(self):
        raw = {k: 0 for k in contributor.INBOX_QUEUE_KEYS}
        raw.update(ai_translations=2, ai_translation_items=3)
        counts = contributor.fold_counts(raw)
        assert counts["ai_translations"] == 5
        assert "ai_translation_items" not in counts

    def test_a_roll_up_without_the_column_still_folds(self):
        # A grouped roll-up renders a missing queue as 0 under its own key,
        # so the key is present; but fold tolerates its absence too.
        raw = {k: 1 for k in contributor.INBOX_QUEUE_KEYS}
        assert contributor.fold_counts(raw)["ai_translations"] == 1
