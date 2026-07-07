"""Tests for the gap-hunting sentence rotation (paradigm-aware reviews).

A paradigm point (subject pronouns, a conjugation table) is really N
questions wearing one card: rotation must test unseen sentences first, then
hunt the ones the learner keeps missing — deterministically, so a page
reload mid-review never changes the sentence.
"""
from backend.repositories.cards import _pick_index

PROMPTS = [
    "{{answer}} soy de México.",       # yo
    "{{answer}} eres mi amigo.",       # tú
    "{{answer}} es mi hermana.",       # ella
    "{{answer}} somos estudiantes.",   # nosotros
    "¿{{answer}} es el doctor Ruiz?",  # usted
]


class TestPickIndex:
    def test_unseen_sentences_come_first(self):
        # Two sentences already seen -> the pick must be one of the other three.
        stats = {PROMPTS[0]: (3, 0), PROMPTS[1]: (1, 0)}
        idx = _pick_index(PROMPTS, None, stats, "card:1:0:")
        assert idx in (2, 3, 4)

    def test_cycles_through_every_unseen_before_repeating(self):
        # Simulate appearances: each answer marks the sentence seen and
        # changes the rotation key. All 5 must appear before any repeats.
        stats: dict[str, tuple[int, int]] = {}
        shown = []
        last = None
        for rep in range(5):
            idx = _pick_index(PROMPTS, last, stats, f"card:{rep}:0:{last or ''}")
            shown.append(idx)
            last = PROMPTS[idx]
            seen, miss = stats.get(last, (0, 0))
            stats[last] = (seen + 1, miss)
        assert sorted(shown) == [0, 1, 2, 3, 4]  # full paradigm coverage

    def test_hunts_the_missed_sentence(self):
        # Everything seen; 'usted' keeps failing -> it comes back.
        stats = {
            PROMPTS[0]: (3, 0), PROMPTS[1]: (3, 0), PROMPTS[2]: (3, 0),
            PROMPTS[3]: (3, 0), PROMPTS[4]: (3, 2),
        }
        assert _pick_index(PROMPTS, None, stats, "card:9:2:x") == 4

    def test_worst_miss_rate_wins(self):
        # 1/3 missed vs 2/2 missed -> the 100% miss rate is hunted first.
        stats = {
            PROMPTS[0]: (3, 1), PROMPTS[1]: (2, 2), PROMPTS[2]: (5, 0),
            PROMPTS[3]: (5, 0), PROMPTS[4]: (5, 0),
        }
        assert _pick_index(PROMPTS, None, stats, "k") == 1

    def test_never_repeats_the_last_shown(self):
        # The missed sentence IS the last shown -> something else appears
        # (the in-session re-drill already handled the immediate retry).
        stats = {p: (2, 0) for p in PROMPTS}
        stats[PROMPTS[4]] = (2, 2)
        idx = _pick_index(PROMPTS, PROMPTS[4], stats, "card:5:1:usted")
        assert idx != 4
        # ...but the very next appearance goes straight back to it.
        assert _pick_index(PROMPTS, PROMPTS[idx], stats, "card:6:1:other") == 4

    def test_uniform_when_all_seen_and_clean(self):
        stats = {p: (2, 0) for p in PROMPTS}
        idx = _pick_index(PROMPTS, PROMPTS[0], stats, "card:7:0:a")
        assert idx in (1, 2, 3, 4)

    def test_deterministic_for_same_state(self):
        stats = {PROMPTS[0]: (1, 1)}
        picks = {
            _pick_index(PROMPTS, None, stats, "card:3:1:z") for _ in range(20)
        }
        assert len(picks) == 1  # reload-stable

    def test_single_sentence_card(self):
        assert _pick_index(["only"], "only", {}, "k") == 0
