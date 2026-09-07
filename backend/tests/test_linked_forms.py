"""One word, several spellings — one card (owner decision, 7 Sep 2026).

Turkish carried mi, mı, mu and mü as four headwords with one shared
definition ("Used to form interrogatives"), so no card could tell the
learner which spelling to type; a first repair gave each spelling a
definition naming its vowel class, which is the harmony OUTCOME tr.md's
hint standard 2 forbids. Now: one headword, the rest in the frequency
file's `alt` column → `vocabulary.alternatives`; the sentence fixes the
shape; typing another shape is the right word graded sloppy, with the rule.
Every consumer that asks "is the word in this sentence" must ask about every
shape, or "Var mı?" reads as a sentence the `mi` card cannot blank.
"""
from __future__ import annotations

import csv
import io

import pytest

from backend.services import linked_forms
from backend.services.extract import ANSWER_MARKER, find_cloze
from backend.services.nlp.base import AnswerResult
from backend.services.nlp.turkish import TurkishNLP, answer_span
from backend.services.span_finders import span_finder


class TestFindCloze:
    def test_blanks_the_shape_the_sentence_carries(self):
        assert find_cloze("Var mı?", ["mi", "mı", "mu", "mü"], answer_span) == (
            f"Var {ANSWER_MARKER}?", "mı")

    def test_headword_first_when_both_appear(self):
        cloze, form = find_cloze("Bu da bir şey değil mi?", ["mi", "mı"], answer_span)
        assert form == "mi" and cloze.endswith(f"{ANSWER_MARKER}?")

    def test_none_when_no_shape_is_a_word(self):
        assert find_cloze("Taler nedir?", ["ta", "te"], answer_span) is None

    def test_the_regex_alone_folds_dotless_i_onto_i(self):
        """Why Turkish has a span finder: Python's IGNORECASE treats ı as a
        case of i, so the plain regex blanks `mı` for the `mi` card — the
        four-headword defect in miniature — and would blank `sik` for `sık`."""
        assert find_cloze("Var mı?", ["mi", "mı"]) == (f"Var {ANSWER_MARKER}?", "mi")
        assert find_cloze("Var mı?", ["mi", "mı"], answer_span)[1] == "mı"
        assert answer_span("Onu sik.", "sık") is None
        assert answer_span("Işık var.", "ışık") == (0, 4)
        assert answer_span("İyi misin?", "iyi") == (0, 3)

    def test_the_registry_knows_turkish_and_thai_only(self):
        assert span_finder("tr") is answer_span
        assert span_finder("th") is not None
        assert span_finder("ru") is None and span_finder(None) is None

    def test_a_single_form_is_make_cloze(self):
        assert find_cloze("Ben de.", ["de"]) == (f"Ben {ANSWER_MARKER}.", "de")


class TestLinkedFormsFile:
    def test_turkish_harmony_sets_are_linked(self):
        forms = linked_forms.linked_forms("tr")
        assert forms["mi"] == ("mı", "mu", "mü")
        assert forms["de"] == ("da",)
        assert forms["ta"] == ("te",)

    def test_the_variants_are_not_headwords_any_more(self):
        with open(linked_forms.DATA_DIR / "tr_frequency.tsv",
                  encoding="utf-8-sig", newline="") as handle:
            words = {r["word"] for r in csv.DictReader(handle, delimiter="\t")}
        assert not {"mı", "mu", "mü", "da", "te"} & words

    def test_forms_of_is_headword_first(self):
        assert linked_forms.forms_of("mi", "tr") == ["mi", "mı", "mu", "mü"]
        assert linked_forms.forms_of("ev", "tr") == ["ev"]

    def test_a_course_without_the_column_has_no_links(self):
        assert linked_forms.linked_forms("ru") == {}


