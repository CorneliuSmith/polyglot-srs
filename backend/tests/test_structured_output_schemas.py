"""Every structured-output schema must be valid for the API's strict rules.

The recommendations feature never produced a single batch in production:
its schema omitted `additionalProperties: false`, which the API REQUIRES
on every object node, so the very first model call answered 400 — for
weeks, invisibly, until the draft error finally surfaced on the page.
Three more schemas (vocab leveling, the sentence-harvest checker, the
tutor's memory summarizer) shipped with the same defect.

This walks every schema the codebase sends via output_config and pins the
invariant, so the next new schema fails HERE instead of in production.
Free-form maps (`additionalProperties: {"type": ...}`) are rejected too —
the API refuses them; use an array of {key, value} pairs.
"""
from __future__ import annotations

import importlib

import pytest

SCHEMAS = [
    ("backend.services.writing_baseline", "_SCHEMA"),
    ("backend.services.tutor", "_SUMMARY_SCHEMA"),
    ("backend.services.seeder.generate_curriculum", "_CURRICULUM_SCHEMA"),
    ("backend.services.seeder.generate_grammar", "_CONTENT_SCHEMA"),
    ("backend.services.seeder.harvest_sentences", "CHECKER_SCHEMA"),
    ("backend.services.define", "_MAKER_SCHEMA"),
    ("backend.services.define", "_CHECKER_SCHEMA"),
    ("backend.services.recommend", "_RECO_SCHEMA"),
    ("backend.services.semantic_check", "_SCHEMA"),
    ("backend.services.level_estimate", "_SCHEMA"),
    ("backend.services.translate", "_MAKER_SCHEMA"),
    ("backend.services.translate", "_CHECKER_SCHEMA"),
    ("backend.services.translate", "_SENTENCE_MAKER_SCHEMA"),
    ("backend.services.translate", "_TRIVIA_SCHEMA"),
    ("backend.services.generate", "_DRILL_SCHEMA"),
    ("backend.services.generate", "_EXAMPLE_SCHEMA"),
    ("backend.services.generate", "_AUDIT_SCHEMA"),
    ("backend.services.generate", "_DRILL_AUDIT_SCHEMA"),
    ("backend.services.generate", "_CHART_SCHEMA"),
    ("backend.services.generate", "_OVERLAP_SCHEMA"),
]


def _lax_object_nodes(node, path="$"):
    """Paths of object nodes that would make the API reject the schema."""
    bad = []
    if isinstance(node, dict):
        if node.get("type") == "object" and node.get("additionalProperties") is not False:
            bad.append(path)
        for key, value in node.items():
            bad += _lax_object_nodes(value, f"{path}.{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            bad += _lax_object_nodes(value, f"{path}[{i}]")
    return bad


def _optional_properties(node, path="$"):
    """Object nodes whose `required` doesn't cover every property.

    The second strict-mode rule, and the one that kept recommendations
    broken after the first was fixed: an optional key is rejected outright.
    Express "may be absent" as "may be an empty string" instead.
    """
    bad = []
    if isinstance(node, dict):
        if node.get("type") == "object" and "properties" in node:
            missing = set(node["properties"]) - set(node.get("required") or [])
            if missing:
                bad.append((path, sorted(missing)))
        for key, value in node.items():
            bad += _optional_properties(value, f"{path}.{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            bad += _optional_properties(value, f"{path}[{i}]")
    return bad


@pytest.mark.parametrize("module,name", SCHEMAS, ids=[f"{m}.{n}" for m, n in SCHEMAS])
def test_every_object_node_forbids_extra_properties(module, name):
    schema = getattr(importlib.import_module(module), name)
    assert _lax_object_nodes(schema) == [], (
        f"{module}.{name} has object nodes without additionalProperties: "
        f"false — the API 400s the whole call before the model runs"
    )


@pytest.mark.parametrize("module,name", SCHEMAS, ids=[f"{m}.{n}" for m, n in SCHEMAS])
def test_every_property_is_required(module, name):
    schema = getattr(importlib.import_module(module), name)
    assert _optional_properties(schema) == [], (
        f"{module}.{name} leaves properties optional — strict structured "
        f"output rejects that; make them required and allow an empty string"
    )
