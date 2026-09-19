# Second brief: Latin print, counted by pen lifts

## Why there is a second brief

The owner looked at the app's lowercase **d** and said it should be two
strokes. The library draws one. The library is right about its source and
wrong about the reader:

```
d lower, latin print
  taught: 1 stroke — "curve around left to close, push straight up to the
          top, then straight down to the baseline"
  source: zaner-bloser.com
  the model's own note: "Taught as one continuous stroke in modern US
          curricula to prevent b/d reversal."
```

The first run answered the question it was asked — *how does a native
writer form this letter* — and modern US print curricula genuinely teach
`a b d g h m n p q r` as one unbroken movement that **retraces** back up a
line it has already drawn. That is a real teaching model with a real
reason behind it (b/d reversal in five-year-olds).

It is the wrong model for this app twice over:

1. **Our reader is an adult learning a foreign script**, not a child being
   taught to avoid mirror-writing in their own. The reversal argument does
   not apply and the retrace is not worth teaching.
2. **The screen cannot show a retrace.** One stroke is drawn as one path,
   so the stem is traced up and then down again in a single animation. It
   reads as neither one stroke nor two — which is exactly what the owner
   saw.

So this run asks the same alphabet a different question: **how many times
does the pen leave the paper.**

The `a` row from the first run already recorded the disagreement, unasked:
*"Some older models teach circle and stem separately."* Those are the
models this run wants.

## What to do with the answer

Send it back as `.jsonl`. It replaces the Latin print rows from
zaner-bloser.com, which is a cross-source replacement, so it is ingested
with:

```bash
python3 scripts/strokes/ingest_rules.py <file>.jsonl --force
```

`--force` exists for exactly this and prints every row it replaces, with
both sources named. The old rows are in git if the decision is ever
revisited.

## Also settles the one gap in the tables

659 letters across ten tables have a sourced rule. The only hole is **56
accented Latin print letters** — the second part of the very first run was
lost before it reached disk and was never re-requested. This run asks for
them too, so the hole closes in the same pass.

---

## The prompt — one paste, three runs

Copy everything between the rules.

---

**HANDWRITING REFERENCE — LATIN PRINT, COUNTED BY PEN LIFTS**

You are compiling a handwriting reference for an app that teaches **adults** to write a script by hand. Your output is **data**, not prose: a program reads it.

**HOW TO WORK.** There are three runs, listed at the end. Do **one run per message**, in the order given. Finish a run, then stop and wait for me to say "next".

**THE TASK — AND HOW IT DIFFERS FROM THE USUAL ONE.** For every letter listed, state how it is formed by hand, counted **by pen lifts**: a new stroke begins every time the pen leaves the paper.

**WHO THIS IS FOR, AND WHY IT CHANGES THE ANSWER.** The reader is an adult who already writes fluently in another script and is learning this one. They are not a child learning to write for the first time. That distinction decides this whole job, because the dominant US print curricula teach the continuous, retraced forms of `a b d g h m n p q r` for a reason that is specific to children: it prevents b/d mirror-reversal in five- and six-year-olds writing their own language. An adult learning Latin script as a foreigner has no such problem, gains nothing from the retrace, and is actively confused by it — the app animates one stroke as one continuous path, so a retraced letter draws its stem twice in a single sweep. **So when a source's reasoning is about young children's motor learning or reversal errors, say so in `disagreement` and give me the lifted form instead.** When a source's reasoning is about the shape of the letter itself, follow it.

**A RETRACE IS A LIFT, FOR THIS JOB.** Many US print curricula teach `a b d g h m n p q r` as one unbroken movement in which the pen runs back up a line it has already drawn — "curve around, push up, then straight down". Count that as **two strokes**, split at the moment the pen doubles back. The reason is practical: the app animates each stroke as one path, so a retraced movement draws the same line twice and teaches nothing. If a source teaches a letter as continuous *without* doubling back — a genuine corner, like the down-and-across of uppercase L, or a closed ring like `o` — that stays **one** stroke. Corners are not lifts. Only retraces are.

