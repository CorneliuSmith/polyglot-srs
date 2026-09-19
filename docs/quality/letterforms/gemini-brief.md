# Brief for a video-capable model: how each letter is written by hand

The provisional stroke library is the centreline of a typeface with rules
guessed around it (`docs/plans/letterform-quality.md`). A typeface cannot
say how many strokes a letter has, in what order, or which parts are one
movement — only a teaching source can. This is the brief that gets those
rules out of a model with video access, in a shape the generator can read.

## How to run it

- **One script per conversation.** Eight scripts in one run produces
  shallow work and blows the context. Nine runs total (Arabic, Cyrillic
  cursive, Cyrillic print, Greek, Latin print, Latin cursive, Devanagari,
  Thai, Hebrew, Hangul).
- **Give it sources.** Link two to four teaching videos yourself if you
  have them; otherwise let it find them, but the source field is not
  optional.
- Replace `{{SCRIPT}}`, `{{STYLE}}`, `{{FORMS}}`, `{{LETTERS}}` and
  `{{COUNT}}` from the table at the bottom, and `{{QUESTIONS}}` with that
  script's open questions.
- **Send the output back as a `.jsonl` file**, not pasted prose.

---

## The prompt

> You are compiling a handwriting reference for an app that teaches adults
> to write a script by hand. Your output is **data**, not prose, and it
> will be read by a program.
>
> **The task.** For every letter listed below, in every form listed, state
> how a native writer forms it **by hand**: how many separate strokes, in
> what order, where each stroke begins and ends, and which parts of the
> letter are one continuous movement of the pen.
>
> **Sources — this is the part that matters.**
> - Use **teaching sources**: school handwriting lessons, literacy or
>   primary-school channels, national curriculum primers, letter-formation
>   worksheets from education ministries or schoolbooks.
> - **Do not use calligraphy** (a nib does things a learner must not
>   copy), decorative lettering, font specimens, typography articles, or
>   other AI-generated content.
> - Prefer sources in the language itself, aimed at children learning to
>   write or at foreign adults learning the script.
> - **Every row carries its source**: a URL, plus a timestamp if it is a
>   video. A row with no source is worthless to me — omit it instead.
> - Where you watched a video, say what you actually saw the hand do, not
>   what you believe about the script.
>
> **Judgement rules.**
> - Describe the **standard taught model**, not a personal or adult
>   shorthand style.
> - If sources disagree, give the most commonly taught version, set
>   `"confidence": "medium"`, and describe the disagreement in
>   `"disagreement"`.
> - **Never guess.** If you cannot find a source for a letter, leave it
>   out of the rows and list it in the final `unknown` object. A missing
>   row is fine; an invented one is not.
> - **Marks are separate strokes.** Dots, bars, diacritics, the Arabic
>   nuqta, the Russian й breve, the i-dot: say explicitly whether they are
>   written immediately after that letter's body or after the whole word.
> - **For cursive**, say where the letter is entered from and where it is
>   left, and whether the pen lifts before the next letter.
> - **For a letter whose forms are written identically**, still emit a row
>   for each form.
>
> **Output format.** One JSON object per line (JSONL). No markdown fences,
> no commentary before or after, no trailing commas. Schema:
>
> ```
> {"script": "<as given>", "style": "<as given>", "glyph": "<the letter>",
>  "form": "<one of the forms given>",
>  "strokes": [
>    {"from": "<zone>", "to": "<zone>", "path": "<what the pen does>",
>     "note": "<optional: merges, splits, lifts, when a mark is added>"}
>  ],
>  "pen_lifts": <integer, strokes minus 1>,
>  "source": "<url, with timestamp for video>",
>  "confidence": "high" | "medium" | "low",
>  "disagreement": "<optional>"}
> ```
>
> `from` and `to` must each be one of exactly these zones — nothing else:
> `top`, `top-left`, `top-right`, `left`, `right`, `centre`, `bottom`,
> `bottom-left`, `bottom-right`, `baseline-left`, `baseline-right`.
>
> `path` is one short phrase, written as an instruction to a learner —
> "straight down", "across, left to right", "round anticlockwise, closing
> the loop", "hook, then straight down without lifting". It becomes the
> text shown beside the stroke, so it must match what the stroke does.
>
> **A good row:**
>
> ```
> {"script":"latin","style":"print","glyph":"f","form":"lower","strokes":[{"from":"top-right","to":"bottom","path":"curve left over the top, then straight down","note":"the hook and the stem are ONE movement — the pen does not lift"},{"from":"left","to":"right","path":"straight across the stem","note":"the crossbar, written last"}],"pen_lifts":1,"source":"https://youtu.be/… 2:41","confidence":"high"}
> ```
>
> **A bad row** (rejected): strokes described as "the letter f is written
> with a hook and a bar" — no zones, no order, no source, and it does not
> say the hook and stem are one movement.
>
> **What I am compiling now**
>
> - Script: `{{SCRIPT}}`
> - Style: `{{STYLE}}`
> - Forms required for each letter: `{{FORMS}}`
> - Letters: `{{LETTERS}}`
> - **Expected rows: {{COUNT}}.** End your output with one final line:
>   `{"summary": {"rows": <n>, "unknown": ["<letter/form>", …], "sources": ["<url>", …]}}`
>
> **Questions I specifically need answered** — put the answer in the
> relevant row's `note`, and if a question is not settled by any source,
> say so in the summary line under `"unsettled"`:
>
> {{QUESTIONS}}

