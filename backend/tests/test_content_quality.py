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
    WRONG_SENSE_RANK_BAND,
    audit_all,
    audit_language,
    audit_points,
    load_baseline,
    regressions,
    wrong_sense_kind,
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


class TestAgreementFeature:
    """A hint that is nothing but the agreement feature the drill exists to test.

    `feminine singular` picks `La` out of {el, la, els, les} on its own, so the
    learner never has to know that casa is feminine — the whole exercise. The
    guards are the same shape as the leak guards: one token of real information
    in the hint and the rule stands down."""

    def test_feature_only_hint_on_an_article_drill_flags(self):
        points = [
            _point(
                _drill("{{answer}} casa és gran.", "La", "feminine singular",
                       "The house is big."),
                # Same drill written the way es.md asks for: it names the work
                # instead of doing it, so it must not flag.
                _drill("{{answer}} gat dorm al sofà.", "El",
                       "the definite article — check the noun's gender",
                       "The cat sleeps on the sofa."),
            )
        ]
        findings = audit_points("ca", points)
        assert findings["agreement_feature"] == [
            "[Test point] hint 'feminine singular' -> answer 'La'"
        ]

    def test_infinitive_person_convention_is_not_a_feature_hint(self):
        # The same hint the leak rule already had to be taught to leave alone:
        # lemma plus person, and the learner still has to conjugate.
        points = [
            _point(
                _drill("Él {{answer}} aquí.", "trabaja", "trabajar, él/ella"),
                _drill("Él {{answer}} pan.", "come", "comer, él/ella"),
            )
        ]
        assert audit_points("es", points)["agreement_feature"] == []

    def test_features_plus_real_information_do_not_flag(self):
        # 'the' is an English gloss, 'the verb' names the slot: in points whose
        # answers span word classes those words are doing work, and a rule that
        # guessed which extra words are filler would fire on convention.
        points = [
            _point(
                _drill("{{answer}} gats dormen.", "Els", "the — masculine plural"),
                _drill("Ci {{answer}} due caffè.", "sono", "plural — the verb"),
            )
        ]
        assert audit_points("ca", points)["agreement_feature"] == []

    def test_neuter_and_abbreviated_gender_count(self):
        # 'neuter' (de/el articles) and 'masc. singular' (hi) are the same hint
        # as 'masculine singular'; catching one spelling and not another would
        # be arbitrary.
        points = [
            _point(
                _drill("{{answer}} Haus ist groß.", "Das", "neuter", "The house is big."),
                _drill("{{answer}} Mann ist hier.", "Der", "masc.", "The man is here."),
            )
        ]
        assert len(audit_points("de", points)["agreement_feature"]) == 2

    def test_determiner_word_needs_a_gender_or_number_beside_it(self):
        # 'indefinite' alone labels the slot; 'plural indefinite' (fr `des`)
        # picks the answer.
        points = [
            _point(
                _drill("Elle achète {{answer}} pommes.", "des", "plural indefinite"),
                _drill("Il y a {{answer}} chat.", "un", "indefinite"),
            )
        ]
        assert audit_points("fr", points)["agreement_feature"] == [
            "[Test point] hint 'plural indefinite' -> answer 'des'"
        ]

    def test_person_only_hint_is_not_an_agreement_leak(self):
        # nl 'first person' / 'third singular' on verb drills: the subject is
        # overt in the sentence, so the feature is free information and the form
        # — the thing being taught — is not given away.
        points = [
            _point(
                _drill("Ik {{answer}} het koud.", "heb", "first person"),
                _drill("Hij {{answer}} honger.", "heeft", "third singular"),
            )
        ]
        assert audit_points("nl", points)["agreement_feature"] == []

    def test_point_with_one_answer_gives_nothing_away(self):
        # jam "Plural with dem": every drill answers `dem`, so 'plural' names the
        # function of an invariant marker rather than picking a paradigm member.
        points = [
            _point(
                _drill("Di tiicha {{answer}} taak tuu long.", "dem", "plural",
                       "The teachers talk too long."),
                _drill("Di mango {{answer}} swiit.", "dem", "plural marker",
                       "The mangoes are sweet."),
            )
        ]
        assert audit_points("jam", points)["agreement_feature"] == []

    def test_counts_alongside_giveaway_by_gloss_rather_than_instead_of_it(self):
        # Same convention as self_answering ⊂ leak_hard: each rule names a way a
        # hint fails, and one failure does not excuse another.
        points = [
            _point(
                _drill("Er {{answer}} veel mensen.", "zijn", "plural",
                       "Use the plural form here."),
                _drill("Er {{answer}} een probleem.", "is", "singular",
                       "There is a problem."),
            )
        ]
        findings = audit_points("nl", points)
        assert len(findings["agreement_feature"]) == 2
        assert len(findings["giveaway_by_gloss"]) == 1


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


