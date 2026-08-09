"""The written trivia baseline.

The corpus is data, so the tests are about its shape rather than its
behaviour: a question added in one locale and forgotten in another shrinks
somebody's bank silently, and an answer index that drifted when options
were reordered during translation makes the game wrong in one language
only. Neither shows up in review, so both are checked here.
"""
from __future__ import annotations

import pytest

from backend.services.trivia_corpus import (
    _QUESTIONS,
    LOCALES,
    offline_questions,
    seed_questions,
)


def test_every_question_exists_in_every_ui_locale():
    for i, entry in enumerate(_QUESTIONS):
        missing = [loc for loc in LOCALES if loc not in entry]
        assert not missing, f"question {i} is missing {missing}"


def test_the_options_line_up_across_locales():
    # One answer index is shared by all six translations, so the options
    # have to stay in the same ORDER — translated in place, not reordered
    # to read more naturally. A differing count is the loudest symptom.
    for i, entry in enumerate(_QUESTIONS):
        counts = {loc: len(entry[loc]["options"]) for loc in LOCALES}
        assert len(set(counts.values())) == 1, f"question {i}: {counts}"
        assert 0 <= entry["answer"] < min(counts.values()), f"question {i}"


@pytest.mark.parametrize("locale", LOCALES)
def test_each_locale_has_a_usable_bank(locale):
    items = seed_questions(locale)
    # Enough to outlast a wait screen, which asks for eight at a time.
    assert len(items) >= 15
    for it in items:
        assert it["question"].strip()
        assert it["fact"].strip()
        # The migration's CHECK constraint; failing it would abort the
        # insert for the whole batch.
        assert 2 <= len(it["options"]) <= 5
        assert 0 <= it["answer_index"] < len(it["options"])


@pytest.mark.parametrize("locale", LOCALES)
def test_no_duplicate_questions_within_a_locale(locale):
    # (locale, question) is UNIQUE in the bank, so duplicates here would
    # quietly store fewer rows than the corpus claims to hold.
    qs = [it["question"] for it in seed_questions(locale)]
    assert len(qs) == len(set(qs))


def test_translations_are_not_just_the_english_left_in_place():
    # The whole point of writing the corpus by hand is that it exists in
    # each language. An entry copied from English and never translated
    # would pass every structural check above.
    english = {it["question"] for it in seed_questions("en")}
    for locale in LOCALES:
        if locale == "en":
            continue
        shared = english & {it["question"] for it in seed_questions(locale)}
        assert not shared, f"{locale} still carries English: {shared}"


def test_an_unknown_locale_gets_nothing_rather_than_english():
    # A German learner is better served by the generator writing them
    # something than by an English game they did not ask for.
    assert seed_questions("de") == []
    assert offline_questions("de", 8) == []


def test_offline_ids_are_stable_and_distinct():
    """The DRAW is random — a fixed slice made every visit to the offline
    path the same questions in the same order — but each question's id must
    stay stable across calls and processes, because the client posts ids
    back to /trivia/seen."""
    a = offline_questions("es", 8)
    assert len(a) == 8
    assert len({x["id"] for x in a}) == 8
    # Same question text → same id, wherever and whenever it was drawn.
    ids = {}
    for _ in range(6):
        for item in offline_questions("es", 20):
            assert ids.setdefault(item["question"], item["id"]) == item["id"]
    # Same question, different locale, different row.
    es = {x["question"]: x["id"] for x in offline_questions("es", 72)}
    fr = {x["id"] for x in offline_questions("fr", 72)}
    assert not fr & set(es.values())


def test_offline_questions_are_ready_to_serve():
    for it in offline_questions("ar", 5):
        assert set(it) == {"id", "question", "options", "answer_index", "fact"}
