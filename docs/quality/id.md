# Indonesian (id) — Content Quality Standards

## Language profile

Latin script, left-to-right, no diacritics of its own. **The authoritative variety is
bahasa Indonesia baku** — standard Indonesian as codified for school and print, the register
of news and formal speech. **Explicitly out of scope:** Malaysian Malay (`bahasa Melayu`, a
different standard), the surrounding regional languages (Javanese, Sundanese, Minang), and
Jakarta colloquial / `bahasa gaul` as a *production* target below C1 — it appears at C1–C2
for recognition and register switching (point 35 drills `Gue` and `Lu`; point 38 keeps `Lu`
and `Udah` inside quoted dialogue while the narration stays baku) and nowhere else.

**No gender, no noun class, no number agreement, no verb conjugation.** Point 1 is literally
"Verbs don't conjugate": `mau` is want/wants/wanted for every subject. Nothing is marked on
the noun, so all drill difficulty sits in three places:

1. **Affix morphophonology** — meN-, ber-, di-, peN-, ter-, memper-, -kan, -i, ke-…-an,
   per-…-an, se-. The nasal changes are the teachable part (`tulis → penulis`,
   `kerja → pekerja`, `ajar → pengajar`), so a hint giving *root + affix* does real work while
   one printing the derived form does none.
2. **Function words as answers** — `apakah`, `ada`, `yang`, `di/ke/dari`,
   `bisa/boleh/harus/mau`, `sedang/masih/pernah/baru`, `bahwa`, `-lah/-kah/-pun`:
   closed-class items whose meaning *is* their name, which is why the `answer — explanation`
   template wrecked those points and left the affix points comparatively clean.
3. **Reduplication and register** — `buku-buku`, `anak-anak` carry a hyphen the grader does
   not forgive; baku vs. Jakarta speech decides the C1–C2 answers.

Grading: `IndonesianNLP` in `backend/services/nlp/latin_base.py` is `AccentFoldingNLP` with
`leading_articles = ()` — nothing to strip, effectively no diacritics to fold, so acceptance
is **exact match after lowercasing**: `buku buku` for `buku-buku` grades WRONG. Not in
`TRANSLIT_LANGS`.

## Hint standards

Universal rules, once: a hint **narrows** the answer without containing it. Never the answer
as a whole word. Never a gloss already sitting in the drill's own translation. Never the
`answer — explanation` template. One hint resolves to exactly one answer inside its point
(allomorph sets excepted where the sentence disambiguates). Hints are English; quoting a
base form (`baca`, `peN-`) is fine, a whole Indonesian sentence is not.

### The rewrite rule — never open a hint with the answer

49 of 152 Indonesian drills do exactly that. The repair is mechanical: (1) delete the leading
`answer —`; (2) read what remains as if you did not know the word — if it still tells the
learner *which* item to reach for, you are done, and 23 of the 49 pass on this step alone;
(3) if what remains is a bare label with nothing to choose between (`'there is'`, `ability`),
add the condition **this sentence** imposes — contrast with the point's other answers,
position, register, or the negation pair. 26 of the 49 need step 3.

| BAD (in the file today) | GOOD (rewrite) |
| --- | --- |
| `apakah — marks a yes/no question, placed at the very front` | `the formal yes/no question word, sentence-initial` |
| `ada — 'there is'` | `the existence word — not the possession verb punya` |
| `orang — the classifier for people` | `the classifier for people` |
| `kapan` (answer `Kapan`) | `the question word for time` |
| `bisa — ability` | `ability, not permission (boleh) or obligation (harus)` |

A bare grammar label survives step 3 **only** when it uniquely picks one answer inside the
point — `static location` / `motion toward` / `origin` in the `di/ke/dari` point does, and
so does `physically present` in the `ada` point, where every answer is `ada`.

### Indonesian-specific rules

**Affix drills: give root + affix, never the derived form.** The derivation is the answer.
GOOD (real): `tulis + peN- → pen-, t drops` for `penulis`; `baca + di- — the object leads`
for `dibaca`. BAD (real): `books — double the word: buku becomes buku-buku` for `buku-buku`
→ rewrite as `plural — reduplicate the root, joined by a hyphen`.

**Bound affixes: describe the job, don't spell the affix.** The `-lah/-kah/-pun` point stores
answers without the hyphen (`lah`) while the hint writes `-lah` — still a whole-word leak.
BAD (real): `-kah — formal yes/no question`. GOOD: `the formal question clitic, attached to
the questioned word`.

**Never quote the construction containing the answer** (7 hints do). BAD (real):
`yang + a clause`; `paling + adjective`. GOOD: `the relativiser that hangs the following
clause on the noun`; `the superlative marker before the adjective`.

**Closed-class contrast points name the axis, not the word.** GOOD (real): `not — negates the
noun/identity, not tidak` for `bukan`; `we, excluding the listener` for `kami`. BAD (real):
`tidak bisa` for `bisa` — prints the answer, names no axis.