**PREFER SOURCES THAT ALREADY TEACH LIFTED FORMS.** Handwriting Without Tears, UK models (Nelson, Letter-join), Australian Foundation, New Zealand, Irish and Canadian primary models, and older US models all teach separate circle-and-stem forms. Use them in preference to Zaner-Bloser and D'Nealian, which are the continuous ones. Where you use a continuous source anyway, split the retrace yourself and say so in `note`.

**ONE HOUSE RULE, AND IT OVERRIDES THE SOURCES.** For lowercase **d**, the stem is written **first**, then the bowl. Report it that way whatever your sources say, and put the sources' own order in `disagreement` so the departure is on the record.

**SOURCES — THIS IS THE PART THAT MATTERS.**
- Use **teaching sources**: school handwriting lessons, national curriculum primers, letter-formation worksheets from education ministries or schoolbooks.
- **Do not use calligraphy**, decorative lettering, font specimens, typography articles, or other AI-generated content.
- **Every row carries its source**: a URL, plus a timestamp if it is a video. A row with no source is worthless — omit it instead.
- **Never guess.** A missing row is fine; an invented one is not. List anything you could not source under `unknown` in the summary line.

**JUDGEMENT RULES.**
- Describe a **standard taught model** — a form some curriculum actually teaches — not someone's personal shorthand or a fast adult scrawl. "Written for adults" changes *which* taught model I want, not whether it is a taught model at all.
- If sources disagree, give the most commonly taught version, set `"confidence": "medium"`, and describe the disagreement in `"disagreement"`.
- **Marks are separate strokes.** The i-dot, every accent, the Turkish ğ breve, the macron: each is its own stroke, and say whether it is written immediately after the letter's body or after the whole word.
- Emit a row for **both** `lower` and `upper` of every letter, even when they are written identically.

**OUTPUT FORMAT.** One JSON object per line (JSONL). No markdown fences, no commentary before or after, no trailing commas.

```
{"script": "latin", "style": "print", "glyph": "<the lowercase letter>",
 "form": "lower" | "upper",
 "strokes": [
   {"from": "<zone>", "to": "<zone>", "path": "<what the pen does>",
    "note": "<optional: where you split a retrace, when a mark is added>"}
 ],
 "pen_lifts": <integer, strokes minus 1>,
 "source": "<url, with timestamp for video>",
 "confidence": "high" | "medium" | "low",
 "disagreement": "<optional>"}
```

`from` and `to` must each be exactly one of: `top`, `top-left`, `top-right`, `left`, `right`, `centre`, `bottom`, `bottom-left`, `bottom-right`, `baseline-left`, `baseline-right`. Nothing else.

`glyph` is always the **lowercase** letter; `form` says which case the row describes. So uppercase B is `{"glyph": "b", "form": "upper"}`.

End every message with one summary line:

```
{"run_complete": true, "rows": <n>, "unknown": ["<letters you could not source>"]}
```

**THE THREE RUNS**

1. **a–z, both cases.** 52 rows. This is the run that matters most: it replaces the current table.
2. **The accented letters, both cases.** á à â ä ã å ç é è ê ë í ì î ï ñ ó ò ô ö õ ú ù û ü ý ÿ æ œ ß ā ē ī ō ū ă ș ț ğ ı ş ẹ ọ — and for each, say whether the mark is written straight after the letter's body or after the whole word. `ß` is lowercase only.
3. **Anything from runs 1 and 2 you had to leave out**, with whatever sources you found on a second attempt, plus your reading of which letters in this alphabet are most contested between teaching models.

---

## What happens to a run once you paste it

`ingest_rules.py` normalises it, strips the Google-redirect wrappers off
the sources, files uppercase rows under the lowercase glyph, drops any row
with no source or no strokes, and refuses a row that would overwrite one
from a different source unless `--force` says to. Then
`gen_from_fonts.py` reads the table and splits, merges, reorders and
flips each letter's strokes to match it, and
`backend/tests/test_strokes.py::TestAgainstTheSourcedRules` scores every
letter against it on every CI run.
