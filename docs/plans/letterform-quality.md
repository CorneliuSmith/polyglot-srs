# Letterform quality: making the provisional strokes look written, not printed

**Owner ask, 18 Sep 2026:** *"please just make the letters look better in
russian, arabic, all the languages because they are not following best
standards for writing generally. Completely closing letters, etc."*

This is the plan for that. It is written to be executed without further
design input: each tier says what to change, in which file, and how to
tell whether it worked.

---

## 1. Why the letters look wrong

The provisional library is the **centreline of a typeface's glyph**
(`scripts/strokes/gen_from_fonts.py`: render → thin → walk → order). That
buys the right *shape family* for nothing, and it is why Arabic now looks
like Arabic. But five things separate a traced typeface from a letter a
teacher would put on a board.

1. **A printing face is not a writing model.** A font draws the *result*
   of writing: overshoot on curves, tapered terminals, a serif where a
   pen would lift. Even the handwriting faces in the table (Marck Script,
   Dancing Script) are display faces built for even colour on a line, not
   models of pen movement. A font's а is a bowl and a stem that happen to
   touch; a hand makes it in one motion with an entry stroke.
2. **Closure is lost.** A counter (о, ه, the loop of ص, the bowl of б) is
   a *ring* in the ink. Thinning gives a ring of skeleton, the walk enters
   it at one pixel and leaves at another, and the two ends are one or two
   pixels apart — which becomes a visible gap at 1000-unit scale. The
   owner's "completely closing letters" is exactly this.
3. **Terminals are eaten.** `prune_spurs` removes the whiskers thinning
   leaves at a thick terminal; it cannot tell a whisker from the last
   millimetre of a real stroke, so tails end short (the hook of ر, the
   foot of a cursive у).
4. **Crossings are not split.** Where a bar crosses a stem — f t A E
   ж х ф — the hand writes the stem in one movement and the bar in
   another. The walk follows whichever branch is straightest at the
   junction instead, so an f's crossbar comes out as part of its hook.
   Thinning leaves the junction as a 2×2 cluster, so the walk never sees
   the four ways at one pixel and cannot pair the opposite arms:
   resolving it needs the cluster collapsed to a point (Tier 0) or the
   split stated (Tier 1). **This is the f the owner found on 18 Sep.**
5. **Junctions are fused.** Where two parts of a letter touch, the
   skeleton has one pixel where the hand has two passes. The tooth logic
   and the upright logic exist to undo this case by case; every script
   has its own version of the problem and only Arabic's is handled.
6. **No proportion model.** Each form is normalised into the script's em
   box, but nothing checks that x-height, ascender, descender and (for
   Arabic) tooth height are consistent *between* letters. A letter can be
   individually plausible and wrong beside its neighbour.

The order and direction rules (LEARN, "the provisional stroke library")
are a sixth axis; they are now covered by the chart check and are **not**
part of this plan except where a rule changes a shape.

---

## 2. Tiers, cheapest first

Each tier is independently shippable and leaves the library better. Do
them in order; stop whenever the sheets look right.

### Tier 0 — Geometry repair in the generator (1 PR, no new inputs)

Purely mechanical fixes to what the walk produces. Nothing here needs a
source, a font or a speaker.

- **Close what should be closed.** After `extract` builds a form's
  strokes: if a stroke's first and last points are within `CLOSE_TOL`
  (start at 3% of the em box) *and* the stroke turns through roughly a
  full circle, snap the last point onto the first. Track the ring test by
  the accumulated turning angle, not by the gap alone, so a ر whose tail
  passes near its start is not welded shut.
- **Join what should touch.** If a stroke's end lies within `CLOSE_TOL`
  of another stroke's path (not its end), extend it to that point. This
  is the crossbar of a t that stops short, the stem of ط that does not
  reach its bowl.
- **Restore terminals.** Run `prune_spurs` only where the spur hangs off
  a junction (a T), never where it hangs off a free end. The pruning that
  matters is the fork whisker; the free-end whisker *is* the terminal.
  Measure: the ink box of each form before and after — no form should
  lose more than 2% of its length to pruning.
