# Tagalog (tl) — Content Quality Standards

## Language profile

Latin script (the modern 28-letter Filipino alphabet), left-to-right, no diacritics in
ordinary writing — dictionary stress marks (pagkáin) are folded away by the grader and must
never carry meaning in a drill. **The authoritative variety is Manila-based Tagalog as
standardised in Filipino**, in the everyday polite register that uses `po`/`ho`.
**Explicitly out of scope:** the other Philippine languages (Cebuano, Ilocano, Hiligaynon),
regional Tagalog dialects (Batangas, Marinduque), Spanish-era orthography, and Baybayin
script. Taglish and "malalim" (deep/literary) Tagalog are in scope only where the path says
so — the C1 register point and the C2 code-switching point, where Taglish is drilled as
production (`Nag-aral ako ng math kanina`, `I-check mo ang email mo.`).

**No gender anywhere** — one pronoun `siya` for he/she, no agreement on adjectives. What
replaces noun class is the **case-marker + focus system**, and it is where nearly all drill
quality is won or lost:

1. **Markers as answers.** `ang` / `ng` / `sa` (and `si` / `ni` / `kay` for names) are two- and
   three-letter particles that *are* the syllabus for eight of the forty points. Their whole
   meaning is their identity, so the `answer — explanation` template destroys them outright:
   `ang — marks the actor as the topic` teaches nothing the blank didn't already need.
2. **Focus + aspect morphology.** `-um-`, `mag-`, `-in`, `-an`, `i-`, `ma-/maka-`,
   `magpa-/pa-…-in`, with three aspects built by infixation and CV-reduplication
   (`kumain / kumakain / kakain`; `basa + -in → binasa`). Hints give *root + affix + aspect
   cell* and stop before the surface form.
3. **The linker `na`/`-ng`**, conditioned by the final sound of the previous word. Drills glue
   the blank onto the host (`Ang tao{{answer}} kumain ay umalis.`), so the answer string and
   the phonological condition both have to be exactly right.

Grading: `TagalogNLP` in `backend/services/nlp/latin_base.py` is `AccentFoldingNLP` with
`leading_articles = ()`, and the code says why — "ang/ng/sa are case-marking particles, not
articles like Spanish 'el' — stripping them would eat a real word". Acceptance is exact match
after lowercasing and accent folding. Not in `TRANSLIT_LANGS`.

## Hint standards

Universal rules, once: a hint **narrows** the answer without containing it. Never the answer
as a whole word. Never a gloss already sitting in the drill's own translation. Never the
`answer — explanation` template. One hint resolves to exactly one answer inside its point
(allomorph sets excepted where the sentence disambiguates). Hints are English; quoting a base
form or an affix (`kain`, `mag-`) is fine, a whole Tagalog sentence is not.

### The rewrite rule — never open a hint with the answer

66 of 152 Tagalog drills do exactly that: the worst rate in the repo. The repair is
mechanical: (1) delete the leading `answer —`; (2) read what remains as if you did not know
the word — if it still tells the learner *which* item to reach for, you are done, and 45 of
the 66 pass on this step alone; (3) if what remains is a bare label with nothing to choose
between (`linker`, `plural marker`), add the condition **this sentence** imposes — the focus
of the verb, the phonological environment, the particle order, or the register.

| BAD (in the file today) | GOOD (rewrite) |
| --- | --- |
| `ang — marks the actor as the topic, since kumain is actor-focus` | `topic marker; kumain is actor-focus, so the eater is the topic` |
| `ng — marks the object, since it isn't the topic here` | `non-topic marker on the thing acted on` |
| `sa — marks the destination` | `the marker for where the motion is headed` |
| `na — linker` | `the standalone linker joining noun and adjective — the written default` |
| `mga — plural marker, placed before the noun` | `the plural marker that goes before the noun` |
| `saan` (answer `Saan`) | `the question word for place` |

A bare grammar label survives step 3 **only** when it uniquely picks one answer inside the
point: `possessor marker` is fine in the `ng` point where every answer is `ng`, but `inclusive
we` and `exclusive possessor` are doing real work in the pronoun points and must stay
contrastive. Rewriting all 66 this way introduces **no** duplicate hints inside any point.

### Tagalog-specific rules

**Focus/aspect drills: root + affix + cell, and stop.** GOOD (real): `sara + -in, completed`
for `Sinara`; `linis + -in, contemplated` for `Lilinisin`; `mag- completed → nag-` for
`Nagbasa`; `-um- incompleted — reduplicated` for `Kumakain`. BAD (real): `kain + -in, completed
→ kinain` and `basa + -in, completed → binasa` — the arrow spells the answer out; delete
everything from the arrow onwards and the hint is already good.

**Marker and particle points name the role, never the marker.** BAD (real): `sa akin —
recipient` for `akin`; `na before ba` for `na`; `ay after a fronted topic` for `ay`; `pa —
still not`. GOOD: `the sa-pronoun for "me" as recipient`; `the "already" particle, which
precedes the question particle`; `the inversion particle that follows a fronted topic`;
`"still/not yet", sitting before the question particle`.

**Taglish points still may not leak.** BAD (real): `i- focus prefix on an English root` for
answer `I`. GOOD: `the focus prefix used for things handed over — here on an English root`.

## Question / drill standards

