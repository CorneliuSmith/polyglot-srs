# Brief for a video-capable model: how each letter is written by hand

The provisional stroke library is the centreline of a typeface with rules
guessed around it (`docs/plans/letterform-quality.md`). A typeface cannot
say how many strokes a letter has, in what order, or which parts are one
movement — only a teaching source can. This is the brief that gets those
rules out of a model with video access, in a shape the generator can read.

## How to run it

- **Paste the prompt below once.** It carries all ten runs and tells the
  model to do one per message and stop; say "next" between them. Ten runs,
  because ten scripts and styles in one message produces shallow work and
  blows the context.
- **Give it sources if you have them.** Link two to four teaching videos
  yourself; otherwise let it find them, but the source field is not
  optional and a row without one is to be dropped.
- The runs are ordered by how cheaply the answer can be checked: Latin
  print first (it settles the `f` the owner found), Hangul last (its
  order is standardised and least in doubt).
- **Send the output back as `.jsonl` files**, not pasted prose.

---

## The prompt — one paste, ten runs

Copy everything between the rules. It carries all ten runs; the model does
one per message.

---

**HANDWRITING REFERENCE — COMPILATION JOB**

You are compiling a handwriting reference for an app that teaches adults to write a script by hand. Your output is **data**, not prose: a program reads it.

**HOW TO WORK.** There are ten runs, listed at the end. Do **one run per message**, in the order given. Finish a run, then stop and wait for me to say "next". Never attempt two scripts in one message. If a run is too large to finish, do as many letters as you can, end with the summary line, and tell me which letters remain.

**THE TASK.** For every letter in the run, in every form listed, state how a native writer forms it **by hand**: how many separate strokes, in what order, where each stroke begins and ends, and which parts of the letter are one continuous movement of the pen.

**SOURCES — THIS IS THE PART THAT MATTERS.**
- Use **teaching sources**: school handwriting lessons, literacy or primary-school channels, national curriculum primers, letter-formation worksheets from education ministries or schoolbooks.
- **Do not use calligraphy** (a nib does things a learner must not copy), decorative lettering, font specimens, typography articles, or other AI-generated content.
- Prefer sources in the language itself, aimed at children learning to write or at foreign adults learning the script.
- **Every row carries its source**: a URL, plus a timestamp if it is a video. A row with no source is worthless to me — omit it instead.
- Where you watched a video, report what you saw the hand do, not what you believe about the script.

**JUDGEMENT RULES.**
- Describe the **standard taught model**, not a personal or adult shorthand style.
- If sources disagree, give the most commonly taught version, set `"confidence": "medium"`, and describe the disagreement in `"disagreement"`.
- **Never guess.** If you cannot find a source for a letter, leave it out of the rows and list it under `unknown` in the summary. A missing row is fine; an invented one is not.
- **Marks are separate strokes.** Dots, bars, diacritics, the Arabic nuqta, the Russian й breve, the i-dot, every accent: say explicitly whether each is written immediately after its own letter's body, or after the whole word is finished.
- **For cursive**, say where the letter is entered from, where it is left, and whether the pen lifts before the next letter.
- If two forms of a letter are written identically, still emit a row for each form.

**OUTPUT FORMAT.** One JSON object per line (JSONL). No markdown fences, no commentary before or after, no trailing commas.

```
{"script": "<as given>", "style": "<as given>", "glyph": "<the letter>",
 "form": "<one of the forms given>",
 "strokes": [
   {"from": "<zone>", "to": "<zone>", "path": "<what the pen does>",
    "note": "<optional: merges, splits, lifts, when a mark is added>"}
 ],
 "pen_lifts": <integer, strokes minus 1>,
 "source": "<url, with timestamp for video>",
 "confidence": "high" | "medium" | "low",
 "disagreement": "<optional>"}
```

`from` and `to` must each be exactly one of: `top`, `top-left`, `top-right`, `left`, `right`, `centre`, `bottom`, `bottom-left`, `bottom-right`, `baseline-left`, `baseline-right`. Nothing else.

`path` is one short phrase written as an instruction to a learner — "straight down", "across, left to right", "round anticlockwise, closing the loop", "hook, then straight down without lifting". It is shown beside the stroke, so it must match what that stroke does.

**A good row:**

```
{"script":"latin","style":"print","glyph":"f","form":"lower","strokes":[{"from":"top-right","to":"bottom","path":"curve left over the top, then straight down","note":"the hook and the stem are ONE movement — the pen does not lift"},{"from":"left","to":"right","path":"straight across the stem","note":"the crossbar, written last"}],"pen_lifts":1,"source":"https://youtu.be/… 2:41","confidence":"high"}
```

**A bad row**, rejected: "the letter f is written with a hook and a bar" — no zones, no order, no source, and it does not say the hook and stem are one movement.

**End every run** with one final line:

```
{"summary": {"run": <n>, "rows": <n>, "unknown": ["<letter/form>", …], "unsettled": ["<question I asked that no source answered>", …], "sources": ["<url>", …]}}
```

