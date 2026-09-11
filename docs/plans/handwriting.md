# Write — handwriting practice, letter by letter, then words, then sentences

A feature plan, written 11 Sep 2026 on the owner's ask: *real* writing
practice with a mouse or finger that walks through how each letter is
written, then has the learner translate and write words and sentences that
are assessed for correctness — Russian cursive alone and connected, Arabic
positional forms — placed in **Practice**.

**Status: Phase 1 (Free write) built and merged 11 Sep 2026** — the
canvas, the on-device neatness panel, the vision assessment on the AI
allowance, the compare view, prompts from the learner's own cards and the
course's lines, the Practice tile, for every course. Not yet built from
Phase 1: the low-confidence staff queue (DEBT.md, *Write, Phase 1*).
Phases 0's stroke-matcher spike and 2–6 are not started. The alphabet
decks stay as they are (owner, 11 Sep 2026): the question of what to do
with them is the last section, not the first.

Revised the same day on two owner points: tracing must extend to words and
whole sentences in the real joined hand (Russian cursive, Arabic initial /
medial / final), not stop at letters — §1 and §4.2; and a learner who
already writes wants, above all, to write freely and be told whether it is
correct and legible — that is now **Free write**, the first mode to ship
(§1, §4.3, §7).

**Name: Write.** It joins Speak in the half of Practice where the learner
*produces* language. The app has typing (the transliteration keyboards) and
speaking (Speak); it has never asked anyone to form a letter by hand, which
for Arabic, Persian, Hebrew, Hindi, Thai, Korean, Greek and Russian is a
skill in its own right and, for a beginner, the one that makes the script
stop looking like noise.

---

## The short answer to "is this possible for each language"

Yes for every course, with three honest caveats:

1. **The letters are a content job before they are a code job.** Guiding
   a stroke means having the stroke: for each letter, in each form it takes,
   an ordered list of pen paths a native writer would draw. No open dataset
   exists for Cyrillic cursive, Arabic positional forms, Hebrew cursive,
   Devanagari or Thai at the quality the app's other content holds. They
   have to be authored — by a speaker tracing them in a staff tool (§5).
   Roughly 600 glyph forms across the eight non-Latin scripts; ten to
   twenty hours of tracing and review, spread across languages, done once.
2. **Letter and word assessment can be exact, on the device, and free.**
   Comparing the learner's strokes to the authored template (count, order,
   direction, shape) is well-understood — the Chinese-learning apps do
   exactly this — and needs no model call. Connected writing (Russian
   cursive words, every Arabic word) is the same comparison against a
   template *composed* from the letter templates by the script's joining
   rules. That composition is the one genuinely hard algorithm in the plan
   (§4.2) and it is Phase 3, not Phase 1.
3. **Sentence assessment needs a model with eyes.** "Translate this and
   write it" produces free handwriting that no template describes. That is
   read by a vision-capable model from a picture of the strokes, which
   costs about a cent a go and draws on the same AI allowance Speak does.
   No browser can recognise handwriting on its own today (§4.3 says which
   options were considered and why they lose).

Per-language verdicts and what each needs are in §3.

---

## 1. What the learner does

Open Practice → **Write** → pick what to practise.

```
┌───────────────────────────────────────────┐
│  Write                 Russian · cursive  │
│                                           │
│  FREE WRITE   write anything — a prompt,  │
│               your own text — and be told │
│               if it is correct & legible  │
│                                           │
│  LETTERS      а б в г д е ё ж з и й к л   │
│               ● ● ● ● ◐ ○ ○ ○ ○ ○ ○ ○ ○   │
│               Learn · Trace · Write       │
│                                           │
│  WORDS &      trace or write, joined up,  │
│  SENTENCES    in the real hand            │
│                                           │
│  [ print | cursive ]   [ alone | joined ] │
└───────────────────────────────────────────┘
```

### Free write — for the learner who already writes

The mode the owner asked for first, and the one that needs no authored
content, so it ships first. Pick a prompt — a sentence to translate (the
support-locale line the app already holds for every example and drill), a
word from your own cards, or **type any text you want to practise** — or
write with no prompt at all. Write it by hand. Tap **Check**.

```
   Write in Russian:  "I am going home."
 ┌─────────────────────────────────────────┐
 │                                         │
 │            (your ink)                   │
 │                                         │
 └─────────────────────────────────────────┘
                                   ( Check )

   Read as:     Я иду домой              ✓ correct
   Legibility:  clear                    ●●●●○
   Notes:       the д is open at the top — a reader could
                take it for а · the м lacks its entry hook
   Neatness:    baseline ✓  size ✓  slant ✓  spacing ~
   ┌──────────────── compare ────────────────┐
   │  Я иду домой        ← a native hand     │
   │  (your ink)         ← yours, aligned    │
   └──────────────────────────────────────────┘
```

Four things come back, from two sources:

