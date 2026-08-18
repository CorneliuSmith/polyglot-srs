"""Picking the sense of an English word a learner actually means.

The English course builds its definitions from WordNet, and WordNet returns
nouns first. So the third commonest word in the language, `be`, shipped as "a
light strong brittle grey toxic bivalent metallic element" — beryllium, whose
chemical symbol is Be. `do` was "an uproarious party", `have` was "a person who
possesses great material wealth", `well` was "a deep hole or shaft dug to obtain
water", and `come` shipped an explicit anatomical definition on a vocabulary
card.

The fix is not a list of exceptions. WordNet ships the signal that settles it:
every lemma carries a frequency count from the sense-tagged corpus, so the
senses of a word are already ranked by how often people mean them. Beryllium
scores 0; the copula scores 10,742.

Deliberately NOT part of this module: any part-of-speech preference. Ranking
noun-below-verb would fix `be` and break `time`, `year`, `way`. The counts
already encode the answer for both, and a rule that guesses where evidence
exists is a rule that will be wrong somewhere nobody is looking.

This file imports nothing from the rest of the codebase on purpose — the
generator that writes the committed gloss column has to run in a bare
environment, and both paths must pick the same sense.
"""
from __future__ import annotations


def best_synset(word: str, synsets: list):
    """The synset for *word* whose lemma is most often used in running text.

    Falls back to WordNet's own first synset when nothing is tagged — for a
    rare word every count is zero, and WordNet's order is then the best guide
    available. Returns None only when *synsets* is empty.
    """
    if not synsets:
        return None
    target = word.lower().replace("_", " ")
    best, best_count = None, -1
    for synset in synsets:
        for lemma in synset.lemmas():
            if lemma.name().lower().replace("_", " ") != target:
                continue
            count = lemma.count()
            if count > best_count:
                best, best_count = synset, count
    return best if best is not None and best_count > 0 else synsets[0]
