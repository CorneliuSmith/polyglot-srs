"""Telling an English usage note apart from a translation (CHECKS §27)."""

from backend.services.drill_notes import split_note


class TestTheEnglishConvention:
    """`docs/quality/en.md` note 0: on the English course the drill's
    `translation` field holds a usage note, because an English rendering of an
    English sentence would hand over the answer. The real translations live
    per locale in `en_drill_hints.<locale>.json`."""

    def test_an_english_learner_of_english_gets_the_note_as_context(self):
        """No `drill_hint_translations` row exists for `en`, so the COALESCE
        that serves the card falls through to the note. It must not then be
        labelled Translation — the owner's card read "do — the participle."."""
        translation, context = split_note(
            "en", "do — the participle.", "do — the participle.")
        assert translation is None
        assert context == "do — the participle."

    def test_a_spanish_learner_of_english_keeps_the_translation(self):
        translation, context = split_note(
            "en", "Ayer fui al mercado.", "The past of 'eat'.")
        assert translation == "Ayer fui al mercado."
        assert context == "The past of 'eat'."

    def test_every_other_course_is_untouched(self):
        """There is no note off the English course, so this must be a no-op —
        a Spanish drill's translation is a translation."""
        assert split_note("es", "The cat sleeps.", "The cat sleeps.") == (
            "The cat sleeps.", None)
        assert split_note("ru", "I am tired.", None) == ("I am tired.", None)

    def test_an_empty_note_is_not_a_layer(self):
        assert split_note("en", None, None) == (None, None)
        assert split_note("en", None, "   ") == (None, None)