- **Read as / correct** — a vision-capable model reads the ink and
  compares it to the expected text (or, with no prompt, just transcribes
  and checks the spelling and grammar of what you wrote). The transcription
  is always shown: if the assessor misread you, you see that rather than a
  silent fail.
- **Legibility and notes** — the model's verdict as a *reader*: could a
  native reader read this at speed, and which letterforms cost them. At
  most two notes, the most useful ones. This is the "is it legible"
  answer, and a model that reads is the right judge of it — with the
  transcription as the calibration.
- **Neatness** — computed on the device from the ink, no model: baseline
  drift, letter-size consistency, slant consistency, spacing regularity.
  Mechanical, exact, free, and the things a writing teacher marks first.
- **Compare** — the expected text rendered in a handwriting-style face
  (later, in the composed native-hand template, §4.2), with your ink
  aligned under it, so you can see the shapes side by side yourself.

Once a script's stroke templates exist (Phases 2–3), the same matcher that
grades traced letters runs over free ink too, and "correct" gains a
per-letter stroke verdict — the form, order and direction of each letter,
not only what the text said. Free write does not wait for that; it gets
better as the content lands.

### Letters — learn, trace, write

Three steps per letter, the same shape whichever script:

```
   LEARN                TRACE                WRITE
 ┌───────────┐       ┌───────────┐       ┌───────────┐
 │    ①      │       │  ·  ·  ·  │       │           │
 │   ╭─╮     │       │ ╭─╮       │       │           │
 │  ╱   ╲    │  →    │╱   ╲ faint│  →    │   blank   │
 │ ②     ③   │       │  you draw │       │  you draw │
 │  animated │       │  over it  │       │  from     │
 │  stroke   │       │  stroke   │       │  memory   │
 │  by stroke│       │  by stroke│       │           │
 └───────────┘       └───────────┘       └───────────┘
   "start at the      each stroke turns    ✓ / "second
    top, loop left"    solid when it       stroke goes
                       matches             right-to-left"
```

*Learn* animates the strokes in order with a numbered start point and a
one-line hint per stroke. *Trace* shows the letter faintly and accepts one
stroke at a time, snapping it solid when it matches. *Write* is a blank
box; the learner draws from memory and gets a verdict per stroke. A letter
is "known" after N clean writes, and the strip at the top fills in.

For scripts with more than one form of a letter (Arabic: alone / start /
middle / end; Russian: print / cursive, lower / upper; Hebrew: print /
cursive; Hindi: letter / half-form / with each vowel sign) the forms are
steps within the letter, not separate letters — you meet ب, then ب at the
start of a word, then in the middle, then at the end, each with the joining
stroke that makes it so.

### Words and sentences — trace, then write, in the real hand

Tracing does not stop at letters. A word or a whole sentence has a stroke
template too — composed from the letter templates by the script's joining
rules (§4.2) — so the same Learn → Trace → Write steps apply to *any* text:
the app animates the word in joined Russian cursive with its connections,
or the Arabic word with each letter in its initial, medial or final form,
shows it faintly, and the learner traces it stroke by stroke, then writes
it from memory. Because the template is composed, the supply is unlimited:
every word on the learner's cards, every example and drill sentence.

The prompt for *Write* is a word or sentence the learner is actually
studying (their due or recent cards — the SRS already knows which). The
check walks their ink against the composed template and reports per
letter: the ones that match turn green, the ones that don't show the
expected form beside what they drew. Russian cursive with the connections;
Arabic with the positional forms; Hangul assembled into its syllable
blocks; Devanagari with the headline drawn last.

**Exemplar sentences.** A composed word is faithful to the forms but can
look assembled next to a real hand. So each script also gets a small set —
a dozen or two — of **speaker-traced exemplar sentences**: a native writer
writes them in one flow in the Workshop's Strokes panel, and that ink is
stored as-is. They are the Learn models a beginner watches, the "native
hand" in Free write's compare panel, and the yardstick the composer is
tuned against (compose the same sentence, overlay the exemplar, fix the
joins until they agree).

```
   Write:  дом   (house)
 ┌─────────────────────────────┐
 │                             │
 │        (your ink)           │
 │                             │
 └─────────────────────────────┘
   д ✓   о ✓   м ✗  the м starts with a hook — [show]
```

Translate-and-write is Free write with a prompt: the sentence in the
learner's own language, the course-language answer expected. On a miss the
transcription shows the differing words marked, the expected sentence, and
the letterform notes. This is also the step that catches "you wrote the
right letters in the wrong words".

### The two toggles

*print / cursive* and *alone / joined* — where the script has the
distinction. A learner can go straight to *Write* and skip *Learn* and
*Trace* entirely: "just write and see if you are writing correctly" is a
mode, not a graduation.

---

## 2. Where it lives

Practice's quiet row becomes four tiles — Gym, Read, Tutor, **Write** — two
by two on a phone, four across on a desktop (the row already switches
between two and three columns by whether the language has a Gym; the same
rule hides Write for a language with no authored strokes yet). Speak keeps
the accent slot. Route `/write`; the page owns its own sub-navigation.

