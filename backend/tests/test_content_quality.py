"""Content-quality audit (backend/services/quality/audit_content.py).

Two halves. The first runs the audit over the real content and holds it to
data/quality/baseline.json — that is the ratchet, and it is the only thing
standing between "Spanish hints give the answer away" and it happening again
in a language nobody is reading this week.

The second half pins the false-positive guards to synthetic drills. Those are
the part that decides whether anyone trusts the checker: a leak rule that flags
`trabajar, él/ella` for answer `trabaja` (the standard "infinitive, person"
convention) gets switched off within a week, and then the real leaks go with it.
"""
from __future__ import annotations

from backend.services.quality.audit_content import (
    FAIL_RULES,
    LANGUAGES,
    audit_all,
    audit_points,
    load_baseline,
    regressions,
)


def _point(*drills, title="Test point", explanation="An explanation."):
    return {"title": title, "explanation": explanation, "drills": list(drills)}


def _drill(sentence, answer, hint, translation="A translation of the sentence."):
    return {
        "sentence": sentence,
        "answer": answer,
        "hint": hint,
        "translation": translation,
    }


class TestBaselineRatchet:
    """The whole audit against the committed baseline."""

    def test_no_fail_level_rule_exceeds_its_baseline(self):
        reports = audit_all(LANGUAGES)
        baseline = load_baseline()
        failures = regressions(reports, baseline)
        if failures:
            by_code = {r["code"]: r for r in reports}
            lines = []
            for code, rule, count, allowed in failures:
                lines.append(f"{code}.{rule}: {count} (baseline {allowed})")
                lines += [f"    {row}" for row in by_code[code]["findings"][rule][:3]]
            raise AssertionError(
                "content quality regressed past data/quality/baseline.json:\n"
                + "\n".join(lines)
                + "\n\nFix the content, or record the new level deliberately with\n"
                "  python -m backend.services.quality.audit_content --update-baseline"
            )

    def test_baseline_only_records_fail_level_rules(self):
        # A warn-level count in the baseline would imply it gates CI. It does not.
        for key in load_baseline():
            code, _, rule = key.partition(".")
            assert code in LANGUAGES, key
            assert rule in FAIL_RULES, key

    def test_ratchet_fires_on_an_increase(self):
        counts = dict.fromkeys(FAIL_RULES, 0)
        counts["leak_hard"] = 3
        report = {"code": "es", "counts": counts}
        assert regressions([report], {"es.leak_hard": 3}) == []
        assert regressions([report], {"es.leak_hard": 2}) == [("es", "leak_hard", 3, 2)]
        assert regressions([report], {}) == [("es", "leak_hard", 3, 0)]


class TestLeakGuards:
    """What separates a leaked answer from an authoring convention."""

    def test_answer_inside_a_longer_word_is_not_a_leak(self):
        # "trabajar, él/ella" is the infinitive-person convention: the drilled
        # form trabaja is only a substring of the citation form.
        points = [_point(_drill("Él {{answer}} aquí.", "trabaja", "trabajar, él/ella"))]
        assert audit_points("es", points)["leak_hard"] == []

    def test_whole_word_answer_in_the_hint_is_a_leak(self):
        points = [_point(_drill("Él {{answer}} aquí.", "trabaja", "trabaja, él/ella"))]
        assert len(audit_points("es", points)["leak_hard"]) == 1

    def test_short_english_function_word_collision_is_not_a_leak(self):
        # Spanish personal "a" colliding with the English article in hint prose.
        points = [_point(_drill("Veo {{answer}} Juan.", "a", "before a person"))]
        assert audit_points("es", points)["leak_hard"] == []

    def test_hint_that_is_only_the_answer_is_still_a_leak(self):
        # pt "me | me" and nl "is | is": the collision guard must not cover these.
        points = [_point(_drill("Ele {{answer}} viu.", "me", "me"))]
        assert len(audit_points("pt", points)["leak_hard"]) == 1

    def test_self_answering_template_flags(self):
        points = [
            _point(
                _drill(
                    "{{answer}} kamu suka kopi?",
                    "apakah",
                    "apakah — marks a yes/no question",
                    translation="Do you like coffee?",
                )
            )
        ]
        findings = audit_points("id", points)
        assert len(findings["self_answering"]) == 1
        # It is a leak as well: naming the pattern does not excuse it.
        assert len(findings["leak_hard"]) == 1

    def test_quoted_construction_is_reported_as_its_own_class(self):
        points = [_point(_drill("Je viens {{answer}} il pleut.", "car", "because (car)"))]
        findings = audit_points("fr", points)
        assert len(findings["construction_quote"]) == 1
        assert len(findings["leak_hard"]) == 1

    def test_arabic_marker_inside_a_marked_up_word_is_not_a_leak(self):
        # A shadda is not a word character, so an unnormalised boundary check
        # reads المحلّفين ("jurors") as المحل + فين and calls it a leak.
        points = [_point(_drill("سأل {{answer}}.", "فين", "asked the jurors المحلّفين"))]
        assert audit_points("ar", points)["leak_hard"] == []


