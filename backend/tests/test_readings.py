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


class TestGreekReading:
    """Greek was the odd script out — Cyrillic got a computed reading and it
    did not, though ELOT 743 is more regular than the Cyrillic mapping."""

    def test_greek_romanizes(self):
        assert sentence_reading("Η Ελλάδα είναι όμορφη.", "el") == \
            "I Ellada einai omorfi."

    def test_the_voicing_rule_is_not_backwards(self):
        """<αυ ευ> take `f` before a voiceless sound and `v` otherwise. Getting
        this backwards prints *auto* for «αυτό» — and a reading is trusted by
        exactly the learner who cannot yet check it."""
        assert sentence_reading("αυτό", "el") == "afto"
        assert sentence_reading("αυγό", "el") == "avgo"
        assert sentence_reading("ευχαριστώ", "el") == "efcharisto"
        assert sentence_reading("Ευρώπη", "el") == "Evropi"

    def test_a_diaeresis_splits_what_would_otherwise_be_a_digraph(self):
        """The mark exists to say "not a digraph". «Μαΐου» is *Maiou*; folding
        it back into a precomposed <ϊ> printed the Greek letter verbatim."""
        assert sentence_reading("Μαΐου", "el") == "Maiou"

    def test_one_greek_letter_becoming_two_latin_ones_is_not_shouting(self):
        assert sentence_reading("Θεσσαλονίκη", "el") == "Thessaloniki"
        assert sentence_reading("Χαίρετε", "el") == "Chairete"

    def test_real_capitals_stay_capitals(self):
        assert sentence_reading("ΕΛΛΑΔΑ", "el") == "ELLADA"

    def test_mp_is_b_at_the_start_and_mp_inside(self):
        assert sentence_reading("μπύρα", "el") == "byra"
        assert sentence_reading("λάμπα", "el") == "lampa"

    def test_gamma_kappa_is_ng_inside_a_word_and_gk_at_the_start(self):
        """The one defect an adversarial pass over 60 corpus sentences found,
        and it was systematic: <γκ> had no entry in the digraph table at all,
        so it fell through to γ→g plus κ→k. That is right word-initially by
        accident and wrong everywhere else. Both examples below are real rows
        from data/el_sentences.tsv."""
        assert sentence_reading("έγκυος", "el") == "engyos"
        assert sentence_reading("πιγκουίνος", "el") == "pingouinos"
        assert sentence_reading("Άγκυρα", "el") == "Angyra"
        assert sentence_reading("γκρίζος", "el") == "gkrizos"

    def test_the_other_gamma_clusters_did_not_regress(self):
        assert sentence_reading("Αγγλία", "el") == "Anglia"
        assert sentence_reading("άγχος", "el") == "anchos"
        assert sentence_reading("ελέγχω", "el") == "elencho"

    def test_the_cloze_blank_survives(self):
        r = sentence_reading("Το {{answer}} είναι καλό.", "el")
        assert "{{answer}}" in r


class TestTheVocabularyReadingIsComputedOnTheGenericPath:
    """Greek reached the database through `csv_importer`, which only ever
    copied a `reading` column its TSV does not have. Hindi and Russian have
    dedicated seeders that compute one, so the same script problem was solved
    for the languages with bespoke code and left open for the language without.
    """

    def test_greek_words_get_a_reading(self):
        from backend.services.seeder.csv_importer import _computed_reading
        assert _computed_reading("άνθρωπος", "el") == "anthropos"

    def test_a_latin_script_word_stores_nothing(self):
        """A reading identical to the headword is noise the card would display."""
        from backend.services.seeder.csv_importer import _computed_reading
        assert _computed_reading("casa", "es") is None

    def test_arabic_stays_deliberately_unread(self):
        from backend.services.seeder.csv_importer import _computed_reading
        assert _computed_reading("كتاب", "ar") is None
