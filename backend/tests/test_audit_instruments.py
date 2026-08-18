"""The Phase 0 measuring instruments (audit_examples, audit_gym).

These two decide what Phases 2 and 4 spend effort on, so a wrong number here
sends real work at the wrong language. The tests pin the decisions that are
easy to get subtly wrong: what counts as a distinct example, what counts as one
structural frame, and the difference between a Gym that hides content and a
language that was never given a Gym at all.
"""
from __future__ import annotations

import json

from backend.services.seeder import audit_examples, audit_gym, audit_polysemy


class TestExampleShape:
    def test_one_frame_with_the_slot_swapped_is_one_shape(self):
        """The reported failure: same length, same opening, one word changed."""
        shapes = {
            audit_examples.shape("Он идёт домой.", "идёт"),
            audit_examples.shape("Он ест домой.", "ест"),
            audit_examples.shape("Он спит домой.", "спит"),
        }
        assert len(shapes) == 1

    def test_a_different_frame_is_a_different_shape(self):
        question = audit_examples.shape("Куда он идёт сегодня вечером?", "идёт")
        statement = audit_examples.shape("Он идёт домой.", "идёт")
        assert question != statement

    def test_the_target_word_is_excluded_from_the_fingerprint(self):
        """Otherwise every sentence differs by its own answer and nothing ever
        collides, which would report a monotone set as varied."""
        a = audit_examples.shape("I eat bread", "eat")
        b = audit_examples.shape("I read bread", "read")
        assert a == b


