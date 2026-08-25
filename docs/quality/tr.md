# Turkish (tr) — Content Quality Standards

## Language profile

Latin script (the 1928 alphabet), left-to-right, with six letters English lacks — `ç ğ ı İ ö ş ü` — and the
dotted/dotless `i` pair that makes casing language-specific. **The authoritative variety is the written standard
of Turkey (İstanbul Türkçesi)** as codified by the Türk Dil Kurumu, whose dictionary is cited in the
`references` of the points in `data/grammar/tr_grammar.json`. **Out of scope:** Cypriot and Balkan Turkish;
Azerbaijani and other Turkic languages, however close; Ottoman orthography and the Arabic-script era; regional
morphology (`geliyom`, `gidiyoz`) — mentionable in a culture note, never drilled.

**No grammatical gender and no noun classes at all** — no articles, no agreement. Nothing in a Turkish hint can
leak "which gender", because there is none; the corresponding trap is leaking *which allomorph*.

Three features dominate drill quality:

1. **Vowel harmony.** Almost every suffix has two or four shapes (`-de/-da`, `-ler/-lar`, `-ı/-i/-u/-ü`),
   selected by the last vowel, plus consonant hardening (`-te/-ta` after a voiceless consonant) and softening
   (`kitap → kitabı`). The learner's job is to *compute* the shape; a hint that computes it for them removes the
   entire exercise.
2. **Agglutination.** Answers are whole built-up words (`evdeyim`, `okuldayız`, `buzdolabında`), so the hint
   convention is a stem gloss plus the names of the pieces: `house + locative + 'I am'`.
3. **Definiteness on the object.** `Kitap okuyorum` and `Kitabı okuyorum` are both correct Turkish with
   different meanings, so the English translation is the only thing that can license the accusative.

## Hint standards

A hint narrows the answer without containing it: never the answer as a whole word; never a gloss already
sitting in the drill's own translation; never the `answer — explanation` template; one hint resolves to exactly
one answer inside a point (allomorph sets excepted where the sentence disambiguates); hints are in English, and
quoting a Turkish base form is fine while whole Turkish sentences are not.

1. **The `stem gloss + suffix names` convention is the house style — keep it.** GOOD: `house + locative + 'I am'`
   → `evdeyim`; `fridge + locative (compound noun keeps its -ı)` → `buzdolabında`; `book + accusative (final
   consonant softens)` → `kitabı`. Naming the *process* is teaching; spelling the result would be leaking.
2. **State the harmony rule, never the harmony outcome.** The learner must look at the last vowel themselves.
   GOOD: `question particle — harmonize with the last vowel` → any of `mı/mi/mu/mü`. BAD: `harmony after 'a/ı'`
   → `mı`; `harmony after 'ö/ü'` → `mü`; `school + accusative (back, rounded)` → `okulu`. The bad shape tells
   the learner which vowel class won, which is the whole computation.
3. **One hint mapping to the four harmony variants of one suffix is CORRECT, not a duplicate-hint violation.**
   This is the single legitimate exemption in the file: in *Question particle (mı / mi / mu / mü)* the hint
   `question particle — harmonize with the last vowel` maps to `mı`, `mi`, `mu`, `mü` across four drills, and
   each drill's own sentence (`Bu kitap ▮?`, `O doktor ▮?`, `Bu süt ▮?`, `Onlar öğrenci ▮?`) determines the
   answer uniquely. Any checker must exempt allomorph sets — same suffix skeleton, harmony variants only, with
   the sentence disambiguating — or it will flag good pedagogy. The exemption does **not** cover two genuinely
   different morphemes sharing a hint.
4. **A one-word hint must name a function, not a translation.** GOOD: `existence` → `var`, `non-existence` →
   `yok`. BAD: `for` → `için` under *Do sport for your health.*; `after` → `sonra` under *After work I do
   sport.*; `like` → `gibi` under *A person like an angel.*; `what` → `Ne` under *What are you reading?*
5. **Quoting the gloss in quotation marks does not fix it.** `'with'` → `ile` and `'more'` → `daha` read as
   careful style but are still the English word from the translation.
6. **Capitalisation is not a second answer.** `TurkishNLP.normalize` applies Turkish lowercasing (`I → ı`,
   `İ → i`), so `Okuduğum` and `okuduğum` are one answer and one shared hint is correct.

## Question / drill standards

A good drill is a sentence a Turkish speaker would say, one blank whose value the sentence and hint fix
together, and a translation of the *completed* sentence. Pitfalls:

- **Accusative drills must be translated with a definite object.** `Ben ▮ okuyorum` is answerable as `kitap` or
  `kitabı`; only *I am reading **the** book* forces the suffix. Every accusative translation in the file does
  this correctly today — it is a rule to hold, not a defect to fix.
- **Give the harmony something to bite on.** A drill whose stem is a loanword with mixed vowels (`kitap`,
  `saat`, `kalp`) teaches the exception before the rule; keep A1 harmony drills on transparent stems and
  introduce the exceptions with an explicit hint about them.
- **The rounded harmony axis is not gradable as written.** Layer 2.5 of `backend/services/nlp/base.py` strips
  combining marks, so `mü → mu`, `sütü → sutu`, `gölü → golu`, `çantada → cantada`, `öğrenci → ogrenci`: a
  learner who ignores rounding gets amber `CORRECT_SLOPPY`, even on a grammar card. The unrounded axis survives
  (`ı` is a separate letter, not `i` plus a mark), so `mı` vs `mi` *is* graded. Design harmony points around the
  front/back contrast and treat rounding as coaching.
- **Case drills are safe from the leniency layers.** `TurkishNLP.get_morphological_family` generates the plural
  and the locative/ablative/genitive/dative from the lemma, but grammar cards grade family matches as
  `WRONG_FORM`, so `evde` typed for `evden` is correctly not accepted.
