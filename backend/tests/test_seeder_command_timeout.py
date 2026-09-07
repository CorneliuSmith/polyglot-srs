"""Every content tool's production connection has a bounded wait.

On 7 Sep 2026 `seed_grammar -l all` hung for two hours after "OK en": the
pooler had reset the server side of its session and asyncpg, with no
command timeout, waited for a reply that was never coming — 0% CPU, one
ESTABLISHED socket, nothing on the server. The operator could not tell it
from a slow run. A timeout makes it an error and a per-course rerun fixes
it. This test reads the source so the guard cannot be lost in a refactor.
"""
from __future__ import annotations

import inspect

import pytest

from backend.services.seeder import (
    base,
    prune_sentences,
    reconcile,
    seed_alphabet,
    seed_grammar,
    source_data,
)


@pytest.mark.parametrize("module", [base, seed_grammar, reconcile, prune_sentences,
                                    seed_alphabet, source_data])
def test_every_production_connect_has_a_command_timeout(module):
    src = inspect.getsource(module)
    connects = [line for line in src.splitlines() if "asyncpg.connect(" in line]
    assert connects, f"{module.__name__} no longer connects? update this test"
    for line in connects:
        assert "command_timeout=" in line, (
            f"{module.__name__}: {line.strip()} has no command_timeout — "
            "a stalled pooler would hang it for ever (7 Sep 2026)")


def test_the_timeout_is_generous_but_finite():
    assert 60 <= base.COMMAND_TIMEOUT <= 900
