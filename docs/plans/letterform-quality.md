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

0. **Measured every stroke, 19 Sep.** 659 letters across every script
   the app teaches have a sourced rule, and `check_rules.py` scores the
   generator against them. The first version of that checker scored
   only the **first** stroke of each letter, with a tolerance that
   allowed an adjacent zone — and the owner found three letters it
   could not see: **B** drawn bowls-first (both orders start top-left,
   so stroke 1 looked right), **a** ending mid-letter going up, and
   **d** starting at the stem instead of the bowl. One stroke of N,
   judged loosely, is not a check. It now scores every stroke — start
   zone, end zone, and which way round it runs — and the headline is
   **letters where every stroke is right**, the only figure that means
   what it sounds like.

   That honest number was 133 of 659. Two operations took it to 227.
   `fit_taught()` permutes and flips a letter's strokes into the order
   and direction the source teaches; `start_ring_where_taught()` then
   rotates a free-standing closed ring so the pen touches down where the
   source starts it.

   | table | letters | every stroke right | strokes right |
   |---|---|---|---|
   | arabic naskh | 124 | 33 → **37** | 126 → **138** of 218 |
   | latin cursive | 128 | 14 → **19** | 75 → **108** of 237 |
   | latin print | 73 | 27 → **47** | 76 → **112** of 138 |
   | cyrillic print | 66 | 10 → **33** | 74 → **131** of 179 |
   | cyrillic cursive | 66 | 7 → **9** | 23 → **38** of 105 |
   | greek print | 48 | 12 → **33** | 39 → **75** of 94 |
   | thai print | 44 | 12 → **17** | 14 → **20** of 49 |
   | devanagari print | 43 | 1 → **3** | 56 → **94** of 170 |
   | hangul print | 40 | 9 → **17** | 43 → **76** of 118 |
   | hebrew print | 27 | 8 → **12** | 20 → **26** of 47 |
   | **total** | **659** | **133 → 227** | **545 → 818** of 1355 |

   Every table improved and none got worse. The ring rotation is the
   small half of that — five letters, o and о and ο and the letters
   built on them — and it only touches a ring that stands alone: the
   first version rotated any closed stroke and broke Р, whose bowl
   closes against the stem, where it starts because of the join and not
   by accident. Stroke *count* is unchanged at 465 of 659 — reordering does not add or remove strokes, and the
   count is what `split_to`/`merge_to` moved in the previous pass
   (393 → 465).

   **What reordering cannot reach**, and the owner's B is the clearest
   case: our B is drawn as *two bowls*, because that is how the
   thinned outline separates, and the taught B is a stem and then the
   bowls. No permutation of two bowls produces a stem. The same goes
   for Devanagari's 3 of 43 — its letters hang from a headline our
   walk draws as part of the body. These are **segmentation** defects,
   not order defects, and they need the walk to cut differently (Tier
   0/2), not the fitter to shuffle.

   The tables also answered which tier each script needs, and the
   answers were not the same. **Cyrillic print** drew too FEW strokes,
   which is Tier 1 — a rule the walk can follow. **Thai** draws too
   MANY, which needed the opposite operation. **Latin cursive** was
   neither: 40 of its 52 letters are one movement and ours managed 14,
   because Dancing Script has no entry or exit sweeps in the outline at
   all — a Tier 2 source-face problem that no walk rule could reach.
   Guessing which was which, rather than measuring, would have wasted
   weeks.

   **A high score is agreement with the table, not with the reader.**
   The owner looked at lowercase print `d`, which the checker passes,
   and said it should be two strokes. He is right and the checker is
   right: the sourced row says one, because Zaner-Bloser teaches the
   bowl, a push back up the stem, and the stem down, all without
   lifting. The model's own note on that row says why — *"to prevent
   b/d reversal"* — which is a reason about five-year-olds writing
   their own language, not about adults learning a foreign one. And a
   retrace cannot be animated: one stroke is one path, so the stem is
   drawn twice.

   That is a defect in the **yardstick**, and no amount of fitting
   reaches it. The fix was a second Latin print run counted by pen
   lifts, with a retrace counted as a lift and a corner not:
   `docs/quality/letterforms/gemini-brief-lifted-print.md`.

   **Runs 1 and 2 landed on 19 Sep**, both from Handwriting Without
   Tears, ingested over the Zaner-Bloser rows with `ingest_rules.py
   --force`. Run 1 was a–z in both cases; run 2 was the 43 accented
   letters, which closes the one hole left in any table — 56 accented
   print rules had been lost before they reached disk weeks earlier
   and were never re-requested. The Latin print table went from 74
   rows to **138**.

   `d` is now two strokes, stem then bowl (the owner's ruling; the
   model recorded the sources' own bowl-first order in `disagreement`,
   so the departure is on the record). `o` and uppercase `L` held at
   one stroke, which is the check that the retrace rule was understood
   and not applied to every corner.

   | latin print | before | after |
   |---|---|---|
   | letters with a sourced rule | 73 | **133** |
   | every stroke right | 47 | **105** |
   | strokes right | 112 of 138 | **297 of 332** |
   | stroke count agrees | 62 | **129** |

   Across all ten tables: **285 of 719 letters** with every stroke
   right, 1003 of 1549 strokes. Latin print alone is now better than
   the other nine tables put together, which says plainly what the
   others are waiting for: a table counted by pen lifts rather than by
   whatever convention its source happened to use.

   One letter changed target rather than improving: `k` is three
   strokes in Zaner-Bloser and two in HWT, which the old table's own
   `disagreement` note had already flagged. Our walk draws three, so it
   now disagrees with the table where it used to agree. That is the
   honest cost of changing source and it is one letter.

   Five sourced letters are not in the library and are allow-listed in
   the gate with a reason: Turkish `İ` (the casing bug in `DEBT.md`),
   and `å`/`ý`, which no course teaches yet — the brief asked for every
   accented letter a Latin course might want, which is a superset of
   what the courses carry today.

   **The score is now a test.** `TestAgainstTheSourcedRules` in
   `backend/tests/test_strokes.py` runs the checker over all ten tables
   on every CI run and fails below the numbers above. It is a ratchet:
   a change that lifts a score lifts the floor with it in the same pull
   request; a change that drops one is a regression to explain, not a
   floor to lower. That is the owner's "use something to check each
   letter each time", and it is Tier 4 arriving through the back door
   — the sourced rule turned out to be a sharper gate than any of the
   geometric invariants Tier 4 originally listed.

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
   the four ways at one pixel and cannot pair the opposite arms.
   **This is the f the owner found on 18 Sep. Fixed 19 Sep**, and not by
   collapsing the cluster: `arms()` counts the limbs on a small ring drawn
   *around* the junction, where a circle cuts each limb exactly once, and
   measures each limb's direction over a long run rather than over the two
   pixels nearest the cluster. One distance could not do both jobs — with
   a single radius, 4 px split the f correctly and left the t turning
   along its crossbar, and 12 px did the reverse. The incoming direction
   needed the same treatment: read over one pixel it pointed down-*left*
   on the f's still-curving hook, which was enough for `crossing()` to
   conclude the pen was already on the bar.

   Two things fell out of it that were worse than the f and had been
   shipping unnoticed. Greek φ and Cyrillic Ф came out as **one stroke —
   the bare stem, with the bowl not drawn at all**; they are now the stem
   and the bowl. And a stroke crossed by an earlier one was cut in two,
   because the pixels just past the junction touch that stroke and the
   walk rejects them as a thinning artefact — the ж lost its stem that
   way. `runs_on()` re-joins those: `chain()` keeps its 3.5 px
   no-questions-asked tolerance and gains a wider one, allowed only when
   the pen is still heading the same way across the gap.
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

