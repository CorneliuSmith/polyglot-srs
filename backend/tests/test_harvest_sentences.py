"""Unit tests for the WP25(d) sentence harvest loop's pure logic."""
from __future__ import annotations

from backend.services.seeder.harvest_sentences import (
    PER_RUN_CAP,
    TARGET_EXAMPLES,
    collect_candidates,
    fold_free_present,
)


class TestAccentSensitiveMatch:
    def test_exact_form_matches(self):
        assert fold_free_present("el", "¿Cómo está el tiempo?")

    def test_diacritic_twin_never_matches(self):
        # The él/el lesson: a folded twin must not nominate the sentence.
        assert not fold_free_present("el", "Es él.")
        assert not fold_free_present("ano", "Tiene cinco años.")

    def test_word_boundaries_hold(self):
        assert not fold_free_present("el", "Elena canta.")


class TestCollectCandidates:
    NEEDY = {"casa": {"id": "v-casa", "have": 0}}

    def test_picks_matching_sentences_with_translations(self):
        picked = collect_candidates(
            self.NEEDY,
            [{"text": "La casa es grande.", "translation": "The house is big."},
             {"text": "No hay perro aquí.", "translation": "No dog here."}],
            existing=set(),
        )
        assert [p["sentence"] for p in picked] == ["La casa es grande."]
        assert picked[0]["vocabulary_id"] == "v-casa"

    def test_respects_per_run_cap(self):
        sentences = [
            {"text": f"La casa número {i} es azul.", "translation": f"House {i}."}
            for i in range(PER_RUN_CAP + 3)
        ]
        picked = collect_candidates(self.NEEDY, sentences, existing=set())
        assert len(picked) == PER_RUN_CAP

    def test_respects_target_total(self):
        # A word one short of TARGET_EXAMPLES takes exactly one more.
        needy = {"casa": {"id": "v-casa", "have": TARGET_EXAMPLES - 1}}
        sentences = [
            {"text": "La casa es roja.", "translation": "The house is red."},
            {"text": "Mi casa es azul.", "translation": "My house is blue."},
        ]
        picked = collect_candidates(needy, sentences, existing=set())
        assert len(picked) == 1

    def test_skips_existing_and_duplicate_sentences(self):
        sentences = [
            {"text": "La casa es roja.", "translation": "The house is red."},
            {"text": "La casa es roja.", "translation": "The house is red."},
        ]
        picked = collect_candidates(
            self.NEEDY, sentences,
            existing={("casa", "La casa es roja.")},
        )
        assert picked == []

    def test_skips_sentences_without_translation(self):
        picked = collect_candidates(
            self.NEEDY,
            [{"text": "La casa es roja.", "translation": ""}],
            existing=set(),
        )
        assert picked == []
