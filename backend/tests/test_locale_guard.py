"""A card must never present one language as another.

A learner studying Turkish with Arabic support was shown
"This city is very big and millions of people live there." under the
label الترجمة. Nothing was broken enough to fail: the English text was
served by the query's own fallback because no Arabic rendering existed,
and every layer downstream trusted the label.

These pin the guard that catches it — including the two ways it could
cry wolf, which matter as much as the catch, because a check that
flags healthy cards gets switched off within a week.
"""
from __future__ import annotations

import pytest

from backend.services.locale_guard import (
    LOCALIZED_FIELDS,
    mark_locale_mismatches,
    mismatched_fields,
    script_of,
    script_ratio,
    text_matches_locale,
)

# The exact card from the report: Turkish course, Arabic support locale,
# personal cloze card whose translation was never rendered into Arabic.
REPORTED = {
    "card_type": "personal",
    "sentence": "Bu şehir çok {{answer}} ve orada milyonlarca insan yaşıyor.",
    "correct_answer": "büyük",
    "hint": "büyük",
    "translation": "This city is very big and millions of people live there.",
}


class TestTheReportedCard:
    def test_the_english_translation_is_caught(self):
        assert mismatched_fields(REPORTED, "ar") == ["translation"]

    def test_the_personal_card_hint_is_not_caught(self):
        # A personal card's hint IS its answer — the learner's own word in
        # the language being STUDIED. Flagging it would mark every personal
        # card of every non-Latin learner.
        assert "hint" not in mismatched_fields(REPORTED, "ar")

    def test_once_translated_nothing_is_flagged(self):
        card = dict(REPORTED, translation="هذه المدينة كبيرة جداً ويعيش فيها ملايين الناس.")
        assert mismatched_fields(card, "ar") == []

    def test_the_card_is_stamped_not_withheld(self):
        # Withholding the only semantic cue would trade a card in the wrong
        # language for one that cannot be answered at all.
        stamped = mark_locale_mismatches(dict(REPORTED), "ar")
        assert stamped["locale_mismatch"] == ["translation"]
        assert stamped["translation"] == REPORTED["translation"]


class TestEveryNonLatinLocale:
    @pytest.mark.parametrize(
        "locale,native,english",
        [
            ("ar", "هذه المدينة كبيرة جداً", "This city is very big"),
            ("fa", "این شهر خیلی بزرگ است", "This city is very big"),
            ("he", "העיר הזאת גדולה מאוד", "This city is very big"),
            ("ru", "Этот город очень большой", "This city is very big"),
            ("el", "Αυτή η πόλη είναι πολύ μεγάλη", "This city is very big"),
            ("hi", "यह शहर बहुत बड़ा है", "This city is very big"),
            ("th", "เมืองนี้ใหญ่มาก", "This city is very big"),
            ("ko", "이 도시는 매우 큽니다", "This city is very big"),
            ("ja", "この街はとても大きい", "This city is very big"),
            ("uk", "Це місто дуже велике", "This city is very big"),
        ],
    )
    def test_native_passes_and_english_is_caught(self, locale, native, english):
        assert text_matches_locale(native, locale) is True
        assert text_matches_locale(english, locale) is False


class TestItDoesNotCryWolf:
    """Every false positive here would flag healthy cards in bulk."""

    @pytest.mark.parametrize("text", ["1991", "3.14", "— , .", "100%", "→"])
    def test_text_with_no_letters_is_never_a_mismatch(self, text):
        assert text_matches_locale(text, "ar") is True

    @pytest.mark.parametrize("text", ["", "   ", None])
    def test_absent_text_is_a_different_bug(self, text):
        assert text_matches_locale(text, "ar") is True

    def test_a_quoted_latin_name_inside_native_prose_passes(self):
        assert text_matches_locale("فيلم Titanic رائع جداً", "ar") is True
        assert text_matches_locale("Он живёт в New York уже год", "ru") is True

    def test_latin_script_locales_are_never_judged(self):
        # "the book" and "el libro" are the same script; guessing here
        # would flag correct Spanish as often as it caught English.
        for locale in ("es", "fr", "pt", "de", "it", "tr", "id", "sw"):
            assert text_matches_locale("This city is very big", locale) is True
            assert mismatched_fields({"translation": "This is English"}, locale) == []

    def test_an_unknown_locale_is_not_judged(self):
        assert script_of("zz") is None
        assert text_matches_locale("anything at all", "zz") is True

    def test_a_regional_tag_still_resolves(self):
        assert script_of("ar-EG") == "ARABIC"
        assert text_matches_locale("This is English", "ar-EG") is False


class TestFieldSelection:
    def test_only_learner_language_fields_are_checked(self):
        # The sentence and the answer are in the language being STUDIED.
        # Checking them against the support locale flags every card.
        card = {
            "card_type": "vocabulary",
            "sentence": "Bu şehir çok {{answer}} ve orada insan yaşıyor.",
            "correct_answer": "büyük",
            "gloss": "bu=this şehir=city",
            "transliteration": "bu şehir çok büyük",
            "translation": "هذه المدينة كبيرة",
            "hint": "كبير",
        }
        assert mismatched_fields(card, "ar") == []

    def test_a_vocabulary_hint_in_english_is_caught(self):
        card = {"card_type": "vocabulary", "hint": "big, large", "translation": "مدينة كبيرة"}
        assert mismatched_fields(card, "ar") == ["hint"]

    def test_every_declared_field_is_actually_checked(self):
        # Guards the list itself: adding a field to LOCALIZED_FIELDS
        # without it being checked would be a silent hole.
        card = {"card_type": "vocabulary"} | {f: "This is English" for f in LOCALIZED_FIELDS}
        assert sorted(mismatched_fields(card, "ar")) == sorted(LOCALIZED_FIELDS)


class TestScriptRatio:
    def test_ratio_ignores_digits_and_punctuation(self):
        assert script_ratio("مدينة، 1991.", "ARABIC") == 1.0

    def test_mostly_latin_with_one_native_word_is_still_a_mismatch(self):
        # The failure mode this must catch: an "Arabic" row that is really
        # an English sentence with a stray native token.
        assert text_matches_locale(
            "This city is very big and millions of people live there مدينة", "ar"
        ) is False


class TestMarkIsAdditive:
    def test_a_clean_card_gains_no_key(self):
        # Absent key means "nothing to report", so older clients and every
        # Latin-script locale see exactly what they saw before.
        card = mark_locale_mismatches({"card_type": "vocabulary", "translation": "مدينة"}, "ar")
        assert "locale_mismatch" not in card

    def test_no_locale_at_all_is_not_an_error(self):
        card = mark_locale_mismatches(dict(REPORTED), None)
        assert "locale_mismatch" not in card