- **Report proportions.** The generator prints, per script, the
  distribution of ink-box top and bottom against the baseline, and flags
  any form more than 2σ from its script's median for height or width.
  This is a report, not a gate, in Tier 0.

*Done when:* no form in any script has a ring with a visible gap on the
contact sheet, and the proportion report has no unexplained outliers.
*Files:* `scripts/strokes/gen_from_fonts.py`, a new migration.
*Effort:* a day; the risk is welding shut something that should stay open,
which the turning-angle test and the sheets catch.

### Tier 1 — A per-letter rules table (1 PR, needs a source per script)

Everything the generator knows is a *global* rule per script. Some letters
simply do not follow one, and no amount of rule-tuning will fix them —
they need to be stated.

Add `RULES: dict[(script, glyph, form), Rule]` to the generator, where a
`Rule` may set: the start point (as a corner of the ink box or an explicit
coordinate), a forced stroke split at a given fraction along a stroke, a
forced merge of two strokes, "this counter is open" / "this counter is
closed", and a replacement hint string. Empty by default: a letter with no
entry keeps today's behaviour, so the table can be filled in letter by
letter without a rewrite.

Seed it from what the owner has already supplied and what is known:

| Script | Source | What it settles |
|---|---|---|
| Arabic | Ibnulyemen chart (2019), *Write it in Arabic* | ص ض as one stroke; ـل ـك stem order; the hamza carriers |
| Russian | propisi (russianlessons.net) | the hook on л м я word-initially; ъ ы ь; the т bar |
| Greek | Foundalis (blocked — needs the file) | θ ζ ξ β, which differ from the typeface |
| Devanagari | headline after the word (done) | half-forms, the ि vowel order |
| Thai | head first, clockwise (done) | ก ญ ธ, whose heads are not rings |

*Done when:* every letter the charts disagree with has an entry.
*Files:* `scripts/strokes/gen_from_fonts.py`, `docs/quality/letterforms/*.md`
for the per-script source notes.
*Effort:* half a day of code, then one sitting per script with the chart.
*Blocked on:* the Greek and Arabic sources — `foundalis.com` and
`eoimalaga.com` are blocked by this environment's egress proxy (DEBT).
Either allow them in the environment's network policy or paste the pages
into the chat as files.

#### 1a. Where the rules come from — including a model that watches video

The owner asked (18 Sep) whether a model with video access could watch
handwriting lessons and produce the rules. **Yes, and it is the right
shape of job**: a video shows exactly what a typeface cannot — how many
strokes, in what order, from where, and which parts are one movement. It
is no use for geometry (closure, terminals, proportion); that is Tier 0
code and needs no source.

Three conditions, or it comes back as prose nobody can use:

1. **One row per (script, letter, form), in a fixed schema**, not an
   essay. The file the generator will read:

   ```json
   {"script": "latin", "style": "print", "glyph": "f", "form": "lower",
    "strokes": [
      {"from": "top-right", "to": "bottom", "path": "hook, then straight down",
       "note": "the hook and the stem are one movement"},
      {"from": "left", "to": "right", "path": "straight across",
       "note": "the crossbar, written after the stem"}
    ],
    "source": "https://… at 3:14", "confidence": "high"}
   ```

   `from` and `to` come from a closed list — `top`, `top-left`,
   `top-right`, `left`, `right`, `bottom`, `bottom-left`,
   `bottom-right`, `centre`. `path` is free text and becomes the hint the
   learner reads. `note` is where a merge or a split is stated, and is
   the field that fixes the f.
2. **A source per row**: the video and timestamp, or the page. A rule
   with no source is a guess, and this library has already shipped three
   rounds of guesses.
3. **Teaching sources, not calligraphy.** A school handwriting lesson, a
   literacy channel, a primer. Calligraphy videos show a nib doing things
   a learner must not copy.

Best sources per script: Latin — a school model demonstration (D'Nealian
or Zaner-Bloser); Russian — прописи lessons, first grade; Arabic — a
*naskh* teaching channel, never *thuluth*; Greek — a Greek primary-school
writing lesson; Devanagari, Thai, Hebrew, Hangul — the same, primary
school.