class TestOtherRuleGuards:
    def test_allomorph_set_is_exempt_from_duplicate_hint(self):
        hint = "question particle — harmonize with the last vowel"
        points = [
            _point(
                _drill("Geliyor {{answer}}?", "mu", hint),
                _drill("Güzel {{answer}}?", "mü", hint),
                _drill("Yorgun {{answer}}?", "mı", hint),
            )
        ]
        assert audit_points("tr", points)["duplicate_hint"] == []

    def test_unrelated_answers_under_one_hint_are_flagged(self):
        hint = "part of day — instrumental"
        points = [
            _point(
                _drill("Я работаю {{answer}}.", "утром", hint),
                _drill("Я отдыхаю {{answer}}.", "вечером", hint),
            )
        ]
        assert len(audit_points("ru", points)["duplicate_hint"]) == 1

    def test_same_answer_capitalised_is_not_a_duplicate(self):
        hint = "plural marker"
        points = [
            _point(
                _drill("{{answer}} ọmọ", "Àwọn", hint),
                _drill("mo rí {{answer}} ọmọ", "àwọn", hint),
            )
        ]
        assert audit_points("yo", points)["duplicate_hint"] == []

    def test_gloss_hint_repeated_in_the_translation_is_a_giveaway(self):
        points = [_point(_drill("{{answer}} canta muy bien.", "Ella", "she", "She sings very well."))]
        assert len(audit_points("es", points)["giveaway_by_gloss"]) == 1

    def test_grammar_label_hint_absent_from_the_translation_is_not(self):
        points = [_point(_drill("{{answer}} canta muy bien.", "Ella", "subject pronoun",
                                "She sings very well."))]
        assert audit_points("es", points)["giveaway_by_gloss"] == []

    def test_english_is_exempt_from_vague_translation(self):
        # The `en` course uses the translation field as a usage note by design
        # ("Clock time."), which made 46 of 46 hits false.
        drill = _drill(
            "It is half {{answer}} three in the afternoon.", "past", "after the hour", "Clock time."
        )
        assert audit_points("en", [_point(drill)])["vague_translation"] == []
        assert len(audit_points("de", [_point(drill)])["vague_translation"]) == 1

    def test_empty_fields_are_flagged(self):
        points = [_point(_drill("Ich {{answer}} hier.", "wohne", "", ""), explanation=" ")]
        assert len(audit_points("de", points)["empty"]) == 3

    def test_arabic_dialect_marker_is_flagged_in_a_drill(self):
        points = [_point(_drill("أنا {{answer}} ماء.", "عايز", "want", "I want water."))]
        assert len(audit_points("ar", points)["ar_register"]) == 1

    def test_msa_word_containing_a_marker_as_a_substring_is_not_flagged(self):
        points = [_point(_drill("سأل {{answer}} القاضي.", "المحلّفين", "the jurors",
                                "He asked the jurors."))]
        assert audit_points("ar", points)["ar_register"] == []