- Natural Manila Tagalog with a plausible speaker: the enclitic point's drills, filled, read `Kumain na ba kayo?` and `Salamat po.` Avoid frames that only exist to host a particle.
- **Exactly one blank** — all 152 drills satisfy this today; keep it that way. One unambiguous answer: in a marker point the sentence's verb focus must actually force `ang` over `ng`, or the drill is a coin flip.
- The blank is often **inside a word**: `Ang libro{{answer}} binasa ko`, `Nag-{{answer}} na ba kayo?`, `{{answer}}-check mo ang email mo.` The `answer` field must be exactly the characters that fill the gap (`ng`, `meeting`, `I`), and the hint must supply the environment (vowel-final host → `-ng`).
- Capitalisation follows the sentence, not the citation form (`Kumain`, `Nagbasa`); grading lowercases, so this is a presentation rule, not a grading trap.
- Translations must show what the focus system is doing. `Kinain ko ang mansanas.` is glossed `I ate the apple.` — correct English, but a reviewer should confirm the point's explanation carries the "the apple was eaten by me" reading, since object focus is the *unmarked* choice here and the English passive is not.
- Register cues belong in the translation: `Thank you (respectfully).` for the `po` drill, `We (you and I) will go…` for `tayo`.

## Translation & definition standards

- No bare one-word gloss for a polysemous item. `data/tl_frequency.tsv` is mostly careful — `may → there is/are; to have (existential marker)`, `wala → there is not; none; to not have`, `iyan → that (near the listener)` — but 64 of its 90 rows carry no sense split (no `;`, no parenthetical); qualify anything with a second everyday sense (`kasi`, `alam`, `ito`).
- No gender or noun class to mark. What must be marked instead is **marker class and focus**: a verb definition should say which focus it is (`kumain` actor-focus, `kinain` object-focus), and a pronoun definition should say which set it belongs to (ang / ng / sa), because those three sets are not interchangeable.
- Register consistency: `po`/`ho` forms are glossed as polite, Taglish items are labelled Taglish, and literary items (`ani`, `kay` exclamative) are labelled literary so a learner never drops them into ordinary speech.

## Current measured state

Counted directly from `data/grammar/tl_grammar.json` — 40 points, 152 drills, every point
`source: "ai"` and `reviewed: false`; no `tl_morphology.json`, no `tl_sentences.tsv`,
`data/tl_frequency.tsv` has 90 entries, gym baseline present.

| Rule | Count | Share of drills |
| --- | --- | --- |
| `leak_hard` — answer whole-word in its own hint | **86** | 57% |
| ├ `self_answering` — the `answer — explanation` template | **66** | 43% |
| ├ construction/derivation quote (`kain + -in, completed → kinain`) | 9 | 6% |
| ├ hint == answer exactly | 2 | 1% |
| └ other whole-word leaks | 9 | 6% |
| `giveaway_by_gloss` / `duplicate_hint` / empty fields | 0 | — |

**19 of 40 points leak in every drill** — the entire A1 band (`ang`, `ng`, `sa`, `na`, `mga`,
`may/wala`, `hindi`) except the `-um-` point, plus `ang pronouns`, `ng pronouns`, `si/sina`,
`Questions`, `Enclitic particles`, `ay inversion`, `Pseudo-verbs`, `may and mayroon`,
`Deictics`, `Conditionals`, `Aspect subtleties` and `Literary and formal Filipino`. Only 13
points are clean, and they are the affix/focus points (`-um-`, `mag-`, aspect, `-an`, `i-`,
`ma-/maka-`, causatives, numbers) — the template was applied wherever the answer was a
particle. Worst offenders, quoted verbatim: `ang — marks the actor as the topic, since kumain
is actor-focus` (answer `ang`, A1); `na — linker` (answer `na`, A1 — the whole hint is the
answer plus one word); `kain + -in, completed → kinain` (answer `Kinain`, A2 — the derivation
is printed in full).

**Correction to the crawl:** its rule text says the `answer — explanation` pattern "accounts
for 72/152 id and 86/152 tl drills". In the file the template accounts for **66/152** here;
86 is the total of *all* leak classes. `data/quality/baseline.json` records the split
correctly (`tl.leak_hard: 86`, `tl.self_answering: 66`). The crawl also reports "one-word
hints 2"; there are **3** — `saan`, `bakit`, and `mag-...-an` (answer `Nagtulungan`), the last
being affix notation with no spaces rather than a word.

## Testing checklist

```bash
python -m backend.services.quality.audit_content --language tl
.venv/bin/pytest backend/tests/test_nlp_latin.py -q -k Tagalog
.venv/bin/pytest backend/tests/test_content_quality.py -q
```

There is no `test_nlp_tagalog.py` — Tagalog grading lives in `TestTagalog` inside
`backend/tests/test_nlp_latin.py`, including `test_particle_not_stripped`, the regression
guard for `ang bahay` keeping its marker. Not in `TRANSLIT_LANGS`, so no translit suite.

A human reviewer pulls 10 random drills and rejects any that: open the hint with the answer or
contain it as a whole word (any A1 marker point fails on sight today); print the derived form
after an arrow in a focus/aspect hint; hint a marker drill without naming the focus that
forces the choice; give a linker drill no phonological condition; store an in-word blank whose
`answer` doesn't match the characters in the gap; label a Taglish or literary form as ordinary
Tagalog, or an ordinary form as polite; or gloss a pronoun without saying which of the ang/ng/sa
sets it belongs to.
