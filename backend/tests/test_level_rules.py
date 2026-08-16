"""The level rule — repositories/level.py and its consumers.

Stage 1+2 of docs/plans/adaptive-sessions.md. The bug these pin: "Your
level" in Settings re-seated deck subscriptions and stored nothing, so
the value the user set never reached a single AI prompt — a self-declared
B2 with a young account got A1 content, and the Reader's "stretch" dial
was one soft sentence against a hard cage. The owner's rule, verbatim
intent: the chosen level anchors the session, and an explicit ask for
harder content is given, uncapped.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from backend.repositories.level import (
    chosen_level,
    resolve,
    set_chosen_level,
    shift_level,
)
from backend.services.reader import _system_prompt


class TestTheFloorRule:
    def test_the_chosen_level_is_a_floor(self):
        # Self-declared B2, card evidence says A1 → B2. The whole point.
        assert resolve("B2", "A1") == "B2"

    def test_evidence_may_still_raise_above_the_choice(self):
        # Chose A2 long ago, cards now show B1 work → B1. The floor never
        # becomes a ceiling.
        assert resolve("A2", "B1") == "B1"

    def test_no_choice_means_evidence_decides(self):
        assert resolve(None, "B1") == "B1"

    def test_nothing_at_all_is_a1(self):
        assert resolve(None, None) == "A1"

    def test_garbage_levels_do_not_crash_the_hot_path(self):
        assert resolve("B9", "A2") == "A2"


class TestShift:
    def test_stretch_is_one_full_level_up(self):
        assert shift_level("B1", +1) == "B2"

    def test_easier_is_one_down(self):
        assert shift_level("B1", -1) == "A2"

    def test_clamped_at_both_ends(self):
        assert shift_level("A1", -1) == "A1"
        assert shift_level("C2", +1) == "C2"


class TestDegradation:
    """The migration lands by the owner's hand (CLAUDE.md). Until then,
    every read is 'no floor' — pre-migration behavior — and a Settings
    save loses persistence, never the deck re-seat.

    The HOW matters as much as the WHAT, and it shipped a real outage:
    presence must be probed with to_regclass, because every caller runs
    inside rls_connection's transaction and a thrown UndefinedTableError
    aborts it — Postgres fails every later query in the request no
    matter what Python catches. The tutor 500'd in production within
    hours of a try/except "guard". These tests therefore assert the
    failing query is NEVER ISSUED, not that its error is caught.
    """

    def _absent_conn(self):
        import backend.repositories.level as level_mod

        level_mod._TABLE_SEEN = False
        conn = AsyncMock()
        conn.fetchval = AsyncMock(return_value=False)  # the probe says no
        conn.execute = AsyncMock()
        return conn

    async def test_a_missing_table_reads_as_no_choice_without_erroring(self):
        conn = self._absent_conn()
        assert await chosen_level(conn, "u", "l") is None
        # Exactly one fetchval — the to_regclass probe. The SELECT that
        # would abort the surrounding transaction is never sent.
        assert conn.fetchval.await_count == 1
        assert "to_regclass" in conn.fetchval.await_args.args[0]

    async def test_a_missing_table_makes_the_write_a_soft_no(self):
        conn = self._absent_conn()
        assert await set_chosen_level(conn, "u", "l", "B2") is False
        conn.execute.assert_not_awaited()

    async def test_presence_is_cached_only_once_true(self):
        import backend.repositories.level as level_mod

        level_mod._TABLE_SEEN = False
        conn = AsyncMock()
        # First probe: absent. Second: the migration landed mid-flight.
        conn.fetchval = AsyncMock(side_effect=[False, True, "B2"])
        assert await chosen_level(conn, "u", "l") is None
        assert await chosen_level(conn, "u", "l") == "B2"
        # Cached now — no third probe.
        conn.fetchval = AsyncMock(return_value="B1")
        assert await chosen_level(conn, "u", "l") == "B1"
        assert "learner_levels" in conn.fetchval.await_args.args[0]
        level_mod._TABLE_SEEN = False


class TestTheFloorReachesThePrompts:
    """assessment.get_assessment_summary is the choke point every AI
    feature reads; the floor applied there is the floor applied
    everywhere."""

    async def _summary(self, chosen, card_level="A1"):
        from backend.repositories import assessment

        conn = AsyncMock()
        with patch.object(assessment, "get_learner_model",
                          new=AsyncMock(return_value={
                              "level": card_level, "known_count": 500,
                          })), \
             patch.object(assessment, "get_weak_areas",
                          new=AsyncMock(return_value=[])), \
             patch.object(assessment, "get_language_profile",
                          new=AsyncMock(return_value={"profile": {}})), \
             patch.object(assessment, "get_placement_insight",
                          new=AsyncMock(return_value=None)), \
             patch.object(assessment, "chosen_level",
                          new=AsyncMock(return_value=chosen)):
            return await assessment.get_assessment_summary(
                conn, "u", "l", depth="reading"
            )

    async def test_a_settings_choice_outranks_a_young_card_history(self):
        # 500 cards of mostly-A1 evidence vs. an explicit B2: B2. Before
        # this, the 500 cards won — and studying more entrenched it.
        summary = await self._summary("B2", card_level="A1")
        assert summary["level"] == "B2"
        assert summary["chosen_level"] == "B2"

    async def test_earned_evidence_still_rises_past_the_choice(self):
        summary = await self._summary("A2", card_level="B2")
        assert summary["level"] == "B2"

    async def test_no_choice_changes_nothing(self):
        summary = await self._summary(None, card_level="A2")
        assert summary["level"] == "A2"
        assert "chosen_level" not in summary


class TestReaderDials:
    """The complexity dial is a level shift, not tone (stage 2)."""

    def test_stretch_pitches_one_level_up_and_opens_the_cage(self):
        prompt = _system_prompt(
            "es", "en",
            {"level": "B1", "known_words": ["casa"],
             "learned_structures": ["present tense"]},
            {"complexity": "stretch"},
        )
        assert "pitched at: \nB2" in prompt or "pitched at: B2" in prompt
        # The cage opens: known material is a floor/calibration, not a cap.
        assert "FLOOR, not the limit" in prompt
        assert "NOT a ceiling" in prompt
        assert "prefer structures" not in prompt

    def test_stretch_rises_above_the_chosen_level_uncapped(self):
        # The owner's rule verbatim: "if the user wants harder content
        # above their level give it to them." Their level resolved to C1
        # (chosen or earned) → stretch is C2, no argument.
        prompt = _system_prompt("es", "en", {"level": "C1"},
                                {"complexity": "stretch"})
        assert "pitched at: C2" in prompt

    def test_easier_pitches_one_level_down_with_the_cage_shut(self):
        prompt = _system_prompt("es", "en", {"level": "B1"},
                                {"complexity": "easier"})
        assert "pitched at: A2" in prompt
        assert "prefer structures" in prompt

    def test_level_mode_is_the_cage_at_their_level(self):
        prompt = _system_prompt("es", "en", {"level": "B1"},
                                {"complexity": "level"})
        assert "pitched at: B1" in prompt
        assert "prefer structures" in prompt

    def test_voice_and_length_still_carry(self):
        prompt = _system_prompt(
            "es", "en", {"level": "A2"},
            {"complexity": "stretch", "voice": "dialogue", "length": "long"},
        )
        assert "DIALOGUE" in prompt
        assert "300–400" in prompt

    # The explicit CEFR pins — the owner: "add a1 - c2 levels as an
    # option". An explicit level replaces the relative dial entirely.

    def test_an_explicit_level_pins_the_target_regardless_of_learner(self):
        prompt = _system_prompt("es", "en", {"level": "A1"},
                                {"complexity": "B2"})
        assert "pitched at: B2" in prompt

    def test_explicit_level_above_the_learner_opens_the_cage(self):
        prompt = _system_prompt("es", "en", {"level": "A1"},
                                {"complexity": "B2"})
        assert "FLOOR, not the limit" in prompt

    def test_explicit_level_at_or_below_keeps_the_cage_shut(self):
        # A B2 learner asking for A2 gets a caged A2 text, not a stretch.
        prompt = _system_prompt("es", "en", {"level": "B2"},
                                {"complexity": "A2"})
        assert "pitched at: A2" in prompt
        assert "prefer structures" in prompt

    def test_quality_rules_ride_in_both_cages(self):
        """The Maya regression: 'The Maya build this big temple', 'every
        king rule one city' — the cage forbade past tense and nothing said
        correctness was inviolable. And 'not information dense': nothing
        demanded facts. Both rules must survive whichever cage is built."""
        for opts in ({"complexity": "level"}, {"complexity": "stretch"},
                     {"complexity": "C1"}):
            prompt = _system_prompt("en", "en", {"level": "A1"}, opts)
            assert "never correctness" in prompt
            assert "Never bend agreement, tense, or word order" in prompt
            assert "carry real information" in prompt
            assert "encyclopedia entry" in prompt


class TestTheChecker:
    """Every generated text is graded against its contract, and a text
    that flunks gets exactly one retry with the verdict injected."""

    def _response(self, payload, tool="emit_reading"):
        class Block:
            type = "tool_use"
            def __init__(self, data):
                self.input = data
        class Resp:
            usage = None
            def __init__(self, data):
                self.content = [Block(data)]
        return Resp(payload)

    def _reading(self, title="ok"):
        return {
            "title": title,
            "sentences": [{"text": "Hola.", "translation": "Hi.",
                           "tokens": [{"text": "Hola.", "gloss": "hi"}]}],
            "new_words": [], "structures": [],
        }

    def _settings(self):
        class S:
            tutor_dev_mock = False
            anthropic_api_key = "sk-test"
            tutor_model = "model-big"
            tutor_summary_model = "model-small"
        return S()

    async def test_a_passing_text_is_served_first_try_with_its_verdict(self):
        from backend.services import reader as mod

        calls = []
        async def create(**kwargs):
            calls.append(kwargs)
            if kwargs["tools"][0]["name"] == "emit_check":
                return self._response({"level_ok": True, "length_ok": True,
                                       "voice_ok": True,
                                       "level_estimate": "B2"})
            return self._response(self._reading())

        with patch.object(mod, "get_settings", return_value=self._settings()), \
             patch.object(mod, "AsyncAnthropic") as client_cls:
            client_cls.return_value.messages.create = create
            reading, _ = await mod.generate_reading(
                "es", "cafés", {"level": "B1"},
                options={"complexity": "stretch"},
            )
        assert reading["check"]["level_ok"] is True
        gens = [c for c in calls if c["tools"][0]["name"] == "emit_reading"]
        assert len(gens) == 1
        # The grader was told the SHIFTED target, and ran on the cheap model.
        check = next(c for c in calls if c["tools"][0]["name"] == "emit_check")
        assert "B2" in check["messages"][0]["content"]
        assert check["model"] == "model-small"

    async def test_a_flunked_text_is_regenerated_once_with_the_verdict(self):
        from backend.services import reader as mod

        calls = []
        async def create(**kwargs):
            calls.append(kwargs)
            if kwargs["tools"][0]["name"] == "emit_check":
                return self._response({"level_ok": False, "length_ok": True,
                                       "voice_ok": True,
                                       "level_estimate": "A1",
                                       "note": "reads like A1, asked B2"})
            return self._response(self._reading())

        with patch.object(mod, "get_settings", return_value=self._settings()), \
             patch.object(mod, "AsyncAnthropic") as client_cls:
            client_cls.return_value.messages.create = create
            reading, _ = await mod.generate_reading(
                "es", "cafés", {"level": "B1"},
                options={"complexity": "stretch"},
            )
        gens = [c for c in calls if c["tools"][0]["name"] == "emit_reading"]
        assert len(gens) == 2
        assert "FAILED its contract check" in gens[1]["system"]
        assert "reads like A1" in gens[1]["system"]
        assert reading["check"]["retried"] is True

    def test_the_grader_must_judge_grammar_and_substance(self):
        # The Maya text PASSED the old checker: right level, right length,
        # broken English, empty sentences. Both axes are now required.
        from backend.services.reader import _CHECK_TOOL

        required = _CHECK_TOOL["input_schema"]["required"]
        assert "grammar_ok" in required
        assert "substance_ok" in required

    async def test_broken_grammar_alone_flunks_the_text(self):
        from backend.services import reader as mod

        calls = []
        async def create(**kwargs):
            calls.append(kwargs)
            if kwargs["tools"][0]["name"] == "emit_check":
                return self._response({
                    "level_ok": True, "length_ok": True, "voice_ok": True,
                    "grammar_ok": False, "substance_ok": True,
                    "level_estimate": "A1",
                    "note": "past events written in bare present",
                })
            return self._response(self._reading())

        with patch.object(mod, "get_settings", return_value=self._settings()), \
             patch.object(mod, "AsyncAnthropic") as client_cls:
            client_cls.return_value.messages.create = create
            reading, _ = await mod.generate_reading(
                "en", "the Maya", {"level": "A1"},
            )
        gens = [c for c in calls if c["tools"][0]["name"] == "emit_reading"]
        assert len(gens) == 2
        assert "past events written in bare present" in gens[1]["system"]
        assert reading["check"]["retried"] is True

    async def test_an_explicit_level_reaches_the_grader_contract(self):
        from backend.services import reader as mod

        calls = []
        async def create(**kwargs):
            calls.append(kwargs)
            if kwargs["tools"][0]["name"] == "emit_check":
                return self._response({
                    "level_ok": True, "length_ok": True, "voice_ok": True,
                    "grammar_ok": True, "substance_ok": True,
                    "level_estimate": "C1",
                })
            return self._response(self._reading())

        with patch.object(mod, "get_settings", return_value=self._settings()), \
             patch.object(mod, "AsyncAnthropic") as client_cls:
            client_cls.return_value.messages.create = create
            await mod.generate_reading(
                "es", "cafés", {"level": "A2"},
                options={"complexity": "C1"},
            )
        check = next(c for c in calls if c["tools"][0]["name"] == "emit_check")
        assert "pitched at C1" in check["messages"][0]["content"]

    async def test_a_broken_grader_never_blocks_the_reading(self):
        from backend.services import reader as mod

        async def create(**kwargs):
            if kwargs["tools"][0]["name"] == "emit_check":
                raise RuntimeError("grader down")
            return self._response(self._reading())

        with patch.object(mod, "get_settings", return_value=self._settings()), \
             patch.object(mod, "AsyncAnthropic") as client_cls:
            client_cls.return_value.messages.create = create
            reading, _ = await mod.generate_reading(
                "es", "cafés", {"level": "B1"},
            )
        assert reading["title"] == "ok"
        assert "check" not in reading
