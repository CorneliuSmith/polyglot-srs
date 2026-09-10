"""The corpus writes about itself, and those rows reached 14 courses.

Tatoeba's bank contains sentences about Tatoeba — "In its home country,
France, Tatoeba became a social and cultural revolution", '"Tatoeba" means
"for example" in Japanese' — and the sentence builder selected them like any
other row, by difficulty. So the Catalan card for `exemple` taught what the
corpus's name means in Japanese, and the Arabic card for `اجتماعية`
("social") taught the corpus's press release. 59 rows across 14 courses,
measured 10 Sep 2026.

Removing them from the files is not enough: a rebuild from Tatoeba would
select them again (quality rule 27 — a file-only deletion is undone by the
next regeneration). So the predicate lives in the prune, the builder drops
them at the source, the floor script drops them from the banks, and the
invariant below is what stops them coming back unnoticed.

No database: these are file and predicate facts, so they run in every sweep.
"""
from __future__ import annotations

import collections
import csv
import glob
import os

import pytest

from backend.services.seeder.prune_sentences import (
    UNSPACED,
    names_the_corpus,
)


class TestThePredicate:
    @pytest.mark.parametrize("sentence", [
        '"Tatoeba" means "for example" in Japanese.',
        "Benvinguts a Tatoeba!",
        "I would love to write hundreds of sentences on TATOEBA.",
        # The Arabic and Persian transliterations: a bare "tatoeba" pattern
        # missed 16 of the 17 Arabic rows, which is why they are listed.
        "تتويبا متعدد اللغات حقًّا.",
        "لقد أصبح موقع تاتوبا في فرنسا، أي موطن نشأته، ظاهرة ثقافية.",
        "شديدي التدقيق لا يشكلون الاغلبية في موقع تاتويبا.",
        'تاتوئبا به ژاپنی یعنی "برای مثال".',
    ])
    def test_it_catches_a_row_about_the_corpus(self, sentence):
        assert names_the_corpus(sentence)

    @pytest.mark.parametrize("sentence", [
        "I didn't go to work yesterday.",
        "Every language that dies out takes a piece of human history with it.",
        "هذا مثال على الجملة العربية.",
        "",
    ])
    def test_it_leaves_an_ordinary_sentence_alone(self, sentence):
        assert not names_the_corpus(sentence)

    def test_it_reads_the_sentence_only(self):
        """Never the translation. The file holds one row per sentence; the
        database holds that sentence once per LOCALE, so keying on the
        translation would delete some locales' copies and keep others — the
        invariant `prune_sentences` states in its own docstring. Every one of
        the 59 measured rows names the corpus in its own language, so the
        predicate never needs the translation to decide."""
        assert names_the_corpus.__code__.co_argcount == 1


def _bank_rows():
    for path in sorted(glob.glob("data/*_sentences.tsv")) + sorted(
            glob.glob("data/sentences/*_sentences.tsv")):
        code = os.path.basename(path).split("_")[0]
        with open(path, encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                yield code, path, row


def test_no_bank_names_the_corpus_beside_a_usable_row():
    """The invariant, and the reason it is shaped this way.

    14 of the 59 were the ONLY sentence their word had, and the programme's
    standing rule is never to strand a word (CHECKS §24, `_context_free`):
    a card with no example at all is not an improvement on a bad one. Those
    14 stay until authoring replaces them, and they are an entry on the
    Phase 8 supply list, not a deletion.

    So the assertion is not "zero rows" — it is that no such row survives
    ALONGSIDE a usable sentence. That cannot be satisfied by a rebuild
    quietly reintroducing them, and it ratchets: every word that gets an
    authored sentence takes its corpus row with it.
    """
    by_word: dict[tuple[str, str, str], list[dict]] = collections.defaultdict(list)
    for code, path, row in _bank_rows():
        by_word[(code, path, (row.get("word") or "").strip())].append(row)

    offenders = []
    for (code, path, word), group in by_word.items():
        named = [r for r in group if names_the_corpus(r.get("sentence") or "")]
        if named and len(named) != len(group):
            offenders.append(f"{code}/{word} in {os.path.basename(path)}: "
                             f"{len(named)} of {len(group)} name the corpus")
    assert not offenders, (
        f"{len(offenders)} word(s) serve a sentence about the corpus while a "
        f"usable one exists — run scripts/enforce_sentence_floor.py: {offenders[:5]}"
    )


def test_thai_is_exempt_from_the_floor_but_not_from_this():
    """§22 exempts Thai from the five-token floor because it writes without
    spaces, so a token count says nothing. The corpus rule counts nothing, so
    the exemption must not reach it — it did at first, and Thai's one row
    survived a full pass."""
    assert "th" in UNSPACED
    source = open("scripts/enforce_sentence_floor.py", encoding="utf-8").read()
    corpus_at = source.index("names_the_corpus(r.get")
    floor_at = source.index("if code in UNSPACED")
    assert corpus_at < floor_at, (
        "the corpus rule must be applied before the UNSPACED floor exemption, "
        "or Thai keeps its corpus rows"
    )
