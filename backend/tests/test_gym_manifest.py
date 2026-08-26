"""Gym manifest access (backend/services/gym_manifest.py)."""
from __future__ import annotations

from backend.services.gym_manifest import (
    load_manifest,
    nonstandard_point_titles,
)


def test_load_manifest_none_for_an_unknown_language():
    # A code with no manifest file has no Gym.
    assert load_manifest("zz") is None


def test_every_course_has_a_manifest():
    """This test used to assert `load_manifest("sw") is None` and called
    Swahili "uninflected" — a Bantu language with noun classes on every
    agreeing word and four slots inside the verb. It was standing in for "no
    manifest yet", and seven courses were in that state: sw, ha, yo, xh, mi,
    th and jam, 298 grammar points that could not be drilled by anyone.

    A point absent from its manifest is untrainable, so the Gym's real
    coverage is this, not the number of manifest files."""
    import json
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    codes = [p.stem for p in (repo / "data" / "gym").glob("*.json")]
    assert len(codes) == 27, f"only {len(codes)} courses have a Gym manifest"
    for code in codes:
        grammar = repo / "data" / "grammar" / f"{code}_grammar.json"
        if not grammar.exists():
            continue
        data = json.loads(grammar.read_text(encoding="utf-8"))
        points = data if isinstance(data, list) else (
            data.get("points") or data.get("grammar_points") or [])
        titles = {(p.get("title") or "").strip() for p in points}
        manifest = load_manifest(code)
        assert manifest, code
        named = {(e.get("point") or "").strip()
                 for col in manifest.get("columns") or []
                 for e in col.get("entries") or []}
        # every entry must name a REAL point: the title is matched literally,
        # so one character out is a dead row in the picker
        assert not (named - titles), f"{code}: {sorted(named - titles)[:3]}"


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
