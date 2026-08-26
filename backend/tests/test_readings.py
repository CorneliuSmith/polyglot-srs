"""Computed script→Latin readings for example sentences (grammar path)."""

from backend.services.readings import sentence_reading


class TestSentenceReading:
    def test_hindi_romanizes(self):
        r = sentence_reading("मैं घर जा रहा हूँ।", "hi")
        assert r and "ghar" in r

    def test_russian_romanizes(self):
        r = sentence_reading("Мой дом — твой дом.", "ru")
        assert r and r.lower().startswith("moj")

    def test_latin_language_gets_no_reading(self):
        assert sentence_reading("Yo voy a casa.", "es") is None

    def test_arabic_deliberately_unsupported(self):
        # unvocalized Arabic would need short vowels a romanization lacks
        assert sentence_reading("أنا ذاهب إلى البيت.", "ar") is None

    def test_empty_and_none_safe(self):
        assert sentence_reading("", "ru") is None
        assert sentence_reading(None, "hi") is None
        assert sentence_reading("   ", "hi") is None


class TestTheReviewCardCarriesAReading:
    """The reading existed for `hi` and `ru` and the review card never showed it.

    `sentence_reading` had exactly one caller — the grammar page — so a learner
    met the same Russian sentence twice: with a reading under the grammar point,
    and as bare Cyrillic on the review card, where they actually have to recall
    it. The card path read only `example_sentences.transliteration`, which is
    empty for every row of ru (28,935), hi (8,130), el, ko and th.
    """

    @staticmethod
    def _row(**over):
        row = {
            "id": "c1", "user_id": "u1", "language_id": "l1",
            "card_type": "vocabulary", "card_id": "v1", "language_code": "ru",
            "ease_factor": 2.5, "interval": 1, "repetitions": 0, "streak": 0,
            "lapses": 0, "next_review": None, "last_prompt": None,
            "word": "живу", "definition": "I live",
            "example_sentences": ["Я живу в Москве."],
            "example_translations": ["I live in Moscow."],
            "example_glosses": [None], "example_transliterations": [None],
            "example_translation_locales": ["en"],
            "morphology": None, "alternatives": None, "part_of_speech": "verb",
        }
        row.update(over)
        return row

    def _card(self, **over):
        from backend.repositories.cards import _vocab_card
        return _vocab_card(self._row(**over), {})

    def test_a_russian_card_with_no_stored_romanisation_computes_one(self):
        card = self._card()
        assert card["transliteration"], "learner sees Cyrillic with no reading"
        assert "Moskve" in card["transliteration"]

    def test_the_computed_reading_does_not_spell_the_hidden_word(self):
        """The whole reason it is computed from the CLOZE. Romanising the raw
        sentence prints `zhivu` in Latin letters directly above a blank whose
        answer is живу — the 926-row answer leak of CHECKS.md §11, regenerated
        on every card instead of sitting in a file where a guard can see it."""
        card = self._card()
        # Two blank conventions live in this corpus — `{{answer}}` from
        # make_cloze and `___` in the authored drill banks. Both must survive
        # the romaniser untouched; accept either rather than pinning one.
        assert ("{{answer}}" in card["transliteration"]
                or "___" in card["transliteration"])
        assert "zhivu" not in card["transliteration"].lower()

    def test_a_stored_romanisation_still_wins(self):
        """Authored beats computed — he and fa have hand-written rows and the
        Korean time expressions were hand-fixed. A fallback that overrode them
        would silently discard the only reviewed romanisation in the corpus."""
        card = self._card(example_transliterations=["AUTHORED ___"])
        assert card["transliteration"] == "AUTHORED ___"

    def test_a_latin_script_card_gets_no_reading(self):
        card = self._card(language_code="es", word="vivo",
                          example_sentences=["Yo vivo en Madrid."])
        assert card["transliteration"] is None

    def test_a_card_with_no_example_sentence_is_unharmed(self):
        card = self._card(example_sentences=[], example_translations=[])
        assert card["transliteration"] is None
        assert card["sentence"] == "I live"
