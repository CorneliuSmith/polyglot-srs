#!/usr/bin/env python3
"""Gate authored example sentences and write them into the committed banks.

Every rule here is one this programme got wrong first (quality-rules 38-41).

**Rank.** A new row is written with `difficulty_rank` = the word's FREQUENCY
rank, which is the convention the corpus already follows. An earlier pass
appended `max + 1` instead; a card draws by `difficulty_rank`, so 2,743
authored sentences sorted last and were never shown — the owner's `мне` card
kept displaying the fragments they had been written to replace.

**Presence.** Verified per language, by real morphology where one exists:
pymorphy3 lemmatises Russian, so парня -> парень and семью -> семья are
confirmed rather than guessed. Arabic has no analyser here and its morphology
is non-concatenative (كان -> كنت, أراد -> يريد), so presence there rests on
the checker pass and is REPORTED as such rather than silently assumed.

**Tokens.** Letters plus marks, never `\\w`, which drops Mn/Mc and turns
नहीं into नह.

**Rejects.** The script prints a sample of what it refuses, because on this
programme a rejection count has been a claim about the matcher more often
than about the content.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"
MIN_WORDS, MAX_WORDS = 7, 14
MORPH_LANGS = {"ru"}


def tokens(sentence: str) -> list[str]:
    out: list[str] = []
    cur = ""
    for ch in sentence or "":
        if unicodedata.category(ch).startswith(("L", "M")) or (cur and ch in "'’-"):
            cur += ch
        else:
            if cur:
                out.append(cur)
                cur = ""
    if cur:
        out.append(cur)
    return out


def fold(text: str) -> str:
    text = unicodedata.normalize("NFD", (text or "").casefold())
    text = "".join(c for c in text if not unicodedata.category(c).startswith("M"))
    return text.replace("ё", "е")


def _ru_present(word: str, sentence: str, morph) -> bool:
    target = fold(word)
    toks = tokens(sentence)
    if target in {fold(t) for t in toks}:
        return True
    return target in {fold(p.normal_form) for t in toks for p in morph.parse(t)[:3]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("results", nargs="+", help="workflow task .output or journal.jsonl")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--attribute-from", metavar="JSON",
        help="work list {code: [{w,...}]} used to assign a course to records "
             "that carry none. A workflow's AUTHOR stage returns bare "
             "{words:[...]}; the course code is added by the second stage, so "
             "a run that crashes in post-processing leaves records with no "
             "code at all. Three did. Without this the work is unattributable "
             "and gets thrown away.")
    args = ap.parse_args()

    owner: dict[str, str] = {}
    if args.attribute_from:
        work = json.loads(Path(args.attribute_from).read_text(encoding="utf-8"))
        counts: dict[str, set] = defaultdict(set)
        for code, items in work.items():
            for it in items:
                counts[it["w"]].add(code)
        owner = {w: next(iter(c)) for w, c in counts.items() if len(c) == 1}

    supplied: dict[str, dict[str, list]] = defaultdict(dict)
    for path in args.results:
        text = Path(path).read_text(encoding="utf-8")
        if path.endswith(".jsonl"):
            blobs = []
            for line in text.splitlines():
                if not line.strip():
                    continue
                rec = json.loads(line)
                if rec.get("type") == "result" and isinstance(rec.get("result"), dict):
                    blobs.append(rec["result"])
        else:
            whole = json.loads(text)
            blobs = [whole.get("result", whole)]
        for b in blobs:
            # Two shapes reach this. A workflow that finished returns
            # {code: {word: [sentences]}}. A workflow that CRASHED in its
            # post-processing leaves per-agent records in the journal shaped
            # {code, words:[{w, sentences}], fixes:[...]} — three runs died
            # that way on a template bug, with every agent's work intact, so
            # reading only the finished shape would have thrown it away.
            if isinstance(b.get("words"), list) or isinstance(b.get("fixes"), list):
                code = b.get("code")
                if not code and owner:
                    # infer from the work list: whichever course asked for
                    # these words. Unanimity required — a word claimed by two
                    # courses is dropped rather than guessed.
                    claims = {owner.get(w["w"]) for w in (b.get("words") or [])}
                    claims.discard(None)
                    code = claims.pop() if len(claims) == 1 else None
                if code:
                    for w in b.get("words") or []:
                        supplied[code][w["w"]] = w["sentences"]
                    for x in b.get("fixes") or []:      # checker wins
                        supplied[code][x["w"]] = x["sentences"]
                continue
            for code, words in b.items():
                if isinstance(words, dict):
                    supplied[code].update(words)

    morph = None
    if any(c in MORPH_LANGS for c in supplied):
        import pymorphy3

        morph = pymorphy3.MorphAnalyzer()

    for code, words in sorted(supplied.items()):
        path = DATA / f"{code}_sentences.tsv"
        freq_path = DATA / f"{code}_frequency.tsv"
        if not path.exists():
            continue
        with open(freq_path, encoding="utf-8-sig", newline="") as fh:
            rank = {(r.get("word") or "").strip(): i
                    for i, r in enumerate(csv.DictReader(fh, delimiter="\t"))}
        raw = path.read_bytes()
        crlf = b"\r\n" in raw
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")), delimiter="\t")
        cols = reader.fieldnames
        rows = list(reader)
        existing = {(r.get("sentence") or "").strip() for r in rows}

        accepted: list[tuple[str, dict]] = []
        rejected: dict[str, list] = defaultdict(list)
        for word, sents in words.items():
            seen, frames = set(), set()
            for s in sents or []:
                sentence = (s.get("sentence") or "").strip()
                translation = (s.get("translation") or "").strip()
                if not (sentence and translation):
                    rejected["incomplete"].append((word, sentence))
                    continue
                n = len(tokens(sentence))
                if not (MIN_WORDS <= n <= MAX_WORDS):
                    rejected[f"outside {MIN_WORDS}-{MAX_WORDS} words"].append((word, sentence))
                    continue
                if sentence in existing or sentence in seen:
                    rejected["duplicate"].append((word, sentence))
                    continue
                if code in MORPH_LANGS and not _ru_present(word, sentence, morph):
                    rejected["target word absent"].append((word, sentence))
                    continue
                frame = tuple(fold(t) for t in tokens(sentence)[:3])
                if frame in frames:
                    rejected["same frame as a sibling"].append((word, sentence))
                    continue
                frames.add(frame)
                seen.add(sentence)
                accepted.append((word, {"sentence": sentence, "translation": translation}))

        verified = "mechanically (pymorphy3)" if code in MORPH_LANGS else "by the checker pass only"
        print(f"{code}: {len(accepted):,} accepted for {len({w for w, _ in accepted}):,} words "
              f"— word presence verified {verified}")
        for why, items in sorted(rejected.items(), key=lambda kv: -len(kv[1])):
            print(f"   rejected {len(items):>4}  {why}")
            for w, s in items[:2]:
                print(f"        {w!r}: {s[:60]}")
        if args.dry_run or not accepted:
            continue

        out = io.StringIO(newline="")
        writer = csv.DictWriter(out, fieldnames=cols, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
        for word, s in accepted:
            row = dict.fromkeys(cols, "")
            # THE RANK RULE: the word's frequency rank, never max+1 — see the
            # module docstring. A row that sorts last is a row nobody reads.
            row.update({k: v for k, v in (
                ("word", word), ("sentence", s["sentence"]),
                ("translation", s["translation"]),
                ("difficulty_rank", str(rank.get(word, 9999))),
            ) if k in cols})
            writer.writerow(row)
        data = out.getvalue()
        if crlf:
            data = data.replace("\n", "\r\n")
        path.write_text(data, encoding="utf-8", newline="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