---

## Slot-ins

| Run | `{{SCRIPT}}` | `{{STYLE}}` | `{{FORMS}}` | `{{COUNT}}` |
|---|---|---|---|---|
| 1 | arabic | naskh | isolated, initial, medial, final (initial/medial only for the 27 joining letters) | 124 |
| 2 | cyrillic | cursive | lower, upper | 66 |
| 3 | cyrillic | print | lower, upper | 66 |
| 4 | greek | print | lower, upper | 48 |
| 5 | latin | print | lower, upper | 52 base + the extras below |
| 6 | latin | cursive | lower, upper | 52 base + the extras below |
| 7 | devanagari | print | letter | 43 |
| 8 | thai | print | letter | 44 |
| 9 | hebrew | print | letter | 27 |
| 10 | hangul | print | letter | 40 |

`{{LETTERS}}`:

- **arabic** — آ ا ب ت ث ج ح خ د ذ ر ز س ش ص ض ط ظ ع غ ف ق ك ل م ن ه و ي پ چ ژ ک گ ی
- **cyrillic** — а б в г д е ж з и й к л м н о п р с т у ф х ц ч ш щ ъ ы ь э ю я ё
- **greek** — α β γ δ ε ζ η θ ι κ λ μ ν ξ ο π ρ σ τ υ φ χ ψ ω
- **latin** — a–z, **plus the letters the Latin-script courses actually
  use** (19 of the 27 courses are Latin-script). Ask for these in the
  same run, lower and upper:
  - Spanish `ñ á é í ó ú ü` · French `à â ç é è ê ë î ï ô ù û ü ÿ œ æ` ·
    Italian `à è é ì ò ó ù` · Portuguese `ã õ á â é ê í ó ô ú ç à` ·
    Catalan `à è é í ï ò ó ú ü ç` · German `ä ö ü ß` ·
    Romanian `ă â î ș ț` · Turkish `ç ğ ı İ ö ş ü` · Māori `ā ē ī ō ū` ·
    Dutch `é ë ï` · Hausa `ɓ ɗ ƙ ƴ` · Yoruba `ẹ ọ ṣ`
  - English, Indonesian, Swahili, Tagalog, Latin and Jamaican Patois add
    nothing beyond a–z.