class TestTurkishSeederAlt:
    @pytest.fixture
    def records(self, tmp_path, monkeypatch):
        import backend.services.seeder.seed_turkish as mod
        tsv = "rank\tword\tpos\ten\talt\n6\tmi\tparticle\tquestion\tmı;mu;mü\n7\tde\tconj\ttoo\tda\n8\tev\tnoun\thouse\t\n"
        (tmp_path / mod.FREQ_FILENAME).write_text(tsv, encoding="utf-8")
        monkeypatch.setattr(mod, "DATA_DIR", tmp_path)
        import asyncio
        return asyncio.run(mod.TurkishSeeder("fake://db").transform())

    def test_alt_becomes_alternatives(self, records):
        by_word = {r["word"]: r for r in records}
        assert by_word["mi"]["alternatives"] == ["mı", "mu", "mü"]
        assert by_word["de"]["alternatives"] == ["da"]
        assert "alternatives" not in by_word["ev"]


class TestCardBlanksTheShape:
    def _row(self, sentences, alternatives=("mı", "mu", "mü")):
        return {
            "id": "c1", "user_id": "u1", "language_id": "l1",
            "card_type": "vocabulary", "card_id": "v1",
            "word": "mi", "part_of_speech": "particle",
            "definition": "the yes/no question particle",
            "example_sentences": list(sentences),
            "example_translations": [None] * len(sentences),
            "example_glosses": [None] * len(sentences),
            "example_transliterations": [None] * len(sentences),
            "example_translation_locales": ["en"] * len(sentences),
            "last_prompt": None, "morphology": {"lemma": "mi"},
            "alternatives": list(alternatives), "language_code": "tr",
            "ease_factor": 2.5, "interval": 0, "repetitions": 0, "streak": 0,
            "lapses": 0, "next_review": None,
        }

    def _card(self, sentences, **over):
        from backend.repositories.cards import _vocab_card
        return _vocab_card(self._row(sentences, **over), {})

    def test_the_answer_is_the_shape_in_the_sentence(self):
        card = self._card(["Var mı?"])
        assert card["sentence"] == f"Var {ANSWER_MARKER}?"
        assert card["correct_answer"] == "mı"
        assert card["alternatives"] == ["mi", "mu", "mü"]

    def test_a_variant_sentence_is_not_a_fallback_to_the_definition(self):
        """Rule 46: before this, 8 of the 10 `mi` sentences were ones the card
        could not blank, and the card served the definition alone."""
        card = self._card(["Bu kötü mü?"])
        assert ANSWER_MARKER in card["sentence"]

    def test_no_sentence_expects_the_headword(self):
        card = self._card(["Taler nedir?"])
        assert card["correct_answer"] == "mi"
        assert card["alternatives"] == ["mı", "mu", "mü"]

    def test_a_card_without_links_is_unchanged(self):
        card = self._card(["Var mı?"], alternatives=())
        assert card["correct_answer"] == "mi"
        assert ANSWER_MARKER not in card["sentence"]
        assert card["alternatives"] == []


class TestTurkishGradesTheShape:
    @pytest.fixture
    def nlp(self):
        return TurkishNLP()

    def test_the_shape_the_sentence_takes_is_correct(self, nlp):
        result, _ = nlp.check_answer("mı", "mı", {
            "alternatives": ["mi", "mu", "mü"], "sentence": f"Var {ANSWER_MARKER}?"})
        assert result == AnswerResult.CORRECT

    def test_another_shape_is_the_right_word_graded_sloppy_with_the_rule(self, nlp):
        result, msg = nlp.check_answer("mu", "mı", {
            "alternatives": ["mi", "mu", "mü"], "sentence": f"Var {ANSWER_MARKER}?"})
        assert result == AnswerResult.CORRECT_SLOPPY
        assert msg and "mı" in msg and "harmonis" in msg

    def test_with_no_sentence_any_shape_is_the_word(self, nlp):
        result, _ = nlp.check_answer("mü", "mi", {
            "alternatives": ["mı", "mu", "mü"],
            "sentence": "the yes/no question particle"})
        assert result == AnswerResult.CORRECT

    def test_a_different_word_is_still_wrong(self, nlp):
        result, _ = nlp.check_answer("da", "mı", {
            "alternatives": ["mi", "mu", "mü"], "sentence": f"Var {ANSWER_MARKER}?"})
        assert result == AnswerResult.WRONG

    def test_other_courses_keep_alternatives_as_correct(self):
        """The base meaning of an alternative — a regional spelling, an
        accepted partner — is another right answer, sentence or not."""
        from backend.services.nlp.base import BaseNLP

        class _Plain(BaseNLP):
            def normalize(self, text):
                return text.strip().lower()

            def lemmatize(self, word):
                return word.lower()

            def get_morphological_family(self, word):
                return {word}

            def get_aspect_partner(self, verb, card_context=None):
                return None

        result, _ = _Plain().check_answer("colour", "color", {
            "alternatives": ["colour"], "sentence": f"The {ANSWER_MARKER} red."})
        assert result == AnswerResult.CORRECT