---

## What happens to a run once you paste it

Each run is ingested, measured and acted on the same way, so the runs can
arrive in any order and none of it is hand work:

1. `python3 scripts/strokes/ingest_rules.py <paste>` merges the rows into
   `scripts/strokes/rules/{script}-{style}.jsonl`. It renames `letter` to
   `glyph`, unwraps the Google-redirect sources, files an uppercase row
   under its lowercase glyph, drops any row with no source or no strokes,
   and reports what it dropped. It is idempotent: pasting the same run
   twice changes nothing.

   It refuses one thing rather than guessing. A row that would overwrite
   an existing one **from a different source** is held back and named,
   because that is how the table silently lost a letter once: the Turkish
   row for "I" is the capital of *dotless* ı — Turkish pairs i-İ and ı-I,
   everyone else i-I — and filing it under i/upper replaced the row for
   the letter every other Latin course writes. Pass `--force` only after
   deciding the new row really is about the same letter.

2. `python3 scripts/strokes/check_rules.py <script> <style>` measures the
   generated library against the table on three things: how many strokes,
   where the first one starts, and where it ends. The end column exists
   because a broken f had the taught count *and* the taught start and was
   still wrong.

3. The disagreements are the work list, and they are read as claims about
   the generator, not as errors to paper over. The f's row said the hook
   and the stem are one movement; the generator was splitting them; the
   fix was in the generator.

## What run 1 got wrong — paste this before run 2

Run 1 came back usable but off-schema in four ways, every one of them
already stated above. The model does not reread the brief between runs, so
paste this correction at the top of the next run's message. It is written
to be sent as-is.

> Four corrections before you continue, all of them in the brief you already
> have:
>
> 1. The key is `glyph`, not `letter`. I have to rename every row by hand.
> 2. `pen_lifts` is required on every row, and it is strokes minus one.
>    You omitted it entirely.
> 3. **Sources.** You gave about fifty rows one generic marketing URL for a
>    worksheet publisher, and wrapped several in a Google redirect with a
>    tracking parameter. A URL that does not show the letter being written
>    is not a source. Give me the page or the video that shows *that letter*,
>    with a timestamp if it is a video, unwrapped. If you cannot find one,
>    leave the row out and put the letter in `unknown` — I mean that, and a
>    short `unknown` list is a better run than a long one with invented
>    sources.
> 4. End with the `{"summary": {...}}` object the brief specifies, not
>    `{"run_complete": ...}`. I need `unsettled` and `sources`.

Two things run 1 got *right* and should keep doing: splitting a run across
messages when it is too long (say which letters remain), and putting the
African Latin letters — `ɓ ɗ ƙ ƴ ẹ ọ ṣ` and their capitals — in `unknown`
rather than inventing them. That result is a finding, not a failure: no
teaching source for them surfaced, and the cursive face we render from has
no glyph for five of them either, so those letters need a human who writes
Hausa or Yoruba, not another run.

---

**THE RUNS**

**Run 1 — script `latin`, style `print`.** Forms: `lower`, `upper`.
Letters: a–z (52 rows), **plus** the extra letters these courses use, lower and upper:
Spanish `ñ á é í ó ú ü` · French `à â ç é è ê ë î ï ô ù û ü ÿ œ æ` · Italian `à è é ì ò ó ù` · Portuguese `ã õ á â é ê í ó ô ú ç à` · Catalan `à è é í ï ò ó ú ü ç` · German `ä ö ü ß` · Romanian `ă â î ș ț` · Turkish `ç ğ ı İ ö ş ü` · Māori `ā ē ī ō ū` · Dutch `é ë ï` · Hausa `ɓ ɗ ƙ ƴ` · Yoruba `ẹ ọ ṣ`.
Questions: Is `f` one stroke (hook and stem together) plus the crossbar, or three? Is `a` one stroke or two, and `d`, and `g`? Is `t` stem then crossbar, and is a crossbar always left to right? Is `k` two strokes or three? **When is a diacritic written — immediately after its own letter, or after the whole word, like the i-dot? Does that differ by country or school model?** Which accented letters are simply the base letter plus a mark (so the base strokes are unchanged), and which need full rows because the shape itself differs — `ß`, `ı` and `İ`, `ø`, `æ`, `œ`, `ɓ ɗ ƙ ƴ`? Are uppercase accents written at all by hand (French often drops them)?

**Run 2 — script `latin`, style `cursive`.** Forms: `lower`, `upper`. Same letters as run 1.
Questions: Which school model are you describing — D'Nealian, Zaner-Bloser, Palmer, or a national model? Name it. Where does each letter start and end on the line, for joining? Which letters do **not** join to the letter after them? Where do the accents go in a joined hand — after the word?

**Run 3 — script `cyrillic`, style `cursive`.** Forms: `lower`, `upper`. 66 rows.
Letters: а б в г д е ж з и й к л м н о п р с т у ф х ц ч ш щ ъ ы ь э ю я ё
Questions: Which letters begin with an entry hook from the baseline rather than at the top? Is `т` written with a bar above it and `ш` with one below, and when is that bar added? Are the dots of `ё` and the breve of `й` written after the letter or after the word? Where does the pen lift in `щ` and `ц` — before the tail, or not at all? Do `л м я` keep their leading upstroke when they begin a word?