class TestExampleCounting:
    def test_both_sentence_locations_are_unioned(self, tmp_path, monkeypatch):
        """Neither path alone answers "what does this word have": jam carries 15
        rows in the pipeline file and 356 in the curated one."""
        data = tmp_path
        (data / "sentences").mkdir()
        (data / "zz_sentences.tsv").write_text(
            "word\tsentence\n" "gato\tEl gato duerme.\n", encoding="utf-8"
        )
        (data / "sentences" / "zz_sentences.tsv").write_text(
            "word\tsentence\n" "gato\tUn gato negro corre rapido.\n", encoding="utf-8"
        )
        monkeypatch.setattr(audit_examples, "DATA", data)
        assert len(audit_examples.load_examples("zz")["gato"]) == 2

    def test_the_same_sentence_in_two_locales_counts_once(self, tmp_path, monkeypatch):
        """The English bank stores one row per translation locale, so its
        202,772 rows are 125,387 distinct (word, sentence) pairs. Counting rows
        would report 1.6x the examples that exist."""
        data = tmp_path
        (data / "sentences").mkdir()
        (data / "zz_sentences.tsv").write_text(
            "word\tsentence\ttranslation_locale\n"
            "cat\tThe cat sleeps.\tfr\n"
            "cat\tThe cat sleeps.\tde\n"
            "cat\tThe cat sleeps.\tru\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(audit_examples, "DATA", data)
        assert len(audit_examples.load_examples("zz")["cat"]) == 1

    def test_a_word_with_no_example_is_uncovered_not_thin(self, tmp_path, monkeypatch):
        """Sourcing and diversity are different problems with different fixes and
        costs an order of magnitude apart, so they are counted apart."""
        data = tmp_path
        (data / "sentences").mkdir()
        (data / "zz_frequency.tsv").write_text(
            "rank\tword\tpos\ten\n1\tuno\tnum\tone\n2\tdos\tnum\ttwo\n", encoding="utf-8"
        )
        (data / "zz_sentences.tsv").write_text(
            "word\tsentence\nuno\tSolo uno queda aqui.\n", encoding="utf-8"
        )
        monkeypatch.setattr(audit_examples, "DATA", data)
        report = audit_examples.audit_language("zz", band=10)
        assert [r["word"] for r in report["uncovered"]] == ["dos"]
        assert [r["word"] for r in report["thin"]] == ["uno"]

    def test_a_language_with_no_frequency_list_reports_its_state(self, tmp_path, monkeypatch):
        """Reporting 0% would claim a measured gap where nothing was measured."""
        (tmp_path / "sentences").mkdir()
        monkeypatch.setattr(audit_examples, "DATA", tmp_path)
        assert audit_examples.audit_language("zz")["state"] == "no frequency list"


def _write_gym_fixture(tmp_path, manifest: dict | None, points: list[dict]):
    (tmp_path / "grammar").mkdir(exist_ok=True)
    (tmp_path / "gym").mkdir(exist_ok=True)
    (tmp_path / "grammar" / "zz_grammar.json").write_text(
        json.dumps({"lists": [], "points": points}), encoding="utf-8"
    )
    if manifest is not None:
        (tmp_path / "gym" / "zz.json").write_text(json.dumps(manifest), encoding="utf-8")


def _point(title, drills=8, level="A2"):
    return {
        "title": title,
        "level": level,
        "drills": [{"sentence": f"x {{{{answer}}}} {i}", "answer": "y"} for i in range(drills)],
    }


def _entry(point, **kw):
    base = {"point": point, "label": "L", "usage": "U", "example": "E"}
    base.update(kw)
    return base


class TestGymBreadth:
    def test_a_drilled_point_absent_from_the_picker_is_hidden(self, tmp_path, monkeypatch):
        _write_gym_fixture(
            tmp_path,
            {"columns": [{"kind": "verbs", "entries": [_entry("Shown")]}]},
            [_point("Shown"), _point("The passive")],
        )
        monkeypatch.setattr(audit_gym, "GRAMMAR_DIR", tmp_path / "grammar")
        monkeypatch.setattr(audit_gym, "GYM_DIR", tmp_path / "gym")
        assert audit_gym.audit_language("zz")["hidden"] == ["The passive"]

    def test_an_explicit_exclusion_is_a_decision_not_drift(self, tmp_path, monkeypatch):
        """The whole point of the escape hatch: absence should be reviewable."""
        _write_gym_fixture(
            tmp_path,
            {
                "columns": [
                    {
                        "kind": "verbs",
                        "entries": [_entry("Shown"), {"point": "The passive", "excluded": "receptive only"}],
                    }
                ]
            },
            [_point("Shown"), _point("The passive")],
        )
        monkeypatch.setattr(audit_gym, "GRAMMAR_DIR", tmp_path / "grammar")
        monkeypatch.setattr(audit_gym, "GYM_DIR", tmp_path / "gym")
        report = audit_gym.audit_language("zz")
        assert report["hidden"] == []
        assert report["excluded"] == [{"point": "The passive", "reason": "receptive only"}]

    def test_a_barely_drilled_point_is_not_counted_as_hidden(self, tmp_path, monkeypatch):
        """A stub is not a form the picker is failing to offer."""
        _write_gym_fixture(tmp_path, {"columns": []}, [_point("Stub", drills=2)])
        monkeypatch.setattr(audit_gym, "GRAMMAR_DIR", tmp_path / "grammar")
        monkeypatch.setattr(audit_gym, "GYM_DIR", tmp_path / "gym")
        assert audit_gym.audit_language("zz")["hidden"] == []

    def test_no_manifest_is_its_own_state(self, tmp_path, monkeypatch):
        """Seven languages have no Gym at all. Reporting that as 0% coverage
        would read as a regression rather than a feature never switched on."""
        _write_gym_fixture(tmp_path, None, [_point("Something")])
        monkeypatch.setattr(audit_gym, "GRAMMAR_DIR", tmp_path / "grammar")
        monkeypatch.setattr(audit_gym, "GYM_DIR", tmp_path / "gym")
        assert audit_gym.audit_language("zz")["state"] == "no manifest"


class TestGymDepthAndCopy:
    def test_a_dangling_entry_is_reported(self, tmp_path, monkeypatch):
        """`point` resolves to an id at request time, so a title matching nothing
        is an empty picker row rather than a harmless typo."""
        _write_gym_fixture(
            tmp_path,
            {"columns": [{"kind": "verbs", "entries": [_entry("Renamed away")]}]},
            [_point("Actual title")],
        )
        monkeypatch.setattr(audit_gym, "GRAMMAR_DIR", tmp_path / "grammar")
        monkeypatch.setattr(audit_gym, "GYM_DIR", tmp_path / "gym")
        report = audit_gym.audit_language("zz")
        assert report["dangling"] == [{"point": "Renamed away", "column": "verbs"}]
        assert report["shown"] == 0

    def test_a1_forms_carry_the_higher_floor(self, tmp_path, monkeypatch):
        _write_gym_fixture(
            tmp_path,
            {
                "columns": [
                    {
                        "kind": "verbs",
                        "entries": [_entry("Beginner"), _entry("Later")],
                    }
                ]
            },
            [_point("Beginner", drills=11, level="A1"), _point("Later", drills=11, level="B1")],
        )
        monkeypatch.setattr(audit_gym, "GRAMMAR_DIR", tmp_path / "grammar")
        monkeypatch.setattr(audit_gym, "GYM_DIR", tmp_path / "gym")
        report = audit_gym.audit_language("zz")
        assert [row["point"] for row in report["thin_forms"]] == ["Beginner"]
        assert report["deficit"] == 1

    def test_an_entry_missing_its_copy_is_reported(self, tmp_path, monkeypatch):
        _write_gym_fixture(
            tmp_path,
            {"columns": [{"kind": "verbs", "entries": [_entry("Shown", usage="", example="")]}]},
            [_point("Shown", drills=12)],
        )
        monkeypatch.setattr(audit_gym, "GRAMMAR_DIR", tmp_path / "grammar")
        monkeypatch.setattr(audit_gym, "GYM_DIR", tmp_path / "gym")
        assert audit_gym.audit_language("zz")["incomplete_copy"] == [
            {"point": "Shown", "missing": ["usage", "example"]}
        ]


def _write_polysemy_fixture(tmp_path, freq_rows, kaikki_lines):
    (tmp_path / "raw").mkdir(exist_ok=True)
    (tmp_path / "zz_frequency.tsv").write_text(
        "rank\tword\tpos\ten\n" + "".join(freq_rows), encoding="utf-8"
    )
    (tmp_path / "raw" / "zz_kaikki.jsonl").write_text(
        "".join(kaikki_lines), encoding="utf-8"
    )


class TestPolysemy:
    """A card has room for one gloss; Portuguese `a` is six words."""

    def test_a_word_with_several_senses_and_a_single_gloss_flags(self, tmp_path, monkeypatch):
        _write_polysemy_fixture(
            tmp_path,
            ["2\ta\tarticle\tthe (feminine singular)\n"],
            [
                '{"word": "a", "pos": "article", "senses": [{"glosses": ["the"]}]}\n',
                '{"word": "a", "pos": "prep", "senses": [{"glosses": ["to, at"]}]}\n',
                '{"word": "a", "pos": "pron", "senses": [{"glosses": ["her, it"]}]}\n',
            ],
        )
        monkeypatch.setattr(audit_polysemy, "DATA", tmp_path)
        monkeypatch.setattr(audit_polysemy, "RAW", tmp_path / "raw")
        report = audit_polysemy.audit_language("zz")
        assert [r["word"] for r in report["polysemous"]] == ["a"]
        assert report["polysemous"][0]["named"] == 1
        assert len(report["polysemous"][0]["senses"]) == 3

    def test_a_gloss_that_names_every_sense_does_not_flag(self, tmp_path, monkeypatch):
        """The fix for this class is a multi-sense gloss, so one must clear it."""
        _write_polysemy_fixture(
            tmp_path,
            ["2\ta\tarticle\tthe (feminine); to, at; her, it\n"],
            [
                '{"word": "a", "pos": "article", "senses": [{"glosses": ["the"]}]}\n',
                '{"word": "a", "pos": "prep", "senses": [{"glosses": ["to, at"]}]}\n',
                '{"word": "a", "pos": "pron", "senses": [{"glosses": ["her, it"]}]}\n',
            ],
        )
        monkeypatch.setattr(audit_polysemy, "DATA", tmp_path)
        monkeypatch.setattr(audit_polysemy, "RAW", tmp_path / "raw")
        assert audit_polysemy.audit_language("zz")["polysemous"] == []

    def test_two_senses_are_ordinary_polysemy_and_do_not_flag(self, tmp_path, monkeypatch):
        """One gloss can carry "bank"; it cannot carry six unrelated words."""
        _write_polysemy_fixture(
            tmp_path,
            ["2\tb\tnoun\ta financial institution\n"],
            [
                '{"word": "b", "pos": "noun", "senses": [{"glosses": ["a bank"]}]}\n',
                '{"word": "b", "pos": "verb", "senses": [{"glosses": ["to bank"]}]}\n',
            ],
        )
        monkeypatch.setattr(audit_polysemy, "DATA", tmp_path)
        monkeypatch.setattr(audit_polysemy, "RAW", tmp_path / "raw")
        assert audit_polysemy.audit_language("zz")["polysemous"] == []

    def test_a_glyph_entry_is_not_a_competing_sense(self, tmp_path, monkeypatch):
        """`character` and `name` entries are the wrong-sense bug, ranked out by
        source_data — counting them here would double-report that defect."""
        _write_polysemy_fixture(
            tmp_path,
            ["2\ta\tprep\tto, at\n"],
            [
                '{"word": "a", "pos": "prep", "senses": [{"glosses": ["to, at"]}]}\n',
                '{"word": "a", "pos": "character", "senses": [{"glosses": ["letter A"]}]}\n',
                '{"word": "a", "pos": "name", "senses": [{"glosses": ["a place"]}]}\n',
            ],
        )
        monkeypatch.setattr(audit_polysemy, "DATA", tmp_path)
        monkeypatch.setattr(audit_polysemy, "RAW", tmp_path / "raw")
        assert audit_polysemy.audit_language("zz")["polysemous"] == []

    def test_a_recorded_pos_absent_from_the_extract_is_reported(self, tmp_path, monkeypatch):
        _write_polysemy_fixture(
            tmp_path,
            ["2\ta\tnoun\tsomething\n"],
            ['{"word": "a", "pos": "prep", "senses": [{"glosses": ["to, at"]}]}\n'],
        )
        monkeypatch.setattr(audit_polysemy, "DATA", tmp_path)
        monkeypatch.setattr(audit_polysemy, "RAW", tmp_path / "raw")
        assert audit_polysemy.audit_language("zz")["mismatched"][0]["pos"] == "noun"

    def test_a_missing_extract_is_unknown_not_clean(self, tmp_path, monkeypatch):
        """data/raw is a 7GB cache and deliberately uncommitted, so its absence
        must never read as a language with no polysemy."""
        (tmp_path / "raw").mkdir()
        (tmp_path / "zz_frequency.tsv").write_text(
            "rank\tword\tpos\ten\n1\ta\tprep\tto\n", encoding="utf-8"
        )
        monkeypatch.setattr(audit_polysemy, "DATA", tmp_path)
        monkeypatch.setattr(audit_polysemy, "RAW", tmp_path / "raw")
        assert audit_polysemy.audit_language("zz")["state"] == "no extract cached"


class TestAgainstTheRealTree:
    def test_english_hides_the_forms_the_plan_named(self):
        """docs/plans/gym-coverage.md measured English at 12 shown and 31 hidden,
        and named the passive and relative clauses among the hidden. If this
        drifts, either the content moved or the instrument broke."""
        report = audit_gym.audit_language("en")
        assert report["shown"] == 12
        assert len(report["hidden"]) == 31

    def test_no_language_has_a_dangling_picker_entry(self):
        """A dangling entry shows the learner an empty form, so this should stay
        at zero even as manifests grow."""
        broken = {
            r["code"]: r["dangling"] for r in audit_gym.audit_all() if r.get("dangling")
        }
        assert not broken, broken