class TestWrongSenseGloss:
    """The kaikki parser takes the first entry carrying any gloss, with no
    part-of-speech ranking, so a `name`/`character`/`symbol` entry can outrank
    the real word. French rank 15 `ne` — the negator — is glossed as a Swiss
    canton; Yoruba's five commonest grammar words are glossed as letter names.
    """

    def test_letter_name_gloss_on_a_frequent_word_flags(self):
        assert wrong_sense_kind(1, "The name of the Latin script letter T/t.") == "letter name"
        assert wrong_sense_kind(
            3, "The sixteenth letter of the Yoruba alphabet, called ó."
        ) == "letter name"

    def test_region_code_gloss_flags(self):
        assert wrong_sense_kind(15, "ISO 3166-2:CH code of Neuchâtel (canton)") == "region code"

    def test_a_word_that_genuinely_names_a_letter_is_not_flagged(self):
        """The guard the rule stands on. Swahili `herufi`, Greek `χι`, Portuguese
        `fi` and Korean `알파` really do name letters — and every one of them sits
        at rank 2417 or deeper, because naming a letter is not a job a language
        gives a high-frequency word. Flagging these would be flagging correct
        content, and a checker that does that gets switched off.
        """
        for rank, gloss in (
            (2427, "letter (letter of the alphabet)"),
            (3798, "chi, the 22nd letter in the modern Greek alphabet."),
            (7198, "phi (name of the Greek letter Φ)"),
            (2417, "alpha (name of the Greek, Ancient Greek letter α)"),
        ):
            assert wrong_sense_kind(rank, gloss) is None, gloss

    def test_the_band_is_the_discriminator(self):
        gloss = "The name of the Latin script letter T/t."
        assert wrong_sense_kind(WRONG_SENSE_RANK_BAND, gloss) == "letter name"
        assert wrong_sense_kind(WRONG_SENSE_RANK_BAND + 1, gloss) is None

    def test_only_the_leading_sense_counts(self):
        """A gloss that leads with the sense a learner wants is doing its job,
        whatever it says afterwards — Swahili `fedha` is silver AND money."""
        assert wrong_sense_kind(229, "silver (chemical element); money; finance") is None
        assert wrong_sense_kind(
            1, "The name of the Latin script letter T/t.; a relativizer"
        ) == "letter name"

    def test_unranked_or_empty_rows_are_ignored(self):
        assert wrong_sense_kind(0, "The first letter of the alphabet") is None
        assert wrong_sense_kind(-1, "The first letter of the alphabet") is None
        assert wrong_sense_kind(5, "") is None

    def test_the_rule_reads_the_committed_corpora(self):
        """Yoruba is the worst case in the repo and the reason this rule is
        fail-level: its commonest words are glossed as letters of the alphabet.
        """
        findings = audit_language("yo")["findings"]["wrong_sense_gloss"]
        assert findings, "yo has known wrong-sense glosses in its top band"
        assert any("'ti'" in row for row in findings)