**Run 4 — script `cyrillic`, style `print`.** Forms: `lower`, `upper`. 66 rows. Same letters.
Questions: Which letters differ in stroke order from their cursive form? Is the bar of `т` part of the same stroke as the stem?

**Run 5 — script `greek`, style `print`.** Forms: `lower`, `upper`. 48 rows.
Letters: α β γ δ ε ζ η θ ι κ λ μ ν ξ ο π ρ σ τ υ φ χ ψ ω
Questions: Which lowercase letters are written differently from their printed shape — `θ`, `ζ`, `ξ`, `β`, `σ`? Is `θ` one stroke or two? Is the handwritten `ξ` one continuous stroke?

**Run 6 — script `arabic`, style `naskh`.** Forms: `isolated` and `final` for every letter; also `initial` and `medial` for every letter that joins on its left (all but ا د ذ ر ز و and آ). 124 rows.
Letters: آ ا ب ت ث ج ح خ د ذ ر ز س ش ص ض ط ظ ع غ ف ق ك ل م ن ه و ي پ چ ژ ک گ ی
Questions: Is `ص`/`ض` one continuous stroke, or a loop and then a bowl? In `ل` and `ك`, is the upright written before or after the base? Are the dots of `ب ت ث ن ي` added after each letter or after the whole word? Is the hamza of `أ` and `إ` written with the alif or added afterwards? When `ا` is joined to the previous letter, does it run **upward** from the join? Are `ط` and `ظ` written bowl first then the upright, or the reverse?

**Run 7 — script `devanagari`, style `print`.** Form: `letter`. 43 rows.
Letters: अ आ इ ई उ ऊ ए ऐ ओ औ क ख ग घ ङ च छ ज झ ञ ट ठ ड ढ ण त थ द ध न प फ ब भ म य र ल व श ष स ह
Questions: Is the shirorekha (headline) drawn per letter, or across the whole word at the end? Which letters have a vertical stem written before the body, and which after? Where do the vowel signs ि ी े ो come in the order?

**Run 8 — script `thai`, style `print`.** Form: `letter`. 44 rows.
Letters: ก ข ฃ ค ฅ ฆ ง จ ฉ ช ซ ฌ ญ ฎ ฏ ฐ ฑ ฒ ณ ด ต ถ ท ธ น บ ป ผ ฝ พ ฟ ภ ม ย ร ล ว ศ ษ ส ห ฬ อ ฮ
Questions: Does every consonant start at its head (the small loop), and is the loop clockwise or anticlockwise? Which letters have no loop to start from — ก, ญ, ธ — and where do those start? Where do tone marks and vowels come in the order?

**Run 9 — script `hebrew`, style `print`.** Form: `letter`. 27 rows.
Letters: א ב ג ד ה ו ז ח ט י ך כ ל ם מ ן נ ס ע ף פ ץ צ ק ר ש ת
Questions: Which letters are written in one stroke and which in two or three? Is the top horizontal always drawn first, and always right to left? Do the final forms ך ם ן ף ץ differ in stroke order from their base letters?

**Run 10 — script `hangul`, style `print`.** Form: `letter`. 40 rows.
Letters: ㄱ ㄲ ㄴ ㄷ ㄸ ㄹ ㅁ ㅂ ㅃ ㅅ ㅆ ㅇ ㅈ ㅉ ㅊ ㅋ ㅌ ㅍ ㅎ ㅏ ㅐ ㅑ ㅒ ㅓ ㅔ ㅕ ㅖ ㅗ ㅘ ㅙ ㅚ ㅛ ㅜ ㅝ ㅞ ㅟ ㅠ ㅡ ㅢ ㅣ
Questions: Confirm the standard stroke order for each jamo (top to bottom, left to right). For `ㄹ` and `ㅂ`, how many strokes and in what order?

---

**Start with run 1 now.**


---

## Before the Latin runs land: the library is a–z

`alphabet_for()` gives every Latin-script course exactly the 26 base
letters (`backend/services/scripts.py`; DEBT, "A Latin-script course's
stroke library is a–z only"). So ñ é ß ğ ı ş have **no row to attach a
rule to**, no Learn step, no Trace, and a word containing one cannot be
composed — it reports the letter missing. A per-language extras table in
`scripts.py` is the fix and is half a day; the rules and the table can be
built in either order, but neither is useful alone.

## What happens to the output

Send the `.jsonl` files back to Claude Code. They become
`scripts/strokes/rules/{script}-{style}.jsonl`, read by the generator as
a per-letter rules table (`docs/plans/letterform-quality.md`, Tier 1): a
row sets the start point, forces a split or a merge, and replaces the
hint text. A letter with no row keeps the rule-derived behaviour, so the
table can be filled one script at a time and never has to be complete.
