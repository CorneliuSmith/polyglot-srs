"""Which sense of an English word the course teaches.

WordNet returns nouns first, so the third commonest word in the language
shipped as beryllium. These pin the rule that replaced that — and, just as
importantly, pin that the rule does NOT reach for a part-of-speech preference,
which would fix `be` and break `time`.
"""
from __future__ import annotations

from backend.services.seeder.wordnet_sense import best_synset


class _Lemma:
    def __init__(self, name, count):
        self._name, self._count = name, count

    def name(self):
        return self._name

    def count(self):
        return self._count


class _Synset:
    def __init__(self, label, lemmas):
        self.label, self._lemmas = label, lemmas

    def lemmas(self):
        return self._lemmas


def _syn(label, word, count):
    return _Synset(label, [_Lemma(word, count)])


class TestBestSynset:
    def test_the_most_used_sense_wins_over_wordnets_first(self):
        """`be` shipped as "a light strong brittle grey toxic bivalent metallic
        element" because WordNet lists beryllium first. It is tagged zero times
        in the corpus; the copula is tagged 10,742 times."""
        beryllium = _syn("beryllium.n.01", "Be", 0)
        copula = _syn("be.v.01", "be", 10742)
        assert best_synset("be", [beryllium, copula]) is copula

    def test_a_noun_still_wins_when_it_is_the_used_sense(self):
        """The counts have to decide both directions. A rule that preferred
        verbs would fix `be` and break `time`, `year` and `way`."""
        noun = _syn("time.n.01", "time", 900)
        verb = _syn("time.v.01", "time", 3)
        assert best_synset("time", [noun, verb]) is noun

    def test_untagged_senses_fall_back_to_wordnets_order(self):
        """For a rare word every count is zero and WordNet's own order is the
        best guide left — falling back is not the same as guessing."""
        first = _syn("rare.n.01", "rare", 0)
        second = _syn("rare.a.01", "rare", 0)
        assert best_synset("rare", [first, second]) is first

    def test_a_lemma_for_a_different_word_does_not_vote(self):
        """A synset is reached through many lemmas; only the one spelled like
        the headword says how often THIS word carries that sense."""
        other = _Synset("x.n.01", [_Lemma("something_else", 5000)])
        ours = _syn("x.v.01", "x", 7)
        assert best_synset("x", [other, ours]) is ours

    def test_multiword_lemmas_match_on_spaces(self):
        syn = _syn("ice_cream.n.01", "ice_cream", 12)
        assert best_synset("ice cream", [syn]) is syn

    def test_no_synsets_returns_none(self):
        assert best_synset("zzz", []) is None