**Tier 1 is begun (19 Sep): the generator reads the table.** `split_to`
in `gen_from_fonts.py` cuts a letter at its sharpest turns until it has
the number of strokes its sourced row says, and `TAUGHT` loads every
`rules/*.jsonl` at import. What forced it was Cyrillic print, which
measured 9/32 on stroke count — the worst of any script — and whose gap
had only one shape: **we drew fewer strokes than taught for 21 of the 32
letters and more for only two.** Sixteen of ours were a single stroke
where the taught model uses five. и is a stem, a diagonal and a stem;
thinning joins them into one connected skeleton and the walk runs
straight through. That is not a font's fault, so no face swap could have
fixed it.

Three guards keep it honest. It only ever **adds** strokes, never
merges. It only runs for a letter that **has a sourced row** — everything
else is drawn exactly as before. And it **stops short of cutting a smooth
curve** to reach a number: о stays one stroke, and a letter that runs out
of corners keeps what it has and shows up in the checker as a
disagreement, which is the truthful answer rather than a flattering one.

### Tier 2 — Better source faces (1 PR per script, needs a font choice)

Where a face is wrong for teaching, swap it. Each entry is a candidate
already OFL-licensed; the work is to add it to `FONTS`, regenerate, and
compare sheets side by side.

| Script | Today | Candidate | Why |
|---|---|---|---|
| Thai | Noto Sans Thai **Looped** | — | done (18 Sep); loopless heads were unwritable |
| Russian cursive | Marck Script | **none found** | measured 19 Sep; no OFL candidate beat it — see below |
| Hebrew | Noto Sans Hebrew (print) | an OFL cursive Hebrew | Israeli handwriting is a different alphabet; **none chosen** |
| Greek | Noto Sans | a Greek handwriting face | handwritten θ ζ ξ differ from print |
| Latin cursive | **Edu NSW ACT Foundation**, Dancing Script for the accented letters | — | done (19 Sep); chosen by measurement, see below |
| Devanagari | Noto Sans Devanagari | — | acceptable; the headline was the issue |
| Hangul | Noto Sans KR | — | acceptable; jamo are geometric |