- **Prefer one-token answers** (the file's only multi-word answer, `ne zaman`, is idiomatic and fine), and keep
  the personal ending inside the answer only when the point is about that ending (`evdeyim`, `okuldayız`).

## Translation & definition standards

- **No bare one-word gloss for a polysemous word — Turkish's homograph problem is stem-shaped.**
  `data/tr_frequency.tsv` has **1283** single-word noun glosses, and many nouns are also bare verb stems
  (= the imperative): `gül` → *rose* (also *laugh!*), `kaz` → *goose* (also *dig!*), `yaz` → *summer; spring*
  (also *write!*), `yüz` → *hundred* (tagged `num`; also *face* and *swim!*). A vocab card built from those rows
  teaches one of two or three equally common words.
- **Where a noun's stem changes under suffixation, the definition says so:** `kitap (kitab-)`, `şehir (şehr-)`,
  `hak (hakk-)` — without it a learner meets `kitabı` and does not recognise `kitap`.
- **Gender/class marking does not apply** — Turkish has none. The corresponding obligation is **harmony class**:
  a definition or gym chip should make front/back and rounded/unrounded visible, since that is what predicts
  every suffix the learner will ever attach.
- **Register:** neutral written standard. `siz` as polite singular is taught as such; the `-yor` reductions of
  speech stay out of the drill sentences.

## Current measured state

From the crawl, re-verified by opening `data/grammar/tr_grammar.json` and `data/tr_morphology.json`.

- **42 points, 285 drills**, every point `source: contributor`, `reviewed: true`, A1→C2 (12/10/7/6/4/3). A1
  points carry 6–12 drills each; everything from A2 up carries 6. 12 points have `related` cross-links and 9
  have a `paradigm` list — the richest cross-linking of the three languages in this group. Corpus:
  `tr_sentences.tsv` 26,359 rows, `tr_frequency.tsv` 10,000, gym manifest `data/gym/tr.json`, seeder
  `backend/services/seeder/seed_turkish.py`.
- **Hint leaks: 0.** Not one hint contains its own answer, in any of the leak classes that dominate German,
  French or Portuguese. Turkish is the cleanest file in this group.
- **Duplicate hints: 1 raw pair beyond the legitimate one.** The allomorph set
  (`question particle — harmonize with the last vowel` → `mı`, `mi`, `mu`, `mü`) is **correct and must be
  exempted**. The other, `to read + object participle, my` → `Okuduğum` / `okuduğum`, is a capitalisation pair,
  i.e. one answer to the grader. Real violations: **0**.
- **Harmony-outcome hints: 3** — `harmony after 'a/ı'` → `mı`, `harmony after 'ö/ü'` → `mü` (both in *Question
  particle*), `school + accusative (back, rounded)` → `okulu`. These do the learner's computation and sit
  alongside four hints in the same point that correctly do not.
- **Giveaway-by-gloss: 10** (hint ≤3 words appearing verbatim in the drill's own translation) — 4 in
  *Before and after*, 3 in *Postpositions ile and için*, plus `daha`/*more*, `gibi`/*like*, `Ne`/*what*.
  **One-word hints: 23.** The crawl says 22; the file says 23 — trust the file. Ten of them are the gloss
  giveaways; `existence` / `non-existence` / `absence` in *Var / yok* name a function and pass.
- **Empty hints/translations/explanations: 0. Vague translations: 0. Answer echoed in the sentence: 0. Answer
  present in the English translation: 0.**
- **Morphology file — the crawl is half wrong and the file wins.** `data/tr_morphology.json` has 3840 entries
  and **zero chips**, as reported. But it is *not* "effectively a bare word list": every one of the 3840 entries
  carries a full `Cases` chart (Nom./Acc./Dat./Loc./Abl./Gen. × singular/plural), and the charts are
  morphologically right — `kitap → kitabı / kitaba / kitapta`, `burun → burnu / burna`, `şehir → şehri`,
  `hak → hakkı`, `su → suyu`, `çocuk → çocuğu`. Softening, syncope, gemination and the buffer `y` are all
  handled.
- **The real morphology gap is coverage, not quality: all 3840 entries are `pos: noun`. There is not one verb.**
  In a language whose difficulty is almost entirely verbal morphology — `-iyor`, `-di`, `-miş`, `-ecek`, `-ir`,
  `-meli`, `-se`, `-ebil`, plus voice and participles, 30 of the 42 grammar points — the gym has no verb
  paradigm to show. Nor is there a `Harmony` chip (front/back, rounded/unrounded) to make the one fact that
  governs every suffix visible.

## Testing checklist

```bash
python -m backend.services.quality.audit_content --language tr
.venv/bin/pytest backend/tests/test_nlp_turkish.py -q
```

Turkish is not in `TRANSLIT_LANGS` (`ru ar el he fa hi th ko`), so the transliteration suite does not apply;
check instead that `ç ğ ı İ ö ş ü` survive the answer box and that a learner typing `IŞIK` for `ışık` is graded
by `turkish_lower`, not by Python's default casing. `test_nlp_turkish.py` already covers the lemmatiser and the
harmony-aware family; the gap worth closing there is an assertion that `mu` typed for `mü` returns
`CORRECT_SLOPPY` rather than `CORRECT`, so the leniency is pinned rather than rediscovered. A human reviewer
pulls 10 random drills (`--sample 10`) and asks:

1. **Does the hint tell me which vowel to use, or only that I must harmonise?** Three fail.
2. **Could I answer this from the English translation alone?** 10 fail on the bare gloss.
3. **If the answer is accusative, does the English say "the"?** All pass today — keep it that way.
4. **Is the suffix set genuinely one morpheme's allomorphs?** If yes, a shared hint is right; if the answers are
   different morphemes, it is underdetermined.
5. **Does the hint name every piece glued into the answer, in order?** `evdeyim` needs stem, case and copula.
6. **Would the answer typed without the dots and cedillas be the same string?** If yes (`mü`, `sütü`, `gölü`),
   the drill grades amber and cannot teach its own contrast.
7. **Is the sentence standard Turkey Turkish, not a spoken reduction?** `geliyom`, `gidiyoz` fail.

## Wrong-lexeme sweep, top 500 (25 Aug 2026)

**8 rows reglossed**, of which **3 were fatal** — the card named a
genuinely different word, not merely an incomplete one. Found by
`audit_wrong_lexeme` and decided by a maker–checker pass against each row's full
kaikki sense inventory and the course's own sentences.

The cause is structural, not clerical: a rank is earned by whatever string appeared in
running text, and where a spelling is both an inflection of a common verb and a separate
dictionary word, the sense-picker could take the dictionary word. See
`docs/quality/CHECKS.md` §3b.

The worst of them, by rank:

| rank | word | now reads |
| --- | --- | --- |
| 65 | `bile` | even, so much as; (after a verb) already; archaic variant of ile: with, toge |
| 174 | `hala` | still, yet (the circumflex of hâlâ is routinely dropped in writing); paterna |
| 182 | `al` | second-person singular imperative of almak: take!, get!, buy! (onu al — pick |

Fixes are in `data/gloss_overrides.tsv` as well as `data/tr_frequency.tsv`, because
glosses regenerate from kaikki and a TSV-only edit would be undone by the next seed.

Re-run with `python -m backend.services.quality.audit_wrong_lexeme --lang tr --band 500` — remaining candidates are rows a reviewer
deliberately kept, plus anything added since.
