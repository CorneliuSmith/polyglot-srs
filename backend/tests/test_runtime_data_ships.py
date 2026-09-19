"""Every data file the API reads at runtime must be in the deployed image.

The failure this guards against does not look like a failure. `.dockerignore`
excludes `data/*` — deliberately, because the seed corpora are 8 GB and the
content lives in Supabase. But two things under `data/` are read from DISK by
the running API, and when they are excluded the code does not crash:

  * the Gym manifests — excluded once, and every language's Gym showed the
    "no forms to train" empty state;
  * `data/<code>_frequency.tsv` — `NLPBackend._collision_surfaces()` catches
    `OSError` and returns an empty set, which turns the collision guard OFF.
    `el` typed for `él` went back to grading CORRECT_SLOPPY in production
    while all 37 tests in test_nlp_collisions.py passed locally, because
    locally the file exists.

That is the whole problem: a test suite that reads the repo cannot see what
the image is missing. This test reads `.dockerignore` instead.
"""
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

# (path the runtime reads, what stops working when it is absent)
RUNTIME_DATA = [
    ("data/gym/es.json", "Gym manifests — every language shows 'no forms to train'"),
    ("data/es_frequency.tsv", "the collision guard degrades silently to off"),
    ("data/ru_frequency.tsv", "the collision guard degrades silently to off"),
    # The whole Thai romanisation layer is one lookup table — the reading is
    # looked up from it at request time and the segmenter is a longest-match
    # walk over the same file. Absent, `th` readings are empty and nothing
    # errors, which is indistinguishable from the layer never being built.
    ("data/th_readings.tsv", "every Thai reading is silently empty"),
    ("data/ar_readings.tsv", "every Arabic reading is silently empty"),
    ("data/he_readings.tsv", "every Hebrew reading is silently empty"),
    ("data/fa_readings.tsv", "every Persian reading is silently empty"),
    # The nightly judge's gate: which (question, course) pairs may be sent
    # to a model. `content_judge.calibrated_pairs()` reads an absent file as
    # EMPTY on purpose — a bad file must switch the judge off, never on — so
    # with the admin switch on, the judge listed every pair "not
    # calibrated", sent nothing, and every coverage row said calibrated:
    # false. Nothing errored; the panel showed a judge that never read.
    (
        "data/eval/calibrated.json",
        "the nightly judge silently judges nothing and every coverage row says calibrated: false",
    ),
    # The corpus the nightly quality loop audits IN PRODUCTION. Absent, the
    # audit does not fail — it finds nothing, which reads as a clean bill of
    # health. Measured 19 Sep 2026 against the live database: 10,395 rows
    # written, every drill rule 0, `unclozable_rows` 0, and the Content Health
    # panel showing 100% top-band coverage for all 27 courses (CHECKS §44).
    ("data/grammar/es_grammar.json",
     "every drill rule reads 0 and the panel calls all 27 courses clean"),
    ("data/grammar/ru_grammar.json",
     "every drill rule reads 0 and the panel calls all 27 courses clean"),
    ("data/es_sentences.tsv",
     "unclozable_rows reads 0 and top-band coverage reports 100% for every course"),
    ("data/ru_sentences.tsv",
     "unclozable_rows reads 0 and top-band coverage reports 100% for every course"),
    # The audit grades the definitions production SERVES, which is the
    # frequency column with these laid over it. Without the file it grades
    # text nobody is shown, and every gloss rule reports a number for a corpus
    # that does not exist.
    ("data/gloss_overrides.tsv",
     "every gloss rule grades the raw frequency column instead of what ships"),
    # The baseline the fail-level rules are scored against, and the panel's
    # audit-delta column.
    ("data/quality/baseline.json",
     "the audit has nothing to score against and the panel's delta is null"),
    # The schema-drift diagnostic derives its expectations FROM these files.
    # With none in the image it has nothing to expect, so /api/health/schema
    # answers `ok: true` against any database at all — including one that
    # is three migrations behind and 500ing on every endpoint that reads
    # them. That is how "the health check says fine" and "readiness 500s"
    # were both true of the same deploy.
    (
        "supabase/migrations/20261012000000_show_glosses.sql",
        "/api/health/schema reports ok:true unconditionally — the diagnostic is blind",
    ),
]


def _dockerignore_rules():
    text = (REPO / ".dockerignore").read_text(encoding="utf-8")
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _excluded(path: str, rules: list[str]) -> bool:
    """Last matching rule wins, as Docker does it."""
    verdict = False
    for rule in rules:
        negated = rule.startswith("!")
        pattern = rule[1:] if negated else rule
        regex = "^" + re.escape(pattern).replace(r"\*", "[^/]*") + "(/.*)?$"
        if re.match(regex, path):
            verdict = not negated
    return verdict


@pytest.mark.parametrize("path,consequence", RUNTIME_DATA)
def test_runtime_data_is_not_dockerignored(path, consequence):
    assert (REPO / path).exists(), f"{path} is missing from the repo entirely"
    assert not _excluded(path, _dockerignore_rules()), (
        f"{path} is excluded from the Docker image, so at runtime {consequence}. "
        "Add a `!` negation to .dockerignore AND a COPY line to the Dockerfile — "
        "the negation alone does nothing without the COPY."
    )


@pytest.mark.parametrize("path,_", RUNTIME_DATA)
def test_runtime_data_is_copied_by_the_dockerfile(path, _):
    """A `!` negation in .dockerignore only makes a path COPYABLE. Without a
    matching COPY the file still never reaches the image — which is exactly
    how data/gym shipped empty the first time."""
    dockerfile = (REPO / "Dockerfile").read_text(encoding="utf-8")
    copied = [
        line.split()[1]
        for line in dockerfile.splitlines()
        if line.startswith("COPY ") and len(line.split()) >= 3
    ]
    covered = any(
        re.match("^" + re.escape(src).replace(r"\*", "[^/]*") + "(/.*)?$", path)
        for src in copied
    )
    assert covered, (
        f"nothing in the Dockerfile COPYs {path}. Add one, or the file is "
        "absent from the image however .dockerignore is written."
    )
