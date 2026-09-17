# Arabic register programme — making every Arabic item MSA (17 Sep 2026)

For the reviewers, the fix write-ups, and whoever runs the passes. The
complaint is old and repeated: learners meet dialect where the course
promises Modern Standard Arabic. The prompts are now pinned (PR #473), so
new content is asked for MSA; **this document is about the content that
already exists**, and about the local model that will read all of it,
because the instruments we have cannot.

**Status (17 Sep 2026).** Steps 1–3 and 6 are built and the judge is
calibrated: `docs/quality/ar-register-2026-09-17.md`. Step 4 onward waits on
reviewers filling `data/eval/ar_register_gold.tsv`. Two items in §8 below now
have an answer the document did not anticipate — see §4 of the results page:
the §1.4 ban on energic forms contradicts grammar point 37, and a C2 drill is
Qurʾān 1:5 verbatim.

The standard is one sentence: **the course teaches Modern Standard Arabic
(الفصحى); Egyptian, Levantine, Gulf, Iraqi and Maghrebi forms, and
Classical forms MSA no longer uses productively, are out of scope in
every learner-facing field; dialect belongs only in a labelled culture
note** (`docs/quality/ar.md`, first paragraph). Everything below is how
to find what breaks that sentence and how to fix it without breaking
anything else.

---

## 1. What "not MSA" looks like — the reviewer's eye

A reviewer needs to recognise four things. Each is listed with its tells
and with what is *not* a tell, because the false alarms have cost more
than the misses so far.

### 1.1 Dialect lexemes
Words MSA does not have. The high-frequency function words are the bulk:

| Dialect | Tell words | MSA |
|---|---|---|
| Egyptian | عايز/عاوز, مش, فين, إيه, إزاي, إزيك, دلوقتي, كده, علشان/عشان, ده/دي/دول, بتاع, برضو, لسه, أوي, يلا, بكرة, ماشي, خلاص (as "OK") | أريد, ليس/لا, أين, ماذا, كيف, كيف حالك, الآن, هكذا, لأن, هذا/هذه/هؤلاء, ملك/الخاص بـ, أيضًا, ما زال, جدًا, هيا, غدًا, حسنًا, انتهى |
| Levantine | بدي/بدك, شو, ليش, وين, هيك, هاد/هاي/هدول, منيح, كتير, هلق, لسا, عم (progressive), كمان, معلش, كيفك | أريد, ماذا, لماذا, أين, هكذا, هذا/هذه/هؤلاء, جيد, كثيرًا, الآن, ما زال, (bare imperfect), أيضًا, لا بأس, كيف حالك |
| Gulf / Iraqi | شلون, وش/وشو, شنو, ماكو/أكو, مو, الحين, توه, زين, عيل, هسه, دحين, يعطيك العافية | كيف, ماذا, ماذا, لا يوجد/يوجد, ليس, الآن, للتو, جيد, إذن, الآن, شكرًا / بارك الله فيك |
| Maghrebi | واش, بزاف, غادي, كاين, علاش, دابا | هل, كثيرًا, سـ/سوف, يوجد, لماذا, الآن |

**Not tells** (the tripwire's false alarms, all verified in the corpus):
هو (he), عم (uncle), عمال (workers), دول (states), بدون, شكرًا, تمام,
مين (harbours, in the frequency list), كمان (violin), زي (a verbal
noun), بين الحين والآخر (an MSA idiom containing الحين), الموظفين (contains
فين), خلّص (form II "to rescue"). A word is a tell only **as a whole word
in its dialect sense**. The judge reads the sentence; a grep cannot.

### 1.2 Dialect morphology
The one that lists never catch: MSA words in dialect grammar.
- **b-imperfect** (بيكتب, بتروح) and **ha-/h- future** (هيروح, حيروح) —
  MSA has no such prefixes; the bare imperfect and سـ/سوف do the work.
  *Not a tell:* بـ + noun (بالسيارة, بنفسك, بيتها) — every one of the
  1,212 prefix matches in the sentence bank was one of these.
- **Negation** مش / ما…ش (ما عرفتش), **demonstrative after the noun**
  (الكتاب ده), **question word at the end** (رايح فين؟), **عم / قاعد /
  بـ progressives**, **the dual and the case endings dropped where MSA
  writes them** (only where the drill's point is the ending).
- **Pronunciation spelled**: ث→ت, ذ→د/ز, ق→ء/ك/g (كلب for قلب is a
  spelling error; آلب for قلب is Egyptian), ج→ g in transliteration.

### 1.3 Dialect orthography that is not dialect
These are *coached, not failed*, and must not be counted as register:
word-final ى/ي, ة/ه, hamza seats (أ/إ/ا), tashkeel presence, Arabic-Indic
digits. The grader already folds them (`docs/quality/ar.md`, §3–4). A
reviewer who "fixes" these is making a spelling edit, not a register one,
and should say so.

### 1.4 Classical and archaic
Forms MSA no longer uses productively: energic and jussive-with-ن forms,
Qurʾanic vocabulary in everyday sentences, the dual in speech contexts
where MSA press would not, حرف نداء archaisms. Rarer; comes from
dictionary dumps and from models "sounding formal". The fix is the plain
MSA press register, not a more colloquial one.

### 1.5 What MSA variation is allowed
Pan-Arab MSA has regional *lexical* preferences that are all MSA: سيارة
everywhere; هاتف/جوال/موبايل (all attested in MSA press — prefer هاتف);
مدرِّس/معلِّم; الآن/حاليًا. Loanwords MSA press uses (إنترنت, كمبيوتر,
تلفزيون) are fine. Neither should be "fixed" to a single regional MSA.

---

## 2. Where the Arabic content lives, and what we know

| Store | Rows | What is learner-facing | Known register state |
|---|---|---|---|
| `data/ar_sentences.tsv` | 13,025 | sentence, translation | 3 confirmed defects (بكرة, وانتا/سنه, a colloquial greeting); a hand check of the widened tripwire finds under twenty genuine dialect rows among 424 word hits — the rest are هو/عم/دول-type false alarms |
| `data/ar_frequency.tsv` (+ `gloss_overrides.tsv`, `ar_seed.json`) | 8,901 | word, POS, English gloss | dialect **entries** glossed as their rare MSA homograph: مش "to suck the marrow", وين "black grape", مو "baldmoney", plus يلا "come on" — the frequency list is a corpus count and counts dialect; these must be retired (`vocab_exclusions.tsv`), not glossed |
| `data/grammar/ar_grammar.json` | 40 points, 274 drills | explanation, culture_note, drill sentence/answer/hint/translation | 0 tripwire hits; unmeasured by a reader |
| `data/ar_morphology.json` | 6,869 | inflection charts | MSA by construction; check the *labels* and any dialect paradigm rows |
| `data/ar_readings.tsv` | — | transliterations | check for dialect pronunciations spelled (g for ج, ʔ for ق) |
| **DB: `example_sentences` (harvested / generated)** | live | sentence, translation | accepted by the unpinned checker until 17 Sep — **the biggest unknown**; not in any file |
| **DB: `vocabulary` + `translations`** | live | definitions in every locale | when Arabic is the *support* locale, definitions were written by unpinned translators |
| **DB: Speak / tutor / Reader outputs** | live logs | what learners saw | past outputs are what people noticed; nothing to fix retroactively, the pin fixes the future; the judge in shadow measures whether it did |

The tripwire (`ar_register`, 18 words) stays as a tripwire. The measurement
above is why it cannot be the instrument: **whole-word lists have a
precision under 5% on this corpus and a recall nobody has measured.**

---

## 3. The instrument: a local Arabic-native judge over every row

One model, one question, every row: *Is this Modern Standard Arabic? If
not, which words, which variety, and what is the MSA that keeps the
meaning?* Run locally so that every row can be read (the sentence bank
alone is 13k rows; with the live tables and the locales it is tens of
thousands), and run on an **Arabic-native** model so the judge is
independent of the makers (the same family should not grade its own
register). Model choice and serving are in
`docs/plans/arabic-msa-local-llm.md` §3 and §5 — Falcon-H1-Arabic-7B or
Jais-2-8B behind vLLM's OpenAI-compatible endpoint; the pass script takes
a `--base-url` and needs nothing else from the app until the provider
seam exists. **Until the local endpoint is up, the same script runs on
Claude with the pinned prompt**; the passes can start this week and the
local model takes over the volume when it arrives.

### 3.1 The verdict
```json
{"i": 12, "verdict": "dialect" | "classical" | "msa" | "unsure",
 "variety": "egyptian" | "levantine" | "gulf" | "iraqi" | "maghrebi" | "mixed" | null,
 "evidence": ["بكرة", "وانتا"],
 "kind": "lexeme" | "morphology" | "orthography_only" | "archaic" | null,
 "msa": "ستُلقي خطابًا غدًا، أليس كذلك؟",
 "meaning_kept": true, "confidence": 0.93, "note": "بكرة → غدًا; ستقلي is a typo for ستُلقي"}
```
Rules the judge is given, verbatim from §1: the tells, the non-tells, the
orthography-only class (never `dialect`), the allowed MSA variation, and
"rewrite the minimum: keep every MSA word, replace only the evidence,
keep the meaning and the level". `unsure` is a legal answer and routes to
a human. The register line from `quality_rules.register_line("ar")` is in
the system prompt too, so the judge and the makers hold the same standard.

### 3.2 Calibration before trust
Before any verdict changes a row, **reviewers label a gold set**: 200
sentences (100 the tripwire flagged, 100 random), 100 vocabulary entries
(the 50 rarest-sense glosses plus 50 random), all 274 drills, and the 40
explanations — with the §1 categories. The judge runs on the same set.
Gates: agreement on `dialect` vs `msa` ≥ 95%; every genuine dialect row
in the gold set caught (recall on the labelled positives = 100%, since
they are few and known); `orthography_only` never filed as `dialect`.
Below the gate, the prompt is fixed and the set re-run; the judge does
not touch production before it passes. The gold set is committed
(`data/eval/ar_register_gold.tsv`) and re-used for every model change.

### 3.3 Two judges disagreeing is a queue item, not a coin toss
On the live tables, run the local judge and the pinned Claude checker
both. Agreement `dialect` → fix queue with the rewrite. Disagreement or
`unsure` from either → review queue with both opinions. Agreement `msa`
→ done, logged. This is the maker–checker rule the programme already
runs everywhere else (never self-certify), applied to register.

---

## 4. Per content type: what to check, how to fix

### 4.1 Sentences (`ar_sentences.tsv`, `example_sentences`)
- **Check:** the sentence for §1.1–1.4; the translation for a meaning
  the MSA rewrite must keep; the *word* column — a dialect sentence often
  sits under an MSA headword it does not actually contain in MSA.
- **Fix:** rewrite to MSA keeping the meaning and the headword's surface
  form (the card blanks the surface form — `apply_authored_sentences.py`
  refuses a row it cannot blank, and so must this pass). If the meaning
  only exists in dialect (a greeting formula, a proverb), **retire the
  row** rather than invent an MSA sentence nobody says.
- **Never** fix spelling-only rows under this pass (log them for the
  spelling pass); never change level or length.

### 4.2 Vocabulary (`ar_frequency.tsv`, glosses, `vocabulary`)
- **Check:** is the *word* a dialect lexeme? (retire); is the *gloss* a
  rare MSA homograph of a dialect word the corpus counted? (retire — the
  frequency is dialect frequency); is the gloss itself written in dialect
  when Arabic is the support locale? (rewrite); does the POS fit MSA?
- **Fix:** dialect headwords go into `data/vocab_exclusions.tsv` with the
  reason `dialect` — a retired word keeps every learner's card and history
  and stops being drawn (`refeed.md`, step 3). Gloss fixes go into
  `gloss_overrides.tsv` (the override file outranks the seed —
  `docs/quality/ar.md`, 7 Sep). Nothing is deleted.

### 4.3 Grammar drills (`ar_grammar.json` drills)
- **Check:** sentence and answer for §1; the **hint** must not be a
  dialect gloss (`want (عايز)` is the documented bad case); the answer
  must be the MSA form the point teaches, with case endings where the
  point is about them.
- **Fix:** rewrite in place in the JSON through the Workshop's drill
  editor (the learner-view preview shows what the card will render), or
  in the file with `apply_drill_hints.py` / the grammar apply scripts;
  the semantic checker re-runs on the point after.

### 4.4 Grammar explanations and culture notes
- **Check:** explanations describe MSA grammar; a dialect comparison is
  allowed only when labelled ("in Egyptian this is …") and only in
  `culture_note`; transliterations in the explanation follow MSA
  pronunciation (q for ق, j for ج, th for ث).
- **Fix:** `apply_grammar_explanations.py`; a relabelled comparison moves
  to the culture note rather than being deleted — that is the one place
  dialect is welcome, and learners have asked for it.

### 4.5 Readings, morphology charts, transliteration
- **Check:** readings spell MSA (no g, no ʔ for ق, no dropped ث); chart
  rows are MSA paradigms (no b-imperfect rows, no dialect plurals) and
  labels are the textbook's.
- **Fix:** in the files; the chart generator is pinned now, so
  regeneration of a bad chart is a re-run.

### 4.6 The support-locale side
Definitions and UI translations *into* Arabic (for Arabic-speaking
learners of other languages) get the same judge with the same schema.
The fix path is `translation_reviews`, which already exists for exactly
this kind of definition review.

---

## 5. The pipeline, step by step

| Step | What | Output | Who |
|---|---|---|---|
| 1 | **Gold set** (§3.2): 200 + 100 + 274 + 40 items labelled by reviewers with the §1 categories. | `data/eval/ar_register_gold.tsv` | reviewers (Arabic speakers), 1–2 days |
| 2 | **The pass script** `backend/services/quality/register_pass.py`: reads a store (`--store sentences|vocab|grammar|db-sentences|db-locale`), batches 20 rows, asks the judge (`--base-url` for the local endpoint, else the pinned Claude checker), writes `out/ar-register-<stamp>.jsonl` of verdicts and a summary. `--dry-run` default; `--restore FILE`. The shape of `seeder/review_hints.py`. | verdict files, a summary page | the agent, 2 days |
| 3 | **Calibrate**: run step 2 on the gold set; report agreement per category; fix the prompt until the §3.2 gate passes. | `docs/quality/ar-register-<date>.md` | agent + reviewers |
| 4 | **Full pass, files**: sentences, vocabulary, grammar, readings. Every `dialect` with a confident rewrite → a proposed row in `data/ar_register_fixes.tsv` (id, field, before, after, evidence, judge, confidence); every `unsure`/disagreement → the same file marked `review`. | one TSV per store | agent |
| 5 | **Review**: reviewers work the TSV (or the Workshop queue it is loaded into — `card_change_requests` for sentences and vocabulary, `point_review_notes` for grammar) with the checklist in §6: accept, edit, or reject each. Nothing is applied unreviewed. | the TSV with a `decision` column | reviewers |
| 6 | **Apply**: `apply_register_fixes.py` writes accepted sentence rewrites into `ar_sentences.tsv` (through the same blank-ability gate as `apply_authored_sentences.py`), retirements into `vocab_exclusions.tsv`, gloss fixes into `gloss_overrides.tsv`, drill/explanation edits into `ar_grammar.json`; then the owner's refeed sequence (`refeed.md`: snapshot, `seeder.run`, `reconcile --apply`). | committed files + one reconcile | agent prepares, **owner runs** |
| 7 | **Full pass, live tables**: `example_sentences` and the Arabic-locale `translations` through the two-judge rule (§3.3); fixes as change requests. | queue items | agent + reviewers |
| 8 | **Verify**: re-run the judge over everything; the gate is **zero confident `dialect` verdicts** and **zero tripwire hits**; the sentence and drill checkers (pinned) re-run over the Arabic corpus pass at their usual rate. Results page. | `docs/quality/ar-register-<date>.md` | agent |
| 9 | **Keep it fixed**: the judge runs nightly over rows created since its last run (harvest, generation, Speak's replies in shadow); anything `dialect` is queued before a learner sees it. | a staff-bell item | agent, after the provider seam |

Steps 1–3 can start now on Claude; steps 4–9 want the local endpoint for
volume and cost, but do not wait on it.

---

## 6. The reviewer's checklist and the fix write-up

For each item, answer in order; stop at the first "no".

1. **Is it Arabic script, complete, and the item the id says?** (no →
   `broken`, not a register item)
2. **Is every word an MSA word in its MSA sense?** Check the evidence
   words against §1.1 *and* the non-tells. (no → `dialect`, name the
   words and the variety)
3. **Is the grammar MSA?** b-/ha- prefixes, ش-negation, post-noun
   demonstratives, dialect question order. (no → `dialect`, kind
   `morphology`)
4. **Is the only oddity spelling — ى/ي, ة/ه, hamza, tashkeel?** (yes →
   `orthography_only`; do not touch under this pass)
5. **Is it archaic or Qurʾanic where MSA press would not be?** (yes →
   `classical`)
6. **Does the proposed MSA keep the meaning, the headword's surface form,
   and the level?** (no → edit it until it does, or `retire` if the
   meaning only exists in dialect)
7. **Would a native reader of a newspaper find the rewrite natural?**
   (no → edit; stilted MSA is the second complaint waiting to happen)

**The fix write-up** — one line per item in the fixes TSV, and for a
batch, one paragraph at the top of the results page:

```
id | store | field | verdict | variety | evidence | before | after | meaning_kept | decision | reviewer | note
```
The paragraph says: how many items were read, how many were `dialect`,
`classical`, `orthography_only`, `unsure`; how many rewrites were
accepted, edited, rejected, retired; the three commonest evidence words;
and anything the judge got systematically wrong (that is a prompt fix,
recorded in §3 next time). That paragraph is what goes to the people who
noted the problem: read N, found M, fixed M, here is how we know.

---

## 7. What this does not do, said plainly

- It does not make MSA sound like conversation. A learner who wants to
  *speak* Egyptian is in the wrong course; the culture notes can say so
  and point at the register difference. A dialect track is a separate
  product decision, not a register fix.
- It does not fix spelling, gender marking, hint leaks, or trivial
  sentences — those have their own passes (`docs/quality/ar.md`); a row
  found by this pass with those faults is logged for them, not fixed
  here, so that one review answers one question.
- It does not run production writes from the agent. Every apply is a
  file change and a reconcile the owner runs (`refeed.md`).

---

## 8. Decisions for the owner

1. **Who reviews.** Two Arabic speakers is the minimum for the gold set
   and the queues (disagreement is data); the Workshop's language roles
   already gate who can see the queues.
2. **Retire or rewrite dialect-only meanings** (greetings, proverbs) —
   the doc says retire; say if you want authored MSA replacements instead.
3. **Regional MSA preferences** — §1.5 says leave them; say if the course
   should prefer one (e.g. هاتف over جوال).
4. **The local endpoint** — steps 1–3 need nothing; steps 4–9 are cheaper
   and faster with it (`arabic-msa-local-llm.md` §5).
5. **Culture notes as the dialect home** — only 2 of 40 points have one;
   the relabelled comparisons will want a few more. Say if reviewers may
   write them.