Nothing on the Study page changes. Write does not enter the daily loop
until the alphabet-deck decision (§8) is made.

---

## 3. Per-language feasibility

"Forms" is the number of stroke templates a speaker has to trace for the
script to be complete. "Joining" is what the word-level composer must
model. Effort is content, not code — the engine is shared.

| Course | Script | What "writing it" actually means | Forms | Joining model | Verdict |
|---|---|---|---|---|---|
| **Russian** | Cyrillic | Handwriting **is cursive** — print is what you read, not what you write. 33 lower + 33 upper cursive; print optional. Several letters change shape entirely (т→m, д→g-like), л/м/я start with a hook, о joins from the top. | ~66 (+33 print) | Every letter joins; entry/exit points per letter; a handful of exceptions. | **Yes.** First script to build — the owner's case and the clearest connected-writing test. |
| **Arabic** | Arabic | Positional forms are mandatory: alone / start / middle / end, six letters (ا د ذ ر ز و) join only from the right. Plus hamza carriers, ة, ى, the لا ligature. Everyday handwriting is closer to *ruqʿah* than to the Naskh the app renders; teach a Naskh-shaped hand first (matches the font and every textbook), offer ruqʿah later. Short vowels are marks, not strokes — optional. | ~100 (+~20 ruqʿah later) | Inherent — a word *is* joined letters. Positional form chosen by the neighbours' joining class (a small table; the Letters page already uses the ZWJ trick to render them). | **Yes.** Second script; shares the joining engine with Persian. |
| **Persian** | Arabic | Arabic plus پ چ ژ گ and its own ی/ک forms. Nastaʿlīq is calligraphy; everyday handwriting is a Naskh/ruqʿah hand. | +~16 on Arabic | Same as Arabic. | **Yes**, for the cost of 16 forms once Arabic exists. |
| **Hebrew** | Hebrew | The key fact: Hebrew **handwriting is a different alphabet** from print (ktav yad — א looks like a loop-and-tail, not the block letter). Learners read print and write cursive. 22 + 5 finals in each. No joining. Niqqud optional. | ~54 | None (letters stand apart). | **Yes.** Simpler than Russian mechanically; the cursive forms are the content. |
| **Greek** | Greek | Handwriting is print-like with a few cursive-ish variants (β, θ, ς). 24 lower + 24 upper + ς. | ~50 | None. | **Yes.** Cheapest non-Latin script. |
| **Hindi** | Devanagari | The writing unit is the *akshara*: consonant + vowel sign, the headline (शिरोरेखा) drawn **after** the letters of a word, half-forms in conjuncts. 11 vowels, 33+ consonants, ~12 vowel signs (before/after/above/below), ~30 common half-forms. | ~90 | Headline as a final stroke across the word; vowel-sign placement by class; half-form substitution before a consonant. | **Yes, with the most composition rules.** Word level lands after ru/ar. |
| **Thai** | Thai | No spaces, no joining; 44 consonants, ~32 vowel shapes that sit before/after/above/below the consonant, 4 tone marks. The one rule that matters: **start at the loop**. Loopless "modern" fonts hide exactly what a learner must write — the reference must use a looped face. | ~80 | Vowel placement by class; no strokes cross letters. | **Yes.** Letter level is easy; word level is a layout problem, not a stroke problem. |
| **Korean** | Hangul | 24 basic + 16 compound jamo, assembled into syllable blocks by six layout patterns; stroke order is strict (left→right, top→bottom). The most *algorithmic* script: 40 templates and a block composer cover everything. | ~40 | Block composition by pattern (initial · vowel · final); scale each jamo into its cell. | **Yes.** Word level is the composer; once it exists, every syllable works. |
| **Latin-script courses** (es fr de it pt nl ca ro tr id tl sw ha yo xh la jam) | Latin | Learners from these languages' home scripts already write Latin; the value is for the **English course** and any Latin course studied *from* Arabic, Russian, Thai, Korean… Print lower + upper (52) plus each language's own letters and marks (ñ ç ß ğ ş ı ă â î ș ț; Hausa ɓ ɗ ƙ; Yoruba ẹ ọ ṣ and tones). Latin **cursive** is a separate style few learners need — leave it off. | 52 shared + ~5–15 per language | None (print). | **Yes, later.** One shared engine; per-language extras are small. |
| **Jamaican Patois** | Latin | Cassidy–LePage spelling is plain Latin. | 0 beyond Latin | — | **Covered by Latin.** |

Sentence-level assessment (§4.3) works for every script the model can read
handwriting in; that is all of the above, with the weakest confidence on
beginner Devanagari and Thai, where a wobbly loop changes the letter. The
plan handles that by showing the transcription — the learner sees what the
assessor *read*, so a misread is visible rather than silently marked wrong.

---

## 4. How the checking works

### 4.1 Letters — on the device, exact, free