## Question / drill standards

- Natural, current baku Indonesian: the di- point's first drill, filled, reads `Buku itu dibaca oleh ribuan orang.` — right; sentences that exist only to host an affix are not.
- **Exactly one blank** — all 152 drills satisfy this today; keep it that way. One unambiguous answer: if a second word fits the frame and the translation equally, tighten the sentence, not the hint.
- Where the blank is a bound affix glued to its host (`Dia{{answer}} yang bertanggung jawab.`), `answer` must be exactly the characters that fill the gap (`lah`, no hyphen); conversely, never drop the hyphen from a reduplicated free form (`buku-buku`).
- The translation translates the whole sentence including the register cue — `Would you like to eat? (formal/polite)` earns its parenthetical because the drill chooses `anda` over `kamu`.
- Pitfalls: the di- passive is *neutral* Indonesian, so its English must read naturally, not stiffly; C2 lexicalised affixation (`mengerti`, `berhasil`, `pengaruh`) must not be hinted as decomposable — that is the point; headline style (point 40) legitimately drops words, so the translation carries what was recovered.

## Translation & definition standards

- No bare one-word gloss for a polysemous item. `data/id_frequency.tsv` mostly gets this right — `tahu → to know (a fact)`, `bilang → to say; to tell (informal)`, `pulang → to go home; to return` — but 65 of its 90 rows carry no sense split at all (no `;`, no parenthetical), acceptable only where the word really has one everyday sense.
- No gender or noun class to mark; instead note the **classifier** where it is not predictable (`orang` people, `ekor` animals, `buah` objects).
- Register is marked in both directions: `bilang` informal beside `mengatakan`; `lu`/`udah` labelled Jakarta colloquial wherever they appear. One register per drill — baku sentence, plain complete English; dialogue sentence, colloquial English.

## Current measured state

Counted directly from `data/grammar/id_grammar.json` — 40 points, 152 drills, every point
`source: "ai"` and `reviewed: false`; no `id_morphology.json`, no `id_sentences.tsv`,
`data/id_frequency.tsv` has 90 entries, gym baseline present.

| Rule | Count | Share of drills |
| --- | --- | --- |
| `leak_hard` — answer whole-word in its own hint | **72** | 47% |
| ├ `self_answering` — the `answer — explanation` template | **49** | 32% |
| ├ construction quote (`yang + a clause`) | 7 | 5% |
| ├ hint == answer exactly | 2 | 1% |
| └ other whole-word leaks | 14 | 9% |
| `giveaway_by_gloss` / `duplicate_hint` / empty fields | 0 | — |

**16 of 40 points leak in every drill**: `Plural by reduplication`, `apakah`, `Classifiers`,
`ada`, `Question words`, `Modality`, `Place prepositions`, `Aspect markers`, `yang`,
`Purpose`, `Conditionals`, `Reported speech with bahwa`, `Discourse particles`, `Formal
connectors`, `Affix pairs that shift meaning`, `Lexicalised affixation`. 19 points are clean —
every other A1 point plus the meN-/ber-/di-/peN- affix points — so the template hit
*function-word* points, not the file as a whole. Worst offenders, quoted verbatim:
`apakah — marks a yes/no question, placed at the very front` (answer `apakah`, A1); `kapan`
(answer `Kapan`, A2 — the hint is the answer, lowercased); `books — double the word: buku
becomes buku-buku` (answer `buku-buku`, A1 — not the template; it spells the answer out at
the end instead).

**Correction to the crawl:** its rule text says the `answer — explanation` pattern "accounts
for 72/152 id and 86/152 tl drills". In the file the template accounts for **49/152** here;
72 is the total of *all* leak classes. `data/quality/baseline.json` already records the split
correctly (`id.leak_hard: 72`, `id.self_answering: 49`), so the prose is what is off.

## Testing checklist

```bash
python -m backend.services.quality.audit_content --language id
.venv/bin/pytest backend/tests/test_nlp_latin.py -q -k Indonesian
.venv/bin/pytest backend/tests/test_content_quality.py -q
```

There is no `test_nlp_indonesian.py` — Indonesian grading lives in `TestIndonesian` inside
`backend/tests/test_nlp_latin.py`. Indonesian is not in `TRANSLIT_LANGS`, so the
transliteration suite does not apply.

A human reviewer pulls 10 random drills and rejects any that: open the hint with the answer or
contain it as a whole word (start with the 16 fully-leaking points — today the whole sample
fails there); hint an affix drill with the derived form instead of `root + affix`; carry a
hint that fits two answers inside one point (`ability` alone among `bisa/boleh/harus/mau`);
reduplicate without the hyphen in `answer`, or put a hyphen into a bound-affix answer; mix
registers, or show `lu`/`udah` without a register label outside the C1–C2 points; or drop a
formality or inclusivity distinction the drill is testing (`anda` vs `kamu`, `kita` vs
`kami`) from the translation.
