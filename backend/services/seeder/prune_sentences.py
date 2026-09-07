"""Delete example sentences the committed bank no longer endorses.

**Why this exists.** `seed_sentences` inserts with `ON CONFLICT DO NOTHING`,
so it can only ever ADD. When a bank is curated down — the owner's 26 Aug
decision to thin English "to the best few per word, selected for variety" —
the rows that were cut stay in the database forever, and the review card
picks from everything present. English shipped 196,004 sentences against a
curated 70,975, so a learner opening the card for "I" was shown "I am.",
"I am you." and "I am!" while "I think he did it." sat unused in the file.

**What it will not do.**

* It never touches a row whose source is not `tatoeba` — UNLESS that row is
  one the exemption exists to protect nothing in: a sentence that is only
  the word it teaches (`_context_free`), or one below the five-token floor
  when the word keeps a longer survivor (`_below_floor`, CHECKS §24).
  `curated` and `ai` rows are otherwise human-authored or human-reviewed and
  are not reproducible from a file; the bulk corpus is.
* It never leaves a word with no example sentence. A word whose every row
  would be deleted keeps its rows and is reported instead.
* It matches on (word, SENTENCE) — never on the translation locale. The file
  keeps one row per sentence, the database holds that sentence once per
  locale, and a German learner needs the `de` translation of a sentence the
  file happens to store with its `es` one. Keying on locale would delete
  every other language's translation of a sentence the bank endorses.

**Reversibility.** Nothing is deleted until a rollback file exists on disk.
The rollback is plain SQL re-inserting every deleted row with its original
id, so learner-facing ids survive a round trip. The whole prune runs in one
transaction.

    python -m backend.services.seeder.prune_sentences -l en          # report
    python -m backend.services.seeder.prune_sentences -l en --apply  # writes
    python -m backend.services.seeder.prune_sentences --rollback out/prune-<stamp>.sql
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import os
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

import asyncpg

from backend.services.extract import find_cloze
from backend.services.linked_forms import forms_of
from backend.services.span_finders import span_finder

REPO = Path(__file__).resolve().parents[3]
DATA_DIR = REPO / "data"
ROLLBACK_DIR = REPO / "out"

# Only the bulk corpus is reproducible from a committed file. Everything else
# represents work a human did that no rebuild would bring back.
PRUNABLE_SOURCES = ("tatoeba",)

# The deletion floor, CHECKS §24 — the same number and the same tokenizer the
# FILE pass uses (`scripts/enforce_sentence_floor.py` imports both from here,
# so the two cannot drift). Thai writes without spaces, so counting tokens
# says nothing about how much sentence is there (§22).
FLOOR = 5
UNSPACED = {"th"}


def sentence_tokens(sentence: str) -> list[str]:
    r"""Letters-plus-marks words, so Devanagari and Arabic vowel signs stay
    attached to their letter — Python's ``\w`` drops them and turns नहीं
    into नह (quality rule 39)."""
    out: list[str] = []
    cur = ""
    for ch in sentence or "":
        if unicodedata.category(ch).startswith(("L", "M")) or (cur and ch in "'\u2019-"):
            cur += ch
        else:
            if cur:
                out.append(cur)
                cur = ""
    if cur:
        out.append(cur)
    return out


def _below_floor(sentence: str, code: str) -> bool:
    """True when the sentence is too thin to teach (CHECKS §24).

    Candidacy only — the caller's never-strand rule still refuses to empty a
    word, so a word whose every sentence is thin keeps them all.

    This exists because the source exemption was shielding exactly the rows
    the owner kept meeting. The English card for `human` served "You are
    human.", "I am human." and "She is human." — 48 rows, source `ai`, none
    of them in any committed bank — while the bank held "Every language that
    dies out takes a piece of human history with it." `_context_free` did not
    reach them: they are not BARE headwords, they are three-token frames. The
    file banks had this floor applied on 31 Aug; production never did, which
    is why pruning `ru` and `ar` left 2,822 and 3,123 thin protected rows
    behind. (Quality rule 42, second instance.)
    """
    if code in UNSPACED:
        return False
    return len(sentence_tokens(sentence)) < FLOOR


def shape_keeps(word: str, survivors: list, candidates: list, code: str) -> list:
    """Which of *candidates* must stay so that no SHAPE of *word* is stranded.

    A word with linked spellings (Turkish mi/mı/mu/mü — `alt` column →
    vocabulary.alternatives, CHECKS §30) is one card whose sentences each
    carry one shape, and the card exists to show the shape the sentence
    takes. So each shape keeps its best row even below the floor ("Var mı?"
    is a whole sentence; the particle's sentences are short by nature): for
    every shape no survivor carries, the longest candidate that carries it.
    Rows are dicts with a "sentence" key. Empty for an unlinked word.
    """
    forms = forms_of(word, code)
    if len(forms) < 2:
        return []
    finder = span_finder(code)

    def shape(r):
        found = find_cloze(r["sentence"], forms, finder)
        return found[1] if found else None

    covered = {shape(r) for r in survivors}
    keeps = []
    for form in forms:
        if form in covered:
            continue
        own = [r for r in candidates if shape(r) == form]
        if own:
            keeps.append(max(own, key=lambda r: len(sentence_tokens(r["sentence"]))))
    return keeps


def _context_free(sentence: str, word: str) -> bool:
    """True when the sentence is only the word it teaches, punctuation aside.

    CHECKS §21: such a row cannot show a learner how the word behaves, so it
    has no value to preserve — which is the ONLY reason `curated`/`ai` rows
    are otherwise exempt. Without this the protection rule shields junk: the
    Russian card for `да` kept "Да." and "Да!" as source='ai' through a full
    prune, sitting beside the real sentences that had just been authored for
    it. 221 such rows in ru+ar alone.

    Script-independent by construction — it compares the punctuation-stripped
    sentence to the headword rather than counting whitespace tokens, which is
    meaningless for Thai and misleading for Korean (CHECKS §22).
    """

    bare = "".join(
        c for c in (sentence or "")
        if not unicodedata.category(c).startswith("P")
    ).strip()
    return bare.casefold() == (word or "").strip().casefold()


def file_pairs(code: str) -> set[tuple[str, str]]:
    """(word, sentence) the committed bank endorses, lowercased on the word."""
    path = DATA_DIR / f"{code}_sentences.tsv"
    if not path.exists():
        return set()
    out: set[tuple[str, str]] = set()
    with open(path, encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            word = (row.get("word") or "").strip().lower()
            sentence = (row.get("sentence") or "").strip()
            if word and sentence:
                out.add((word, sentence))
    return out


async def survey(conn: asyncpg.Connection, code: str) -> dict:
    """What a prune of *code* would delete, and what it would refuse to."""
    keep = file_pairs(code)
    if not keep:
        return {"code": code, "skipped": "no committed bank", "delete": [],
                "protected": 0, "kept_empty": []}
    rows = await conn.fetch(
        """
        SELECT es.id, es.vocabulary_id, lower(v.word) AS word, es.sentence,
               es.translation, es.translation_locale, es.difficulty_rank,
               es.source, es.license, es.gloss, es.transliteration,
               es.reviewed, es.language_id
        FROM example_sentences es
        JOIN vocabulary v ON v.id = es.vocabulary_id
        JOIN languages l  ON l.id = v.language_id
        WHERE l.code = $1
        """,
        code,
    )
    exempt_rows = [r for r in rows if r["source"] not in PRUNABLE_SOURCES]
    # Group by word so the "never strand a word" rule can be applied per word.
    by_word: dict[str, list] = {}
    for r in rows:
        by_word.setdefault(r["word"], []).append(r)

    delete, kept_empty = [], []
    for word, group in by_word.items():
        # A context-free row is a candidate whatever its source: the exemption
        # exists to protect work a rebuild cannot reproduce, and there is
        # nothing there to protect.
        def _prunable(r):
            return (
                r["source"] in PRUNABLE_SOURCES
                or _context_free(r["sentence"], word)
                or _below_floor(r["sentence"], code)
            )

        survivors = [
            r for r in group
            if not _prunable(r) or (word, r["sentence"]) in keep
        ]
        candidates = [
            r for r in group
            if _prunable(r) and (word, r["sentence"]) not in keep
        ]
        if not candidates:
            continue
        if not survivors:
            # Deleting these would leave the word with nothing at all.
            kept_empty.append(word)
            continue
        # Never strand a SHAPE either (CHECKS §30) — same predicate as the
        # file-side floor script and its test.
        for r in shape_keeps(word, survivors, candidates, code):
            candidates.remove(r)
        delete.extend(candidates)
    # `protected` must mean "kept ONLY because of its source", so it counts
    # exempt rows that SURVIVE. Counting every exempt row overlapped `delete`
    # the moment thin rows lost the exemption (§24a), and the columns then
    # did not reconcile for a reader deciding whether to --apply.
    exempt_deleted = sum(1 for r in delete
                         if r["source"] not in PRUNABLE_SOURCES)
    protected = len(exempt_rows) - exempt_deleted
    return {"code": code, "skipped": None, "delete": delete,
            "protected": protected, "exempt_deleted": exempt_deleted,
            "kept_empty": kept_empty, "total": len(rows)}


def write_rollback(reports: list[dict], stamp: str) -> Path:
    """Every statement needed to put the rows back, ids included."""
    ROLLBACK_DIR.mkdir(exist_ok=True)
    path = ROLLBACK_DIR / f"prune-sentences-{stamp}.sql"
    lines = [
        "-- Rollback for backend.services.seeder.prune_sentences",
        f"-- generated {stamp}",
        '-- Replay with: psql "$DATABASE_URL" -f this-file',
        "BEGIN;",
    ]

    def lit(v) -> str:
        if v is None:
            return "NULL"
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, int | float):
            return str(v)
        return "'" + str(v).replace("'", "''") + "'"

    for rep in reports:
        for r in rep["delete"]:
            cols = ("id", "language_id", "vocabulary_id", "sentence",
                    "translation", "difficulty_rank", "source", "license",
                    "gloss", "transliteration", "reviewed", "translation_locale")
            vals = ", ".join(lit(r[c]) for c in cols)
            lines.append(
                f"INSERT INTO example_sentences ({', '.join(cols)}) "
                f"VALUES ({vals}) ON CONFLICT (id) DO NOTHING;"
            )
    lines.append("COMMIT;")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


async def apply(conn: asyncpg.Connection, reports: list[dict]) -> int:
    ids = [r["id"] for rep in reports for r in rep["delete"]]
    if not ids:
        return 0
    async with conn.transaction():
        for i in range(0, len(ids), 5000):
            await conn.execute(
                "DELETE FROM example_sentences WHERE id = ANY($1::uuid[])",
                ids[i:i + 5000],
            )
    return len(ids)


def print_report(reports: list[dict]) -> None:
    print(f"{'lang':<6}{'db':>9}{'delete':>9}{'thin':>8}"
          f"{'keeps':>8}{'protected':>11}{'stranded':>10}")
    print("-" * 61)
    tot_d = tot_p = tot_x = 0
    for rep in reports:
        if rep.get("skipped"):
            continue
        d = len(rep["delete"])
        x = rep.get("exempt_deleted", 0)
        tot_d += d
        tot_p += rep["protected"]
        tot_x += x
        print(f"{rep['code']:<6}{rep['total']:>9,}{d:>9,}{x:>8,}"
              f"{rep['total'] - d:>8,}{rep['protected']:>11,}"
              f"{len(rep['kept_empty']):>10,}")
    print("-" * 61)
    print(f"{'all':<6}{'':>9}{tot_d:>9,}{tot_x:>8,}{'':>8}{tot_p:>11,}")
    print("\ndelete    rows no committed bank endorses: the bulk corpus, plus")
    print("          any row that is only its headword or below the five-token")
    print("          floor whatever its source (CHECKS §18a, §24a)")
    print("thin      of those, the ones a curated/ai exemption used to shield")
    print("keeps     rows that remain")
    print("protected rows kept ONLY because they are curated or ai")
    print("stranded  words whose every row would go; left untouched instead")


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--language", "-l", default="all")
    ap.add_argument("--db-url", default=os.environ.get("DATABASE_URL"))
    ap.add_argument("--apply", action="store_true",
                    help="delete (a rollback file is written first)")
    ap.add_argument("--rollback", metavar="FILE", help="replay a rollback file and exit")
    args = ap.parse_args()
    if not args.db_url:
        print("ERROR: DATABASE_URL not set. Pass --db-url or set DATABASE_URL.")
        return
    conn = await asyncpg.connect(args.db_url)
    try:
        if args.rollback:
            await conn.execute(Path(args.rollback).read_text(encoding="utf-8"))
            print(f"rolled back from {args.rollback}")
            return
        if args.language == "all":
            codes = [p.name.split("_")[0]
                     for p in sorted(DATA_DIR.glob("*_sentences.tsv"))]
        else:
            codes = [args.language]
        reports = [await survey(conn, c) for c in codes]
        print_report(reports)
        if not args.apply:
            print("\nDRY RUN — nothing deleted. Re-run with --apply to write.")
            return
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        path = write_rollback(reports, stamp)
        print(f"\nrollback written first: {path}")
        n = await apply(conn, reports)
        print(f"deleted {n:,} example sentences")
        print(f"undo with: python -m backend.services.seeder.prune_sentences "
              f"--rollback {path}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
