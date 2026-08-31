"""Safety invariants of the example-sentence prune.

This deletes learner-facing content from production, so each rule below is
asserted rather than trusted. The bug it exists to fix: `seed_sentences` can
only ADD (ON CONFLICT DO NOTHING), so thinning a committed bank leaves the
cut rows live forever — English served "I am.", "I am you." and "I am!" for
the word "I" while the curated file held "I think he did it."
"""

from backend.services.seeder import prune_sentences as ps
from backend.tests.integration.conftest import requires_db

pytestmark = requires_db


def _row(**kw):
    base = dict(id="00000000-0000-0000-0000-000000000000",
                vocabulary_id="v", word="i", sentence="I am.",
                translation=None, translation_locale="es", difficulty_rank=1,
                source="tatoeba", license=None, gloss=None,
                transliteration=None, reviewed=True, language_id="l")
    base.update(kw)
    return base


class TestSurveyRules:
    """survey() decides what dies; these pin the three rules that protect data."""

    def _survey(self, rows, keep, monkeypatch):
        monkeypatch.setattr(ps, "file_pairs", lambda code: keep)

        class _Conn:
            async def fetch(self, *a, **k):
                return rows
        import asyncio
        return asyncio.run(ps.survey(_Conn(), "en"))

    def test_a_sentence_the_file_keeps_survives_in_every_locale(self, monkeypatch):
        """The file stores one row per sentence; the DB stores it once per
        locale. Matching on locale would delete the German translation of a
        sentence the bank endorses, which is the whole point of keeping it."""
        rows = [_row(sentence="I think he did it.", translation_locale=loc)
                for loc in ("es", "de", "fr", "ru")]
        rep = self._survey(rows, {("i", "I think he did it.")}, monkeypatch)
        assert rep["delete"] == []

    def test_curated_and_ai_rows_are_never_candidates(self, monkeypatch):
        """Those are human-authored or human-reviewed; no rebuild brings
        them back, so the file's silence is not evidence against them."""
        rows = [_row(sentence="hand written", source=s)
                for s in ("curated", "ai")]
        rep = self._survey(rows, {("other", "unrelated.")}, monkeypatch)
        assert rep["delete"] == []
        assert rep["protected"] == 2

    def test_a_word_is_never_stranded_with_nothing(self, monkeypatch):
        """Deleting every sentence a word has is worse than keeping bad ones:
        the card renders with no example at all."""
        rows = [_row(sentence="I am."), _row(sentence="I am you.")]
        rep = self._survey(rows, {("other", "unrelated.")}, monkeypatch)  # endorses neither
        assert rep["delete"] == []
        assert rep["kept_empty"] == ["i"]

    def test_unendorsed_rows_go_when_the_word_still_has_one(self, monkeypatch):
        rows = [_row(sentence="I am."), _row(sentence="I am you."),
                _row(sentence="I think he did it.")]
        rep = self._survey(rows, {("i", "I think he did it.")}, monkeypatch)
        assert sorted(r["sentence"] for r in rep["delete"]) == \
            ["I am you.", "I am."]
        assert len(rep["delete"]) == 2
        assert rep["kept_empty"] == []


def test_the_rollback_restores_original_ids():
    """Re-inserting with fresh ids would orphan nothing today, but the
    rollback must reproduce the table as it was, not merely its contents."""
    rep = {"delete": [_row(id="11111111-1111-1111-1111-111111111111",
                           sentence="I'm o'clock \"quoted\"")]}
    import tempfile
    from pathlib import Path
    ps.ROLLBACK_DIR = Path(tempfile.mkdtemp())
    sql = ps.write_rollback([rep], "TESTSTAMP").read_text(encoding="utf-8")
    assert "11111111-1111-1111-1111-111111111111" in sql
    # single quotes doubled, not escaped away
    assert "I''m o''clock" in sql
    assert sql.startswith("-- Rollback") and sql.rstrip().endswith("COMMIT;")


def test_an_empty_committed_bank_deletes_nothing(monkeypatch):
    """The most dangerous possible input: a missing or empty TSV means the
    file endorses NOTHING, and a naive prune would delete the language's
    entire corpus. survey() must refuse rather than obey."""
    monkeypatch.setattr(ps, "file_pairs", lambda code: set())

    class _Conn:
        async def fetch(self, *a, **k):
            raise AssertionError("must not even query with no committed bank")
    import asyncio
    rep = asyncio.run(ps.survey(_Conn(), "en"))
    assert rep["skipped"] == "no committed bank"
    assert rep["delete"] == []


class TestContextFreeRowsLoseTheirExemption:
    """`curated`/`ai` rows are exempt because no rebuild reproduces them.
    A row that is only the headword has nothing to reproduce, and the
    exemption was shielding junk: the Russian `да` card kept "Да." and "Да!"
    as source='ai' through a full prune, beside the real sentences that had
    just been authored for it. 221 such rows in ru+ar alone."""

    def test_a_bare_headword_is_prunable_even_when_ai(self):
        assert ps._context_free("Да.", "да")
        assert ps._context_free("Да!", "да")
        assert ps._context_free("¿No?", "no")

    def test_a_real_sentence_keeps_its_exemption(self):
        assert not ps._context_free("Да, я согласился помочь с переездом.", "да")
        assert not ps._context_free("Это он, да?", "да")

    def test_it_does_not_count_whitespace(self):
        """Thai has no spaces; comparing to the headword still works."""
        assert ps._context_free("ใช่", "ใช่")
        assert not ps._context_free("ผมกินข้าว", "กิน")