**Why Russian cursive was NOT reswapped (19 Sep).** The same exercise,
against the 66-letter propisi table, and it came back the other way:

| face | count | start | end | in one stroke |
|---|---|---|---|---|
| **Marck Script (kept)** | **28/66** | 35/66 | **28/66** | 15 |
| Caveat | 26/66 | 32/66 | 24/66 | **24** |
| Bad Script | 25/66 | 35/66 | 21/66 | 13 |
| Neucha | 23/66 | 35/66 | 26/66 | 24 |
| Pangolin | 20/66 | **38/66** | 28/66 | 21 |

Nothing beat the incumbent. Caveat and Neucha write more letters in one
movement (24 against Marck's 15, where the table says 41), but agree
with the taught stroke count *less* often overall — they over-merge the
letters that genuinely do lift. Pangolin starts in the right place most
often and is worst on count. The columns disagree, which is exactly what
Latin's did not do: there, one face won every column at once (19→32 on
count and 14→31 on one-stroke), and that is what made the swap obvious.

So the library keeps Marck Script, and the entry in this table changes
from "swap it" to "nothing on Google Fonts is a propisi model". They are
all display or casual scripts. The remedy is a face from outside that
catalogue, or drawing one; it is in `DEBT.md`. **Ambiguous evidence is a
reason not to churn a library, not a reason to pick the nearest thing.**

**How the Latin cursive face was chosen (19 Sep).** Not by eye: seven
OFL candidates were rendered, walked and scored against the sourced
Zaner-Bloser table, which is what the rules table makes possible.

| face | count | start | end | in one stroke |
|---|---|---|---|---|
| **Edu NSW ACT Foundation** | **32/52** | **27/52** | 23/52 | **31** |
| Edu SA Beginner | 32/52 | 22/52 | **27/52** | 29 |
| Caveat | 31/52 | 21/52 | 26/52 | 26 |
| Edu QLD Beginner | 29/52 | 25/52 | 19/52 | 25 |
| Edu AU VIC WA NT Pre | 28/52 | 21/52 | 24/52 | 26 |
| Edu TAS Beginner | 27/52 | 24/52 | 23/52 | 24 |
| Edu VIC WA NT Beginner | 27/52 | 20/52 | 23/52 | 24 |
| *Dancing Script (was)* | *19/52* | *26/52* | *20/52* | *14* |

The Edu faces are Australian state school handwriting models — literally
what a teacher hands out, which is what the brief asks a source to be.
Edu NSW ACT Foundation and Edu SA Beginner tie on stroke count; NSW wins
the column that matters, since the taught table says **40 of the 52
letters are one stroke** and NSW writes 31 of them that way against SA's
29 and Dancing Script's 14. SA wins on where the first stroke ends,
which is the reason to keep it in mind if NSW disappoints on the sheet.

The cost is coverage: the Edu faces carry 126 code points — a-z, A-Z and
punctuation, no accented letters at all — against Dancing Script's 559.
So `FONTS` now holds a **chain** for Latin cursive and each glyph is
drawn by the first face that has it: a-z from the teaching hand, á ñ ü ç
from Dancing Script, rather than French and Spanish losing their cursive
templates. The two faces do not share an x-height, so the seam is real;
it is in `DEBT.md`.

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

**Begun 19 Sep:** the first table is in
(`scripts/strokes/rules/latin-print.jsonl`, 57 of ~150 Latin print rows,
Zaner-Bloser) and `scripts/strokes/check_rules.py` measures the library
against it. It is a *report*, not yet an input to generation: the
generator does not read the table, so a rule cannot yet force a split or
a start. Making it an input is the rest of Tier 1.

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

**Landed 19 Sep, by a different route than planned.** The geometric
invariants above are still worth having, but the gate that shipped is
`TestAgainstTheSourcedRules` in `backend/tests/test_strokes.py`: it
scores every letter of all ten rules tables on every CI run, every
stroke, and fails below a recorded floor per table. A sourced rule
turned out to be a far sharper instrument than "stroke count within the
script median ± 2" — it catches a letter drawn backwards, which no
invariant about counts or closure can see. Raising a floor is part of
the change that earns it; lowering one needs a sentence saying why.

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