class TestConsumersAgree:
    def test_the_audit_counts_variant_sentences_as_clozable(self, tmp_path, monkeypatch):
        from backend.services.quality import audit_content as ac
        (tmp_path / "tr_frequency.tsv").write_text(
            "rank\tword\tpos\ten\talt\n6\tmi\tparticle\tq\tmı;mu;mü\n", encoding="utf-8")
        (tmp_path / "tr_sentences.tsv").write_text(
            "word\tsentence\ttranslation\tdifficulty_rank\nmi\tVar mı?\tIs there?\t1\n",
            encoding="utf-8")
        monkeypatch.setattr(ac, "DATA", tmp_path)
        monkeypatch.setattr(linked_forms, "DATA_DIR", tmp_path)
        linked_forms.linked_forms.cache_clear()
        try:
            unclozable, _ = ac._audit_sentence_cards("tr")
        finally:
            linked_forms.linked_forms.cache_clear()
        assert unclozable == []

    def test_the_authored_sentence_gate_accepts_a_variant(self):
        import scripts.apply_authored_sentences as gate
        assert gate.clozable("mi", "Bu kötü mü?", "tr")
        assert not gate.clozable("mi", "Taler nedir?", "tr")

    def test_the_prune_keeps_one_row_per_shape(self, monkeypatch):
        """Every `mi` sentence but one is below the five-token floor — the
        particle's sentences are short by nature — so the floor alone would
        leave the card able to show `mi` and never mı, mu or mü. Each shape
        keeps its longest row; the rest of the thin ones still go."""
        from backend.services.seeder import prune_sentences as ps
        sentences = ["Var mı?", "Bu kadar mı?", "O çok mu?", "Bu kötü mü?",
                     "Gerçekten kötü mü?", "Bu da bir şey değil mi?"]
        # the file endorses only the long one (an empty file prunes nothing)
        monkeypatch.setattr(ps, "file_pairs",
                            lambda code: {("mi", "Bu da bir şey değil mi?")})
        rows = [dict(id=f"0000000{i}-0000-0000-0000-000000000000",
                     vocabulary_id="v", word="mi", sentence=sent, translation=None,
                     translation_locale="en", difficulty_rank=1, source="tatoeba",
                     license=None, gloss=None, transliteration=None, reviewed=True,
                     language_id="l")
                for i, sent in enumerate(sentences)]

        class _Conn:
            async def fetch(self, *a, **k):
                return rows
        import asyncio
        rep = asyncio.run(ps.survey(_Conn(), "tr"))
        deleted = {r["sentence"] for r in rep["delete"]}
        # mı keeps its longer row; the two mü rows tie on length and the
        # first in bank order stays
        assert deleted == {"Var mı?", "Gerçekten kötü mü?"}
        kept = set(sentences) - deleted
        assert {find_cloze(k, linked_forms.forms_of("mi", "tr"), answer_span)[1]
                for k in kept} == {"mi", "mı", "mu", "mü"}


def _tsv(text: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(text), delimiter="\t"))