The canvas captures strokes as timed point lists from pointer events (mouse,
finger, pen — one API; `touch-action: none` on the box so a phone doesn't
scroll while you draw). Each template is the same thing authored: an
ordered list of strokes, each a point list, in a 1000×1000 box, with a
start-point hint.

Checking one stroke against its template:

1. **Normalise** — translate and scale the learner's whole attempt to the
   template box (so size and placement don't matter), resample every stroke
   to a fixed number of points.
2. **Count and order** — the same number of strokes, in the same order.
   Cursive letters and Arabic forms mark which strokes *may* be joined into
   one continuous pen movement, so writing б in one go is not a fault.
3. **Direction** — the start of the learner's stroke is nearer the
   template's start than its end (a stroke drawn backwards fails here with
   the message "this stroke goes the other way").
4. **Shape** — average point-to-point distance after alignment (dynamic
   time warping so a slow start doesn't skew it), within a tolerance that
   is loose in *Trace* and tighter in *Write*.

Every failure names the stroke and the reason. This is the approach the
established Chinese-character trainers use; it is a few hundred lines of
TypeScript, no dependency, and it runs offline — which matters for the
native apps plan.

### 4.2 Words — the composed template

A word's template is built from letter templates by the script's rules:

- **Cyrillic cursive** — each letter carries an *entry* and *exit* point;
  the composer places letters left to right, joins exit to next entry with
  a connecting segment, and applies the exceptions (letters after о join
  from the top; л м я begin with a hook only word-initially or after a
  non-joining letter).
- **Arabic / Persian** — pick each letter's positional form from its
  neighbours' joining class (right-joining letters break the chain), place
  right to left on a baseline, substitute لا. The joining stroke is part of
  the form, so there is no separate connector.
- **Hangul** — choose the block layout from (initial, vowel, final?) and the
  vowel's orientation, scale each jamo into its cell.
- **Devanagari** — place consonants, substitute half-forms before a
  following consonant, attach vowel signs by class, then append the
  headline as the final stroke across the word.
- **Thai, Hebrew, Greek, Latin** — place glyphs; vowel/mark placement by
  class for Thai.

The learner's ink is then matched *progressively*: strokes are consumed
left to right (right to left for Arabic and Hebrew) against the composed
stroke list, so a whole word written in one continuous cursive stroke is
segmented by where it best matches each letter in turn. This is the hard
part of the plan. It is bounded — the composition rules per script fit on
a page each — but it is where the feel has to be tuned on real hands, which
is why Phase 0 builds a spike of it for Russian before anything is
committed to.

### 4.3 Free writing — a model that can see, plus what the ink itself says

Free writing has no template (until §4.2's composer exists for the
script, after which the matcher of §4.1 runs over free ink as well and adds
a per-letter stroke verdict). The client renders the ink to a PNG (the
canvas's own export, ~1000×400 px, a few kilobytes) and posts it with the
expected sentence — or with nothing, when the learner wrote without a
prompt, in which case the model transcribes and judges the spelling and
grammar of what it read. The backend calls a vision-capable Claude model
(`resolve_model("write_assess")`, one tier above the translate tier — the
same rule the checker follows) with a tool schema:

```
transcription   what was written, as text
matches_target  bool
word_diffs      [{expected, written, note}]
letterform_notes [{letter, note}]     ← at most two, the most useful
legibility      1–5
confidence      low | medium | high
```

Confidence *low* is shown as "I'm not sure I read this right — here is
what I saw" rather than as a fail, and lands in a staff queue (the existing
feedback queue, kind `writing`) so a speaker can look.

**Neatness, on the device.** Independent of the model, the ink yields
four mechanical measures a writing teacher marks first, each exact and
free: *baseline drift* (fit a line through stroke bottoms; report the
slope and wobble), *size consistency* (variance of stroke heights,
x-height band), *slant consistency* (variance of the dominant stroke
angle), *spacing regularity* (variance of gaps between ink clusters along
the baseline; for Arabic, between joined groups). Shown as ✓ / ~ / ✗ with
a one-line tip. These need no template, no model and no content, so they
are in the first shipped version. Spend draws on the
learner's AI allowance exactly as Speak's turns do — one assessment is one
"message" — after a cheap on-device gate (enough ink, more than one
stroke) so an empty box costs nothing.

**What was considered and why it loses.** The browser Handwriting
Recognition API is Chrome-only, never shipped past origin trial, and absent
on iOS — building on it would mean no Safari. Tesseract.js is print OCR and
fails on cursive and beginner hands. Google's ML Kit *Digital Ink* is
excellent and on-device but native only — worth a Capacitor plugin later
for the phone apps (word-level recognition offline), not a web foundation.
A vision model is the only path that works everywhere now, and its
per-call cost is small.

### 4.4 What one assessment costs

Image ≈ 500–700 tokens, prompt ≈ 400, output ≈ 200. On the tier the
checker uses today that is under **one cent** per sentence. A learner
writing ten sentences a session, five sessions a week, is about $2 a month
at list price — within the AI allowance a paid tier already funds. Letters
and words cost nothing.

---

## 5. The content: authored strokes, in the Workshop

The strokes are content and get the same treatment as every other kind:
authored, reviewed by a speaker, versioned, importable.

**A "Strokes" panel in the Workshop.** Pick a script, a glyph and a form.
The glyph renders faintly behind the canvas in a handwriting-style font
(so the author traces a real letterform, not their memory of one — Arabic
positional forms via the ZWJ trick the Letters page already uses). The
author draws the strokes in order; each is recorded, resampled and
smoothed; they set the entry/exit points for joining scripts, add a
one-line hint per stroke ("start at the top"), preview the animation, save.
A reviewer for that language marks it reviewed. About a minute per form;
the whole of Russian cursive is an evening, Arabic a weekend.

The same panel records **exemplar sentences**: the author writes a given
sentence in one flow, as they would on paper, and the ink is stored whole
(strokes, order, timing) against the sentence text — no cutting into
letters. A dozen per script, chosen to cover every letter in every form
(a pangram-style set the panel can propose from the alphabet).

**A file path for bulk work.** `data/strokes/{script}.json` — the same
pattern as `data/alphabet/{code}.json`: a reviewed set authored elsewhere
seeds without touching code. Templates carry `source` and `reviewed` like
every other row.

**An accelerator, optional.** Font outlines (via opentype.js) can be
skeletonised into a centreline, giving the *shape* of every glyph for free
— but not the stroke *order* or *direction*, which is what teaching is. So
a possible Phase 1.5: pre-fill each form with its skeleton and let the
author only cut and order the strokes. Worth trying on Arabic where the
forms are many and the shapes regular; not worth building before a human
has traced one script by hand and the team knows what "good" feels like.

**Reference fonts.** Google Fonts serves the app already (Noto Naskh
Arabic). Handwriting-style faces exist there for Cyrillic (Marck Script,
Caveat), Devanagari (Kalam), Korean (Nanum Pen Script), Thai — but the
Thai face must keep its loops (Sarabun does not; Noto Serif Thai does).
Hebrew cursive has no Google face; an OFL font can be self-hosted. The
font is only the tracing guide and the "expected" rendering — never the
stroke source.

---

## 6. Data and API

Tables (one migration, owner-applied, code degrades without it as usual):

- `script_glyphs` — `script`, `language_code` (null for script-wide),
  `glyph`, `form` (`alone | start | middle | end | lower | upper | half |
  print | cursive`), `style` (`print | cursive | naskh | ruqah`), `strokes`
  jsonb, `joins` jsonb (entry, exit, joins_next), `hints` jsonb, `source`,
  `reviewed`, `created_by`. Unique on (script, glyph, form, style).
- `script_exemplars` — `script`, `language_code`, `style`, `text`,
  `strokes` jsonb (the whole sentence as written), `source`, `reviewed`,
  `created_by`. The native-hand models and the composer's yardstick.
- `writing_progress` — per (user, glyph) attempts, passes, best score,
  last practised. Drives the letter strip and, later, an SRS-style
  revisit of weak letters.
- `writing_attempts` — per (user, language) attempts at the word and
  sentence level: target, score, feedback jsonb, `created_at`. **Ink is
  not stored by default** — handwriting is as personal as a voice
  recording, and Speak keeps no audio. Low-confidence sentence
  assessments keep their PNG for 30 days so a staff reviewer can see what
  the model saw; that is the one exception and it is deleted on a timer.

Endpoints: `GET /api/write/manifest?language_id` (scripts, styles, forms
authored, counts — what the Practice tile keys on); `GET
/api/write/glyphs?script&style`; `POST /api/write/progress`; `GET
/api/write/words?language_id` (the learner's own current words); `GET
/api/write/sentences?language_id` (support-locale prompts with their
course-language answers, from the example and drill tables); `POST
/api/write/assess` (PNG + expected text, or PNG alone → verdict;
allowance-gated); `GET /api/write/exemplars?script&style`. Workshop:
`PUT /api/contribute/strokes` and the review flag.

---

## 7. Phases

Free write comes first because it needs nothing authored: the day it
ships, the owner can write Russian or Arabic and be told whether it is
correct and legible. Everything traced depends on strokes existing, so it
follows the authoring tool.

| Phase | What lands | Size |
|---|---|---|
| **0 — Spike** | The canvas and stroke capture on a phone and a mouse; a first pass of the vision assessment prompt on real handwriting samples (the owner's, in Russian and Arabic) to see how it reads a beginner and an adult hand; the letter matcher and a *rough* Russian cursive composer on five hand-traced letters, to settle the tolerances. **No schema, no UI polish.** | 2–3 days |
| **1 — Write: Free write** | The Practice tile and page; the canvas; prompts from the learner's own cards, from the example/drill translations, or typed; vision assessment on the allowance with the on-device gate; the neatness panel; the compare view in a handwriting-style face; the low-confidence queue in the Workshop. **Ships for every course at once — no content needed.** | ~1.5 weeks |
| **2 — Strokes in the Workshop** | The authoring panel (single forms *and* one-flow exemplar sentences), the tables, the import path, reviewed flag. The owner or a speaker traces Russian cursive (66) and Arabic (~100) and a dozen exemplar sentences each. | ~1 week build; content in parallel |
| **3 — Write: Letters** | The three-step letter flow, per-form steps, progress strip, print/cursive toggle. Ships per script as its strokes are reviewed. | ~1 week |
| **4 — Write: Words and sentences, traced** | The composers (Cyrillic joins, Arabic/Persian forms, Hangul blocks, Devanagari headline, Thai/Hebrew/Greek/Latin placement) tuned against the exemplars; progressive matching; Learn → Trace → Write over any word or sentence; the same matcher over free ink for per-letter verdicts in Free write; the composed native hand replaces the font in the compare view. | 1–2 weeks, ru/ar first |
| **5 — The rest of the scripts** | Hebrew, Greek, Hindi, Thai, Korean, Persian as their strokes are authored; the shared Latin engine for the English course. | content-paced |
| **6 — Native apps** | ML Kit Digital Ink via a Capacitor plugin for offline word recognition, if the phone apps plan proceeds. | later |

Order of scripts is by the owner's priorities and by who can review:
Russian and Arabic first (the ask), then whichever of Hebrew / Greek /
Korean has a speaker available — they are the cheapest — then Hindi and
Thai, whose composition rules are the most work.

Total: roughly five to seven weeks of build across phases 0–4, plus ten to
twenty hours of speaker tracing and review, plus the reviewed strokes being
the gate for each script's *traced* modes going live. Free write is live
for every course from Phase 1.

---

## 8. The alphabet decks

**Kept, unchanged, until Write has letter progress.** Then the decision:

The alphabet deck teaches a letter as a *typing* card — prompt is the
romanisation and sound, answer is typing the letter on the transliteration
keyboard. That is reading-and-typing, not writing, and it is the only path
today that walks a beginner through the script in order. Write's Letters
mode covers the same ground by hand. Once it exists there are three
options, and only the owner can pick:

1. **Keep both.** The deck stays in Study as the typing drill; Write is
   the handwriting drill. Two answers to "learn the letters", which is what
   the owner is reacting to.
2. **Replace the deck's answer.** Letter cards stay in the SRS but their
   drill becomes *write the letter* (canvas) instead of *type the letter*,
   with typing as a fallback on a device with no pointer worth the name.
   One path, spaced repetition intact, nothing deleted. **Recommended**
   once Phase 2 is stable — it turns the decks into Write's spaced-review
   layer rather than a rival.
3. **Retire the deck.** Write's progress strip is the only letter path;
   `A0` rows are retired (`vocabulary.retired`, not deleted — the
   migration for that already exists). Loses spaced review of letters
   unless (2) is done first.

Nothing in Phases 0–4 depends on this choice.

---

## 9. Open decisions for the owner

1. **Russian: cursive first?** Recommended yes — it is what Russians write
   and what the ask names. Print forms as an optional second style.
2. **Arabic hand: Naskh-shaped first, ruqʿah later?** Recommended yes.
3. **Hebrew: cursive for writing, print for reading only?** Recommended
   yes — teaching a learner to hand-draw block letters is teaching them
   something no Israeli does.
4. **Sentence assessment on the AI allowance, as Speak is?** Recommended
   yes; a separate cap is more knobs for no reason.
5. **Keep the ink?** Recommended no, with the 30-day exception for
   low-confidence assessments a reviewer needs to see.
6. **Latin cursive?** Recommended no — print and the language's own
   letters only.
7. **Who traces?** The owner for Russian; a speaker for each other script.
   The Workshop panel makes it a task a reviewer can do without an
   engineer.

---

## 10. Risks, named

- **Progressive matching on continuous cursive** may need more tuning
  than a phase allows. Mitigation: Phase 0 spikes it before anything else
  is committed; the fallback is asking for words letter by letter (each
  letter in its joined form) until it is right.
- **Beginner handwriting misread by the model** at the sentence level,
  most likely in Devanagari and Thai. Mitigation: show the transcription;
  low confidence is not a fail; the reviewer queue.
- **"Legible" is a judgement, not a measurement.** The model answers as a
  reader, which is the right question, but it is one reader. Mitigation:
  the neatness panel is exact and separate; the compare view lets the
  learner judge shapes themselves; and once templates exist the per-letter
  stroke verdict is a fact, not an opinion. Phase 0 tests the assessor on
  the owner's own hand first, so its calibration is known before anyone
  else sees a verdict.
- **Content stalls a script.** A script with no reviewed strokes simply
  does not show Write — the same rule as Gym for a language with no form
  categories. Nothing half-authored reaches a learner.
- **Phone ergonomics.** A finger on a 5-inch screen is not a pen. The
  canvas is the full width, letters are drawn large, and the Trace step's
  tolerance is generous. Pen input (Apple Pencil, S-Pen) comes through the
  same pointer events with pressure and works without extra code.

---

## 11. Adapting to the learner's hand (planned 11 Sep 2026, owner ask)

A reader that has seen your writing before reads it better. After the
first session the owner's *d* (straight ascender) and *e* (open loop, long
tail) were flagged as ambiguous — which is fair for a stranger and useless
the fifth time. The reader should adapt; the learner must be able to see
that it has, turn it off, and wipe it.

### What "adapt" means, concretely

Four mechanisms, in the order they pay off:

1. **Reference samples — the reader is shown your hand.** The single most
   effective lever with a vision model is a few examples of *this*
   writer's letters with their confirmed text. Up to three of the
   learner's own samples ride along with each Check as extra image blocks
   ("reference: this writer's confirmed hand; it reads *X*"). Misreads
   drop, and a consistent personal form stops being a "difference".
   Needs ink to be kept — see the setting.
2. **Confirmations — the learner teaches it.** After a misread, one tap:
   *"I wrote the expected text"* (or edit the transcription). That
   attempt becomes a confirmed sample, and its letterforms become known
   habits. Without this the profile is only the model's own opinion of
   itself; with it, the learner corrects the reader the way they would a
   person.
3. **A hand profile — habits, not repeats.** Per (learner, language): a
   small list of letterform habits with counts and last-seen dates,
   built from confirmed samples and from notes that recur. Once a habit
   is confirmed legible it is passed to the reader as "known and fine —
   do not flag"; a habit that keeps costing legibility is flagged
   *once*, then tracked, and shown in the notes as *"your д again — third
   time"* rather than as a fresh discovery. The profile is also what the
   Progress page can chart: legibility over time, per language.
4. **Personal neatness baselines.** The neatness panel compares the
   session to the learner's own typical values (their usual slant, their
   usual gap rhythm), so the verdict becomes *"steadier than your
   usual"* rather than a fixed bar. And when the stroke matcher lands
   (Phases 2–4), the per-letter tolerance widens for a form the learner
   has confirmed and the reader finds legible — the matcher adapts to a
   hand the same way the reader does.

### The setting — Account → Learning

**"Adapt to my handwriting"** — one toggle, on by default, with a plain
line under it: *"Keeps a few of your own writing samples (up to twelve
per language) so the reader learns your hand. Turn it off and they are
deleted."* Beside it, **"Reset what it has learned"** — deletes the
samples and the habits for the current language (or all languages) and
starts fresh; useful after a learner changes how they form a letter on
purpose. Turning the toggle off deletes everything and stops collecting;
turning it on starts again from nothing. This is the only place ink is
ever kept, and it is the learner's to remove.

### Data

- `writing_profiles` — `(user_id, language_id)`, `adapt` boolean (the
  toggle, default true), `habits` jsonb `[{letter, note, count,
  confirmed_ok, last_seen}]`, `stats` jsonb (running legibility mean and
  count), `updated_at`. Own-only RLS.
- `writing_samples` — `id`, `user_id`, `language_id`, `text`, `image`
  (PNG, capped at ~60 KB — the export is small), `strokes` (the compacted
  `[x, y, t]` strokes — the method, not only the shape), `method` (its
  summary), `confirmed` boolean, `created_at`. **Rolling cap of twelve per language**, preferring
  confirmed samples and letter diversity (a sample whose text covers
  letters no kept sample has beats a duplicate). Own-only RLS; deleted
  with the toggle and by Reset.

### The call

With `adapt` on and samples present, the assessor's message gains up to
three reference images before the learner's canvas, and the system prompt
gains the habits: *"Known forms of this writer, confirmed legible — do not
flag: д with a straight ascender; е with an open loop."* Three extra
images are roughly 1,500 tokens — the assessment stays under two cents.
With `adapt` off, or on a fresh profile, the call is exactly today's.

### What it must not do

- Never store ink without the toggle on; never keep more than the cap;
  never keep a sample the learner has not confirmed *or* the reader read
  with high confidence (a low-confidence sample teaches the wrong hand).
- Never lower the bar for correctness. The profile makes the reader
  *read* better and stops it repeating itself; a misspelled word is still
  a difference, and a form the reader still cannot read is still a note.
- Never share samples across learners. One person's hand is one person's.

### Phases

| | What lands | Size |
|---|---|---|
| A | **Built 11 Sep 2026.** Confirm button on a misread → confirmed sample + habit; `writing_settings`, `writing_profiles`, `writing_samples` (migration 20261019); the Account toggle and Reset; samples ride along on Check — with the **method** of each sample (strokes, lifts, direction, speed; `services/ink_method.py`) kept and told to the reader, on the owner's ask that how one writes be captured, not only what. | ~1 week |
| B | Habits into the prompt (known-fine forms not flagged; recurring ones counted); Progress page legibility trend. | 2–3 days |
| C | Personal neatness baselines. | 1–2 days |
| D | Adaptive tolerance in the stroke matcher — with Phase 4 of the main plan. | with Phase 4 |

---

## 12. The writer's verdict, and a baseline (planned 11 Sep 2026, owner ask)

Two facts the second day of use made plain. In **Free** mode the reader
badged "Correct" — which was the reader grading the spelling of its *own*
reading; nobody but the writer knows what was written, so a verdict there
is meaningless until the writer gives one. And a reader that learns a hand
one Check at a time takes weeks to become useful; a writer should be able
to hand it their hand in one sitting.

### 12.1 The writer's verdict is the ground truth

- **Free mode never claims "correct".** It shows what it read, a spelling
  line about that reading, and asks **"Is this what you wrote?"** — *Yes*
  confirms the reading as it stands; *No — I wrote…* opens it to edit and
  confirm. (Built with Phase A, 11 Sep.)
- **Every Yes / No is a labelled example**, and the label is the only
  ground truth the whole adaptation has. *Yes* → a confirmed sample and
  the flagged forms marked known-fine. *No + correction* → a confirmed
  sample of the corrected text, and — the new part — a **misread record**:
  which letters the reader got wrong in this hand, from the diff between
  its reading and the writer's text, aligned letter by letter.
- **An accuracy readout, per language**: "the reader gets your hand right
  *N* of *M* times" and "letters it trips on: أ ن". Shown in Account under
  the toggle and, briefly, on the Write page after a confirmation. It is
  what tells the writer the adaptation is real, and tells the owner, in
  aggregate per script (Workspace → Insights), where the reader is weak
  before anyone complains.

### 12.2 Baseline: hand the reader your hand in one sitting

**Write → "Set up my hand"** (also from Account, beside the toggle; and
*Redo my baseline* after a deliberate change of hand):

```
   Set up my hand · Arabic                     3 of 8
 ┌─────────────────────────────────────────────────┐
 │  Write:  أنا أحب البيت الكبير                    │
 │  (in your usual hand — this is not a test)      │
 │                                                 │
 │             (canvas)                            │
 └─────────────────────────────────────────────────┘
   Read as:  أنا أحب البيت الكبير    Is this what you wrote?  [Yes] [No…]
```

- **Eight short prompts per script**, chosen so that between them every
  letter appears in every form it takes — the Arabic positional forms, the
  Russian cursive lower- and upper-case, the Hebrew cursive alphabet, the
  Hangul jamo across the block patterns, the Devanagari vowel signs. This
  is the **same content as §5's exemplar sentences**: a coverage set the
  Strokes panel can propose from the alphabet, reviewed by a speaker. One
  set per script serves both the Learn models and the baseline.
- Each prompt is written, read, and **confirmed by the writer** (Yes /
  No…). Eight confirmed samples with their method land at once; the reader
  has the hand from the next Check. Legibility and neatness on the
  baseline are *recorded, not judged*: this is the writer's normal, the
  yardstick for Phase C's personal neatness ("steadier than your usual")
  and the zero point of the Progress trend.
- **Letters to watch.** The baseline's misread records produce, on the
  spot, the list of letters the reader could not read in this hand — and
  that is also, honestly, the list a stranger might struggle with. Shown
  once at the end; kept in the profile.
- Free of charge in AI terms beyond eight Checks; capped at one baseline
  per language per day so it cannot be used as unlimited spend.

### 12.3 Data

- `writing_profiles.stats` gains `checks`, `confirmed_right`,
  `confirmed_wrong`, `misread_letters` (letter → count),
  `baseline_at`, and the baseline's neatness measures.
- `writing_samples.source` — `check | confirm | baseline`, so baseline
  samples can be preferred as references and replaced by *Redo*.
- `script_coverage_sets` — or simply the exemplar rows of §5 tagged
  `baseline_order`; no new table if §5's `script_exemplars` lands first.
  Until a script has a reviewed set, the baseline uses the course's own
  A1 sentences chosen greedily for letter coverage — worse, but never
  absent.

### 12.4 Phases

| | What lands | Size |
|---|---|---|
| A′ | Free mode asks the writer; Yes / No…; no false "Correct". **Built 11 Sep.** | — |
| B | **Built 11 Sep 2026.** Misread records from No + correction (letter-level diff, `services/write_diff.py`); accuracy readout and letters-to-watch on Write after a confirmation, in Account, and on Progress with a legibility strip; per-course aggregate in Workspace → Insights. | 3–4 days |
| C | The baseline session: coverage sets (greedy from A1 sentences now, §5 exemplars when reviewed), the eight-prompt flow, *Redo*, baseline stats recorded; baseline samples preferred as references. | ~1 week |
| D | Personal neatness against the baseline (was §11 C). | 1–2 days |
| E | **Built 11 Sep 2026 with B.** Habits counted back ("again — 3×" on a repeated note); the Progress card's legibility strip. | 2–3 days |

The order is deliberate: B first because the accuracy number is what
proves the adaptation to the writer and what tells the owner whether the
reader is good enough per script to keep building on; C second because
the coverage sets are content, and content takes the longest to arrive.