- **devanagari** — अ आ इ ई उ ऊ ए ऐ ओ औ क ख ग घ ङ च छ ज झ ञ ट ठ ड ढ ण त थ द ध न प फ ब भ म य र ल व श ष स ह
- **thai** — ก ข ฃ ค ฅ ฆ ง จ ฉ ช ซ ฌ ญ ฎ ฏ ฐ ฑ ฒ ณ ด ต ถ ท ธ น บ ป ผ ฝ พ ฟ ภ ม ย ร ล ว ศ ษ ส ห ฬ อ ฮ
- **hebrew** — א ב ג ד ה ו ז ח ט י ך כ ל ם מ ן נ ס ע ף פ ץ צ ק ר ש ת
- **hangul** — ㄱ ㄲ ㄴ ㄷ ㄸ ㄹ ㅁ ㅂ ㅃ ㅅ ㅆ ㅇ ㅈ ㅉ ㅊ ㅋ ㅌ ㅍ ㅎ ㅏ ㅐ ㅑ ㅒ ㅓ ㅔ ㅕ ㅖ ㅗ ㅘ ㅙ ㅚ ㅛ ㅜ ㅝ ㅞ ㅟ ㅠ ㅡ ㅢ ㅣ

## `{{QUESTIONS}}` per script

**Arabic (naskh):**
- Is ص / ض written as one continuous stroke or as a loop and then a bowl?
- In ل and ك (isolated and final), is the upright written before or after the base?
- Are the dots of ب ت ث ن ي added after each letter or after the whole word?
- Is the hamza of أ and إ written with the alif or added afterwards?
- When ا is joined to the previous letter, does it run **upward** from the join?
- Are ط and ظ written bowl first and then the upright, or the reverse?

**Cyrillic cursive:**
- Which letters begin with an entry hook from the baseline rather than at the top?
- Is т written with a bar above it, and ш with one below? When is the bar added?
- Are the dots of ё and the breve of й added after the letter or after the word?
- Where does the pen lift in щ and ц — before the tail or not at all?
- Do л м я keep their leading upstroke when they begin a word?

**Greek:**
- Which lowercase letters are written differently from their printed shape (θ, ζ, ξ, β, σ)?
- Is θ one stroke or two?
- Is the handwritten ξ one continuous stroke?

**Latin print:**
- Is f one stroke (hook and stem together) plus the crossbar, or three?
- Is a one stroke or two (bowl then stem)? Is d? Is g?
- Is t stem then crossbar? Is the crossbar always left to right?
- Is k three strokes or two?

**Latin — accents and extra letters** (ask in both the print and the
cursive run):
- **When is a diacritic written** — immediately after its own letter, or
  after the whole word is finished, like the i-dot? Does the answer
  differ by country or school model?
- Which of these are **a base letter plus a mark** (so the base letter's
  strokes are unchanged and only the mark is new): á à â ä ã é è ê ë í ì
  î ï ó ò ô ö õ ú ù û ü ÿ ñ ç ş ğ ă ș ț ā ē ī ō ū ẹ ọ ṣ?
- Which need **full rows because the shape itself differs**: ß, ı and İ
  (Turkish dotless and dotted i — say how both are formed and when the
  dot is added), ø, æ, œ, ɓ ɗ ƙ ƴ?
- Are **uppercase accents** written at all in handwriting (French often
  drops them), and if so is the mark the same stroke as on lowercase?
- Is the Turkish **ı** written exactly like a dotless i, and does the
  learner ever add a dot to it by mistake — is that called out in
  teaching?

**Latin cursive:**
- Which school model is being taught (D'Nealian, Zaner-Bloser, Palmer, or a national model)? Name it.
- Where does each letter start and end on the line, for joining?
- Which letters do **not** join to the letter after them?

**Devanagari:**
- Is the shirorekha (headline) drawn per letter, or across the whole word at the end?
- Which letters have a vertical stem written before the body, and which after?
- Where do the vowel signs (ि ी े ो) come in the order?

**Thai:**
- Does every consonant start at its head (the small loop), and is the loop clockwise or anticlockwise?
- Which letters have no loop to start from (ก, ญ, ธ), and where do those start?
- Where do tone marks and vowels come in the order?

**Hebrew (print/block):**
- Which letters are written in one stroke and which in two or three?
- Is the top horizontal always drawn first, and always right to left?
- Do the final forms (ך ם ן ף ץ) differ in stroke order from their base letters?

**Hangul:**
- Confirm the standard stroke order for each jamo (top to bottom, left to right).
- For ㄹ and ㅂ, how many strokes and in what order?

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
