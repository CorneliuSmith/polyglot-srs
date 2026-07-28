"""Gym manifest access (backend/services/gym_manifest.py)."""
from __future__ import annotations

from backend.services.gym_manifest import (
    load_manifest,
    nonstandard_point_titles,
)


def test_load_manifest_none_for_uninflected_language():
    # A language without a curated manifest has no Gym.
    assert load_manifest("sw") is None


def test_load_manifest_reads_columns():
    manifest = load_manifest("ru")
    assert manifest is not None
    assert manifest["language"] == "ru"
    assert manifest["columns"]


def test_nonstandard_titles_flags_pattern_breakers():
    titles = nonstandard_point_titles("ru")
    # Verbs of motion are marked non-standard in the Russian manifest.
    assert any("motion" in t.lower() for t in titles)
    # A plainly regular category is not flagged.
    assert "Past tense (-л)" not in titles


def test_nonstandard_titles_empty_without_manifest():
    assert nonstandard_point_titles("sw") == frozenset()


class TestManifestResolvesToRealCurriculum:
    """Every Gym cell points at a grammar point by TITLE. A title that no
    longer matches renders an empty cell with no error anywhere — the Gym
    just quietly offers nothing to drill. Cheap to check, invisible without
    a check."""

    def _codes(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        return sorted(p.stem for p in (root / "data" / "gym").glob("*.json"))

    def _titles(self, code):
        import json
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        path = root / "data" / "grammar" / f"{code}_grammar.json"
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        points = data["points"] if "points" in data else data
        return {p["title"] for p in points}

    def test_every_entry_resolves_to_a_grammar_point(self):
        problems = []
        for code in self._codes():
            titles = self._titles(code)
            if titles is None:
                continue  # manifest without a seeded curriculum file
            manifest = load_manifest(code)
            assert manifest is not None, code
            for column in manifest["columns"]:
                for entry in column["entries"]:
                    if entry["point"] not in titles:
                        problems.append(f"{code}: {entry['point']!r}")
        assert not problems, "Gym cells with no matching grammar point: " + "; ".join(problems)

    def test_labels_are_unique_within_a_language(self):
        """Two cells with the same label are indistinguishable to a learner."""
        for code in self._codes():
            manifest = load_manifest(code)
            labels = [
                e["label"] for c in manifest["columns"] for e in c["entries"]
            ]
            assert len(labels) == len(set(labels)), f"{code}: duplicate cell labels"


def test_portuguese_gym_drills_the_future_subjunctive():
    """Reported by the owner. Portuguese is the one Romance language where
    the future subjunctive is an everyday form (quando eu chegar, se você
    quiser) — Spanish's is archaic, French and Italian have none — so the
    Gym drilling the present and imperfect subjunctive but not this one was
    an omission, not an editorial choice.

    The personal infinitive rides along: it is identical to the future
    subjunctive for regular verbs and diverges for irregulars, which is
    exactly the confusion a conjugation gym exists to drill out.
    """
    manifest = load_manifest("pt")
    points = {e["point"] for c in manifest["columns"] for e in c["entries"]}
    assert any(p.startswith("Futuro do subjuntivo") for p in points)
    assert any(p.startswith("Infinitivo pessoal") for p in points)
