#!/usr/bin/env python3
"""Drop example sentences too thin to teach, where the word has better ones.

CHECKS §23 sets the AUTHORING bar at 7-14 words. This is the weaker
DELETION bar, and the two are deliberately different: authoring to 7-14 is
what we aim for, while a five-word corpus sentence is often perfectly good
and there is no reason to destroy it.

What gets dropped is a sentence under FIVE tokens **for a word that already
has a longer one**. The owner's card for `мне` is the case: it showed
"Это мне?", "Это не мне." and "Это мне." — three near-identical fragments —
while three authored sentences of ten and eleven words sat unseen behind
them, because a card draws by difficulty_rank and appended rows sort last.
Deleting the fragments is what makes the good ones visible; re-ranking would
have worked too, but leaving three useless rows in place to be shuffled is
not the better outcome.

Never strands a word: if everything it has is under five tokens, it all
stays until something better is authored.

Thai is skipped entirely (§22) — it writes without spaces, so counting
whitespace tokens says nothing about how much sentence is there.
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

DATA = REPO / "data"

# The floor, the tokenizer and the unspaced-script exemption live with the
# PRODUCTION prune, and this pass imports them: the file bank and the database
# must be thinned by the same rule or one of them drifts (they did — the files
# got this floor on 31 Aug and production did not until CHECKS §24a).
from backend.services.seeder.prune_sentences import (  # noqa: E402
    FLOOR,
    UNSPACED,
    shape_keeps,
)
from backend.services.seeder.prune_sentences import (  # noqa: E402
    sentence_tokens as tokens,
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    total_dropped = total_words = total_stranded = 0
    for path in sorted(DATA.glob("*_sentences.tsv")):
        code = path.name.split("_")[0]
        if code in UNSPACED:
            continue
        raw = path.read_bytes()
        crlf = b"\r\n" in raw
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")), delimiter="\t")
        cols = reader.fieldnames
        rows = list(reader)
        by_word = defaultdict(list)
        for r in rows:
            by_word[(r.get("word") or "").strip()].append(r)

        drop: set[int] = set()
        improved = stranded = 0
        for _word, group in by_word.items():
            thin = [r for r in group if len(tokens(r.get("sentence") or "")) < FLOOR]
            if not thin:
                continue
            if len(thin) == len(group):
                stranded += 1          # nothing better exists; leave it alone
                continue
            # A linked spelling keeps its best row (Turkish harmony, §30).
            full = [r for r in group if r not in thin]
            kept = shape_keeps(_word, full, thin, code)
            for r in thin:
                if not any(r is k for k in kept):
                    drop.add(id(r))
            improved += 1
        total_dropped += len(drop)
        total_words += improved
        total_stranded += stranded
        if not drop:
            continue
        print(f"  {code}: -{len(drop):,} thin sentences, {improved:,} words improved, "
              f"{stranded:,} left alone")
        if args.dry_run:
            continue
        keep = [r for r in rows if id(r) not in drop]
        out = io.StringIO(newline="")
        writer = csv.DictWriter(out, fieldnames=cols, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for r in keep:
            writer.writerow(r)
        data = out.getvalue()
        if crlf:
            data = data.replace("\n", "\r\n")
        path.write_text(data, encoding="utf-8", newline="")

    print(f"\ntotal: {total_dropped:,} dropped, {total_words:,} words improved, "
          f"{total_stranded:,} words left alone (nothing better yet)")
    if args.dry_run:
        print("DRY RUN — nothing written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
