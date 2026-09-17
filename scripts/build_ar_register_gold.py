#!/usr/bin/env python3
"""Build the Arabic register gold set that reviewers label.

`docs/quality/ar-register-programme.md` §3.2 and §5 step 1 specify the set:
200 sentences (100 the tripwire flagged, 100 random), 100 vocabulary entries
(the 50 rarest-sense glosses plus 50 random), all 274 drills and all 40
explanations. Reviewers fill `label`, `variety`, `evidence` and `note` using
§1 and the §6 checklist; the judge is then run on the same items and the two
are compared (§3.2 gate). Regenerating must reproduce the file byte for byte,
so every sample is seeded and every sort is total.

Three things this script had to decide, each recorded because the obvious
choice was wrong:

**"The tripwire flagged" cannot mean the shipped tripwire.** The shipped
`ARABIC_DIALECT_MARKERS` (29 whole words) flags **zero** rows in the current
13,025-row bank, and the widened §1.1 list flags 22 — not the 100 the gold
set needs, and not the 424 word hits §2 of the programme records, which were
measured on the 14,671-row bank before the prune. So the flagged half is
drawn by a deliberately RECALL-oriented net (`_candidates`): the §1.1 tells
as whole words, the same tells wearing a proclitic (و ف ب ل ال), and the
three morphology patterns §1.2 names. It flags 1,710 rows at a precision the
programme already measured as poor — which is the point. A gold set exists to
show where the judge draws its line, so it must contain the hard negatives,
not only the easy positives.

**The b-prefix rows are the most valuable rows in the set.** §1.2 records
that every one of the 1,212 prefix matches in the bank was بـ + noun
(بالسيارة, بنفسك, بالنسبة) and not a b-imperfect verb. A judge that files
those as dialect fails the §3.2 gate on precision, and nothing else in the
corpus tests that. They are sampled as their own stratum rather than being
allowed to crowd the set out.

**"Rarest-sense" is not English-gloss rarity — that was measured and it
fails.** The defect §2 describes is a dialect word the corpus counted,
glossed with its rare MSA homograph's meaning: مش "to suck the marrow",
وين "black grape", مو "baldmoney", يلا "come on". Scoring the *English*
gloss for rarity looks like the way to find them and is not: against
`data/en_frequency.tsv` the four land at positions 5,916 / 6,859 / 1,555 /
6,702 by rarest content word, and no better by mean rarity or by the
fraction of unlisted words. "Suck", "marrow", "bone", "black" and "grape"
are all ordinary English; what is rare is the *sense*, which no English
frequency list knows about. Worse, the metric inverts: the commonest Arabic
words have the longest glosses, those glosses carry grammatical
metalanguage ("partitive", "enclitic") that the list does not contain, and
so ranks 1, 3, 4 and 5 came out as the "rarest senses" in the corpus.

What actually identifies the class is the **headword**: the entry is a §1.1
dialect tell that the frequency count treated as a word. Eleven entries
qualify, and they are the stratum — including the four the programme names
and, deliberately, the homographs that are genuinely MSA and must NOT be
retired (عم "from what?", كمان "violin", دول "to internationalize", زين "to
adorn"). Eleven items where the reviewer has to decide one against the
other is worth more than fifty the metric was never able to find. The
remaining thirty-nine are filled by gloss rarity, which does find the
"baldmoney" shape even though it cannot find the sense.

    python -m scripts.build_ar_register_gold            # writes the TSV
    python -m scripts.build_ar_register_gold --check    # verify it is current
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"
OUT = DATA / "eval" / "ar_register_gold.tsv"

sys.path.insert(0, str(REPO))

from backend.services.quality.audit_content import _arabic_bare_tokens  # noqa: E402

SEED = 20260916

COLUMNS = [
    "id", "store", "field", "text", "translation",
    "label", "variety", "evidence", "note", "stratum",
]
# `stratum` is the one column the programme's §6 shape does not list. It is
# machine-written and never a reviewer field: it records WHY an item is in the
# set, which is what makes the agreement figures readable per category and
# what lets a later run prove the sample was not quietly reshaped. The nine
# reviewer columns are exactly §6's, and four of them ship blank.
REVIEWER_BLANK = ("label", "variety", "evidence", "note")

# Every tell in programme §1.1, all four varieties, plus the spelling variants
# the shipped tripwire carries. Whole words only — the tokeniser bares the
# marks so المحلّفين cannot read as المحل + فين.
TELLS = set("""
عايز عاوز مش فين ايه إيه ازاي إزاي ازيك إزيك دلوقتي كده كدا علشان عشان ده دي دول
بتاع برضو لسه أوي يلا بكرة ماشي خلاص بدي بدك شو ليش وين هيك هاد هاي هدول منيح كتير
هلق لسا عم كمان معلش كيفك حكي شلون وش وشو شنو ماكو أكو مو الحين توه زين عيل هسه دحين
واش بزاف غادي كاين علاش دابا انتا
""".split())

# Programme §1.1 "Not tells": verified in this corpus as MSA words that the
# lists above collide with. A row whose only evidence is one of these is a
# hard negative, and the set keeps them on purpose.
NOT_TELLS = set("هو عم عمال دول بدون شكرا تمام مين كمان زي الحين الموظفين خلص".split())

# The three register defects `docs/quality/ar.md` records as confirmed. They
# are pinned into the set rather than left to the sampler: §3.2's recall gate
# is "every labelled dialect row caught", and a gold set that can miss the
# only verified positives cannot measure it. بكرة is deliberately NOT one of
# them on its own — "بكرة القدم" is football, so the same string is both the
# Egyptian "tomorrow" and an ordinary MSA noun phrase, and both shapes are in
# the set.
KNOWN_DEFECT_SUBSTRINGS = ("وانتا", "خطاب بكرة")

PROCLITICS = ("وال", "فال", "بال", "لل", "و", "ف", "ب", "ل", "ال")

# §1.2's morphology tells. Applied to the BARED token string, so tashkeel
# cannot hide a prefix and cannot invent one.
MORPHOLOGY = {
    "b_imperfect": re.compile(r"(?<!\w)(?:بي|بت|بن|با)[ء-ي]{2,}"),
    "ha_future": re.compile(r"(?<!\w)(?:هي|هت|هن|حي|حت|حن)[ء-ي]{2,}"),
    "sh_negation": re.compile(r"(?<!\w)ما[ء-ي]{2,}ش(?!\w)"),
}

_CONTENT_STOP = set("""
a an the of to and or in on at for with from by as is are was were be been being
that this these those it its his her their our your my no not any some one two
第 or etc eg ie also very more most such than then there here who whom which what
""".split())
_EN_WORD = re.compile(r"[a-z]+")


def _read_tsv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _sid(word: str, sentence: str) -> str:
    """A sentence's id: content-addressed, so reordering the bank cannot
    silently repoint a label at a different sentence."""
    digest = hashlib.sha1(f"{word}\t{sentence}".encode()).hexdigest()
    return f"ar-sent-{digest[:12]}"


def _candidates(rows: list[dict]) -> dict[int, list[str]]:
    """Row index -> the strata it belongs to, for every row the net flags."""
    found: dict[int, list[str]] = {}
    for i, row in enumerate(rows):
        tokens = _arabic_bare_tokens(row.get("sentence") or "")
        tokset = set(tokens)
        why: list[str] = []
        whole = sorted(tokset & TELLS)
        if whole:
            why.append("hard_negative" if set(whole) <= NOT_TELLS else "whole_word")
        for token in tokens:
            if token in TELLS:
                continue
            if any(token.startswith(p) and token[len(p):] in TELLS
                   and len(token[len(p):]) >= 2 for p in PROCLITICS):
                why.append("proclitic")
                break
        bared = " ".join(tokens)
        for name, pattern in MORPHOLOGY.items():
            if pattern.search(bared):
                why.append(name)
        if why:
            found[i] = why
    return found


def _rarity(gloss: str, en_rank: dict[str, int], floor: int) -> float:
    """How rare an English gloss reads, as the mean rank of its content words.

    Long glosses are scored 0: a long gloss belongs to a common Arabic word
    and its rare-looking words are grammatical metalanguage, not a rare
    sense. See the module docstring for what this does and does not find."""
    words = [w for w in _EN_WORD.findall((gloss or "").lower())
             if len(w) > 2 and w not in _CONTENT_STOP]
    if not words or len(words) > 6:
        return 0.0
    return sum(en_rank.get(w, floor) for w in words) / len(words)


def _sample(pool: list, n: int, rng: random.Random) -> list:
    """A seeded sample that is stable under a reordering of *pool*."""
    if len(pool) <= n:
        return list(pool)
    return rng.sample(pool, n)


def build() -> list[dict]:
    rng = random.Random(SEED)
    out: list[dict] = []

    # ---- sentences -------------------------------------------------------
    sentences = _read_tsv(DATA / "ar_sentences.tsv")
    flagged = _candidates(sentences)
    # Strata in priority order: the scarce, high-signal rows are taken whole;
    # the two big morphology strata are sampled to fill the rest. Ordering the
    # buckets by scarcity is what keeps 1,145 b-prefix rows from swallowing
    # the 22 whole-word ones.
    order = ["whole_word", "sh_negation", "proclitic", "hard_negative",
             "ha_future", "b_imperfect"]
    # A row can trip several patterns at once. It belongs to the SCARCEST one
    # it trips, not the alphabetically first: bucketing by `sorted(why)[0]`
    # filed 17 of the 22 whole-word hits under b_imperfect, because a dialect
    # sentence usually also contains a بـ word, and the rarest stratum in the
    # set all but vanished.
    rank_of = {name: n for n, name in enumerate(order)}
    buckets: dict[str, list[int]] = {}
    for i, why in flagged.items():
        buckets.setdefault(min(why, key=lambda w: rank_of[w]), []).append(i)
    quota = {"whole_word": 100, "sh_negation": 100, "proclitic": 20,
             "hard_negative": 20, "ha_future": 15, "b_imperfect": 25}
    picked: list[tuple[int, str]] = []
    pinned = sorted(
        i for i, row in enumerate(sentences)
        if any(s in (row.get("sentence") or "") for s in KNOWN_DEFECT_SUBSTRINGS)
    )
    picked.extend((i, "known_defect") for i in pinned)
    for name in order:
        pool = [i for i in sorted(buckets.get(name, [])) if i not in set(pinned)]
        take = _sample(pool, min(quota[name], 100 - len(picked)), rng)
        picked.extend((i, name) for i in sorted(take))
        if len(picked) >= 100:
            break
    # Top up to 100 from whatever the quotas left behind, scarcest first, so
    # the flagged half is the size §3.2 specifies whenever the net can fill it.
    if len(picked) < 100:
        taken = {i for i, _ in picked}
        for name in order:
            spare = [i for i in sorted(buckets.get(name, [])) if i not in taken]
            take = _sample(spare, min(len(spare), 100 - len(picked)), rng)
            picked.extend((i, name) for i in sorted(take))
            taken.update(take)
            if len(picked) >= 100:
                break
    flagged_ids = {i for i, _ in picked}
    for i, stratum in sorted(picked):
        row = sentences[i]
        out.append({
            "id": _sid(row["word"], row["sentence"]), "store": "sentences",
            "field": "sentence", "text": row["sentence"],
            "translation": row.get("translation") or "", "stratum": stratum,
        })
    rest = [i for i in range(len(sentences)) if i not in flagged_ids]
    for i in sorted(_sample(rest, 100, rng)):
        row = sentences[i]
        out.append({
            "id": _sid(row["word"], row["sentence"]), "store": "sentences",
            "field": "sentence", "text": row["sentence"],
            "translation": row.get("translation") or "", "stratum": "random",
        })

    # ---- vocabulary ------------------------------------------------------
    freq = _read_tsv(DATA / "ar_frequency.tsv")
    en_rows = _read_tsv(DATA / "en_frequency.tsv")
    en_rank = {}
    for r in en_rows:
        w = (r.get("word") or "").strip().lower()
        try:
            rank = int(r.get("rank") or 0)
        except ValueError:
            continue
        if w and w not in en_rank:
            en_rank[w] = rank
    floor = max(en_rank.values(), default=0) + 1
    tells = sorted((r for r in freq if r["word"] in TELLS),
                   key=lambda r: int(r["rank"]))
    taken_ranks = {r["rank"] for r in tells}
    scored = sorted(
        ((_rarity(r.get("en") or "", en_rank, floor), int(r["rank"]), r)
         for r in freq if r["rank"] not in taken_ranks),
        key=lambda t: (-t[0], t[1]),
    )
    fill = [r for _, _, r in scored[:50 - len(tells)]]
    for r in tells:
        out.append({
            "id": f"ar-vocab-{r['rank']}", "store": "vocab", "field": "gloss",
            "text": r["word"], "translation": r.get("en") or "",
            "stratum": "dialect_headword",
        })
    for r in fill:
        out.append({
            "id": f"ar-vocab-{r['rank']}", "store": "vocab", "field": "gloss",
            "text": r["word"], "translation": r.get("en") or "",
            "stratum": "rarest_sense",
        })
    rarest_ranks = taken_ranks | {r["rank"] for r in fill}
    pool = [r for r in freq if r["rank"] not in rarest_ranks]
    for r in sorted(_sample(pool, 50, rng), key=lambda x: int(x["rank"])):
        out.append({
            "id": f"ar-vocab-{r['rank']}", "store": "vocab", "field": "gloss",
            "text": r["word"], "translation": r.get("en") or "",
            "stratum": "random",
        })

    # ---- grammar: every drill and every explanation ----------------------
    parsed = json.loads((DATA / "grammar" / "ar_grammar.json").read_text(encoding="utf-8"))
    points = parsed["points"] if isinstance(parsed, dict) else parsed
    for p_i, point in enumerate(points):
        for d_i, drill in enumerate(point.get("drills") or []):
            out.append({
                "id": f"ar-drill-{p_i}-{d_i}", "store": "grammar", "field": "drill",
                "text": (drill.get("sentence") or "").replace("\n", " "),
                "translation": (drill.get("translation") or "").replace("\n", " "),
                "stratum": f"point:{point.get('title', '?')}",
            })
    for p_i, point in enumerate(points):
        text = (point.get("explanation") or "").strip()
        if not text:
            continue
        out.append({
            "id": f"ar-expl-{p_i}", "store": "grammar", "field": "explanation",
            "text": text.replace("\n", " "), "translation": "",
            "stratum": f"point:{point.get('title', '?')}",
        })

    for item in out:
        for column in REVIEWER_BLANK:
            item.setdefault(column, "")
    return out


# The MSA homographs of §1.1's "Not tells", as frequency ENTRIES. The
# headword is a dialect tell; the gloss is the genuine MSA word that shares
# its spelling, so the entry is correct and must NOT be retired. Keeping them
# beside the four that must be is what makes the stratum a test rather than a
# list of answers.
_MSA_HOMOGRAPH_ENTRIES = {"عم", "كمان", "دول", "زين", "خلاص", "أوي", "بكرة"}
_DIALECT_ENTRIES = {"مش", "وين", "مو", "يلا"}

DOCUMENTED = DATA / "eval" / "ar_register_documented.tsv"
DOCUMENTED_COLUMNS = ["id", "expected", "why"]


def documented(items: list[dict]) -> list[dict]:
    """The subset of the gold set whose answer the programme already states.

    Reviewers have not labelled anything yet, and a judge graded only against
    another model's opinion is self-certification (quality rule §6, rule 30).
    These rows are different: the answer is asserted in
    `docs/quality/ar-register-programme.md` or `docs/quality/ar.md`, verified
    in this corpus by whoever wrote it, and it is a fact about the row rather
    than a judgement about Arabic. They are the part of calibration that does
    not depend on an opinion, and they are labelled `why` so a reviewer who
    disagrees can argue with the document instead of with a number."""
    rows = []
    for item in items:
        stratum, text = item["stratum"], item["text"]
        if stratum == "known_defect":
            rows.append({"id": item["id"], "expected": "dialect",
                         "why": "ar.md records this row as a confirmed register defect"})
        elif stratum == "hard_negative":
            rows.append({"id": item["id"], "expected": "msa",
                         "why": "programme 1.1 non-tell: the only marker is an MSA word"})
        elif stratum == "b_imperfect":
            rows.append({"id": item["id"], "expected": "msa",
                         "why": "programme 1.2: every b-prefix match in the bank is ba + noun"})
        elif stratum == "dialect_headword" and text in _DIALECT_ENTRIES:
            rows.append({"id": item["id"], "expected": "dialect",
                         "why": "programme 2: dialect entry glossed as its rare MSA homograph"})
        elif stratum == "dialect_headword" and text in _MSA_HOMOGRAPH_ENTRIES:
            rows.append({"id": item["id"], "expected": "msa",
                         "why": "programme 1.1 non-tell: the gloss is the genuine MSA homograph"})
    return rows


def render_documented(rows: list[dict]) -> str:
    out = ["\t".join(DOCUMENTED_COLUMNS)]
    for r in rows:
        out.append("\t".join(str(r[c]).replace("\t", " ") for c in DOCUMENTED_COLUMNS))
    return "\n".join(out) + "\n"


def render(items: list[dict]) -> str:
    buf = []
    buf.append("\t".join(COLUMNS))
    for item in items:
        buf.append("\t".join(str(item.get(c, "")).replace("\t", " ") for c in COLUMNS))
    return "\n".join(buf) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="fail if the committed file is not what this script builds")
    args = ap.parse_args()
    items = build()
    blob = render(items)
    doc_rows = documented(items)
    doc_blob = render_documented(doc_rows)
    if args.check:
        for path, want in ((OUT, blob), (DOCUMENTED, doc_blob)):
            current = path.read_text(encoding="utf-8") if path.exists() else ""
            if current != want:
                print(f"STALE: {path.relative_to(REPO)} is not what this script builds.")
                return 1
        print(f"OK: {OUT.relative_to(REPO)} is current ({len(items)} items); "
              f"{DOCUMENTED.name} has {len(doc_rows)} documented answers.")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(blob, encoding="utf-8")
    DOCUMENTED.write_text(doc_blob, encoding="utf-8")
    by_store: dict[str, int] = {}
    by_stratum: dict[str, int] = {}
    for item in items:
        by_store[item["store"]] = by_store.get(item["store"], 0) + 1
        key = item["stratum"].split(":")[0]
        by_stratum[key] = by_stratum.get(key, 0) + 1
    print(f"{OUT.relative_to(REPO)}: {len(items)} items")
    for k, v in sorted(by_store.items()):
        print(f"   store {k:10s} {v}")
    for k, v in sorted(by_stratum.items(), key=lambda t: -t[1]):
        print(f"   stratum {k:16s} {v}")
    expected: dict[str, int] = {}
    for r in doc_rows:
        expected[r["expected"]] = expected.get(r["expected"], 0) + 1
    print(f"{DOCUMENTED.relative_to(REPO)}: {len(doc_rows)} answers the docs "
          f"already state — {expected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