**The brief itself is written**: `docs/quality/letterforms/gemini-brief.md`
— the prompt, one run per script, with each script's letter list, the
expected row count, and the questions that script has left open.

What comes back is checked like everything else: the arrowed contact
sheet against the source, letter by letter, before a migration is
written. The generator takes the table as data — the walk already accepts
a forced start and first step — so filling it needs no code per letter,
and a letter with no row keeps today's behaviour.

### Tier 2 — Better source faces (1 PR per script, needs a font choice)

Where a face is wrong for teaching, swap it. Each entry is a candidate
already OFL-licensed; the work is to add it to `FONTS`, regenerate, and
compare sheets side by side.

| Script | Today | Candidate | Why |
|---|---|---|---|
| Thai | Noto Sans Thai **Looped** | — | done (18 Sep); loopless heads were unwritable |
| Russian cursive | Marck Script | a propisi face | Marck is a display script; propisi is what children are taught |
| Hebrew | Noto Sans Hebrew (print) | an OFL cursive Hebrew | Israeli handwriting is a different alphabet; **none chosen** |
| Greek | Noto Sans | a Greek handwriting face | handwritten θ ζ ξ differ from print |
| Latin cursive | Dancing Script | a school-model face (D'Nealian-like) | Dancing Script is decorative, not a teaching model |
| Devanagari | Noto Sans Devanagari | — | acceptable; the headline was the issue |
| Hangul | Noto Sans KR | — | acceptable; jamo are geometric |

*Done when:* each script's face is one a teacher would hand out.
*Effort:* an hour per script once the face is chosen; choosing is the work.

### Tier 3 — Ground truth from speakers (product, not generation)

The generated library is scaffolding. The Workshop already lets a speaker
retrace a form and keeps its em frame and joins (PR #488), and a bundled
form can be saved over. What is missing:

- a **review queue** for stroke forms, so a second speaker signs off;
- a **coverage view**: which forms of which script are still generated
  rather than traced;
- **paid or volunteer recruitment** for one speaker per script.

*Done when:* the alphabet of at least one script is wholly speaker-traced,
which also gives a yardstick to measure the generator against.

### Tier 4 — Automatic quality gates (1 PR, after Tier 0)

Turn the eye-check into a test, so this class of problem cannot ship
again (it has twice).

For every generated form assert: every stroke has ≥ 2 distinct points; no
stroke self-intersects more than twice; closed counters are closed; the
form's ink box sits inside the script's metric envelope; stroke count is
within the expected range for that letter (from the rules table where
present, else the script median ± 2); direction matches the script rule.
Run it in `backend/tests/test_strokes.py` against the checked-in data, so
CI fails on a bad regeneration.

*Done when:* a deliberately broken form fails CI.

---

## 3. Order of work and what it costs

| # | Tier | Blocked on | Size |
|---|---|---|---|
| 1 | Tier 0 geometry repair | nothing | 1 day |
| 2 | Tier 4 gates | Tier 0 | half a day |
| 3 | Tier 1 rules table, Arabic + Russian | the charts (Arabic in hand) | 1 day |
| 4 | Tier 2 face swaps | a font choice per script | 1 hour each |
| 5 | Tier 1 rules, Greek | the Foundalis page | half a day |
| 6 | Tier 3 speaker traces | recruitment | ongoing |

Every regeneration writes a **new** migration (`--migration <name>`) and
never edits a pushed one; the client shows the bundled copy immediately,
so nothing visible waits on the owner pushing it.

---

## 4. How to tell it worked

The test is not "the sheet looks better to me". It is:

1. **The closure check**: no ring in any script has a gap (Tier 4 gate).
2. **The chart check**: each Arabic form matches the Ibnulyemen chart for
   shape, stroke count and start point — letter by letter, with the
   arrowed contact sheet beside the chart.
3. **A learner's Write step**: writing each letter the way the Learn step
   shows it passes the matcher at the shipped tolerance. If the app's own
   template cannot pass its own check, the template is wrong.
4. **The owner's eye**, last, on the two sheets per script — not first.
