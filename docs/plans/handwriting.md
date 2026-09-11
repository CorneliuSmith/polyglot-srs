# Write — handwriting practice, letter by letter, then words, then sentences

A feature plan, written 11 Sep 2026 on the owner's ask: *real* writing
practice with a mouse or finger that walks through how each letter is
written, then has the learner translate and write words and sentences that
are assessed for correctness — Russian cursive alone and connected, Arabic
positional forms — placed in **Practice**.

**Status: plan only. Nothing is built.** The alphabet decks stay as they
are (owner, 11 Sep 2026): the question of what to do with them is the last
section, not the first.

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
│  LETTERS      а б в г д е ё ж з и й к л   │
│               ● ● ● ● ◐ ○ ○ ○ ○ ○ ○ ○ ○   │
│               Learn · Trace · Write       │
│                                           │
│  WORDS        write the words you are     │
│               learning, joined up         │
│                                           │
│  SENTENCES    translate and write —       │
│               checked when you're done    │
│                                           │
│  [ print | cursive ]   [ alone | joined ] │
└───────────────────────────────────────────┘
```

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

### Words — joined up

The prompt is a word the learner is actually studying (their due or recent
cards — the SRS already knows which). They write it in one go. The check
walks their ink against the composed template and reports per letter: the
ones that match turn green, the ones that don't show the expected shape
beside what they drew. Russian cursive with the connections; Arabic with
the positional forms; Hangul assembled into its syllable blocks; Devanagari
with the headline drawn last.

```
   Write:  дом   (house)
 ┌─────────────────────────────┐
 │                             │
 │        (your ink)           │
 │                             │
 └─────────────────────────────┘
   д ✓   о ✓   м ✗  the м starts with a hook — [show]
```

### Sentences — translate and write

The prompt is a sentence in the learner's own language (the support-locale
line the app already holds for every example and drill); the learner writes
the course-language sentence by hand. When they tap **Check**, the ink goes
to the assessor and comes back as:

```
   You wrote:   Я иду домой
   Expected:    Я иду домой                          ✓ correct
   Handwriting: clear · the д could be more open — [show]
```

or, on a miss, the transcription with the differing words marked, the
expected sentence, and one or two notes on letterforms. This is also the
step that catches "you wrote the right letters in the wrong words".

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

### 4.3 Sentences — a model that can see

Free writing has no template. The client renders the ink to a PNG (the
canvas's own export, ~1000×400 px, a few kilobytes) and posts it with the
expected sentence. The backend calls a vision-capable Claude model
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
feedback queue, kind `writing`) so a speaker can look. Spend draws on the
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
/api/write/assess` (PNG + expected → verdict; allowance-gated). Workshop:
`PUT /api/contribute/strokes` and the review flag.

---

## 7. Phases

| Phase | What lands | Size |
|---|---|---|
| **0 — Spike** | The canvas, stroke capture, the letter matcher, and a *rough* Russian cursive composer, with five Russian cursive letters and five Arabic forms traced by hand. Tried on a phone and a mouse. Decides the tolerances and whether the progressive matcher feels right. **No schema, no UI polish.** | 2–3 days |
| **1 — Strokes in the Workshop** | The authoring panel, the tables, the import path, reviewed flag. The owner or a speaker traces Russian cursive (66) and Arabic (~100). | ~1 week build; content in parallel |
| **2 — Write: Letters** | The Practice tile and page, the three-step letter flow, per-form steps, progress strip, print/cursive toggle. Ships for any script with reviewed strokes. | ~1 week |
| **3 — Write: Words** | The composers (Cyrillic joins, Arabic/Persian forms, Hangul blocks, Devanagari headline, Thai/Hebrew/Greek/Latin placement) and progressive matching; prompts from the learner's own cards. | 1–2 weeks, ru/ar first |
| **4 — Write: Sentences** | Vision assessment on the allowance, the on-device gate, feedback UI, low-confidence queue in the Workshop. | ~1 week |
| **5 — The rest of the scripts** | Hebrew, Greek, Hindi, Thai, Korean, Persian as their strokes are authored; the shared Latin engine for the English course. | content-paced |
| **6 — Native apps** | ML Kit Digital Ink via a Capacitor plugin for offline word recognition, if the phone apps plan proceeds. | later |

Order of scripts is by the owner's priorities and by who can review:
Russian and Arabic first (the ask), then whichever of Hebrew / Greek /
Korean has a speaker available — they are the cheapest — then Hindi and
Thai, whose composition rules are the most work.

Total: roughly five to seven weeks of build across phases 0–4, plus ten to
twenty hours of speaker tracing and review, plus the reviewed strokes being
the gate for each script going live.

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
- **Content stalls a script.** A script with no reviewed strokes simply
  does not show Write — the same rule as Gym for a language with no form
  categories. Nothing half-authored reaches a learner.
- **Phone ergonomics.** A finger on a 5-inch screen is not a pen. The
  canvas is the full width, letters are drawn large, and the Trace step's
  tolerance is generous. Pen input (Apple Pencil, S-Pen) comes through the
  same pointer events with pressure and works without extra code.
