# Portuguese (pt) — Content Quality Standards

## Language profile

Latin script, left-to-right. The marks authors drop are the tilde (`ã õ`, `pães`, `mãos`), the
circumflex (`ê ô`, `têm`, `avô`), the acute (`á é í ó ú`), the cedilla (`ç`) and — the one that
carries a whole C1 point — the **grave of crase** (`à`). `data/grammar/pt_grammar.json` uses no
apostrophes at all; hyphens are structural (`diga-me`, `dir-te-ei`) and belong to the answer.

**The authoritative variety is Brazilian Portuguese, post-Acordo Ortográfico.** The file commits
throughout: `você`/`vocês` as the everyday you, `a gente` for spoken "we", próclise as the default
pronoun placement ("Brazilian Portuguese prefers the pronoun BEFORE the verb"), `estar` + `-ndo`
for the progressive, and the lexicon `ônibus`, `celular`. `Ciberdúvidas da Língua Portuguesa` is
the reference cited in every point. **Explicitly out of scope as a production target:** European
Portuguese (`tu` with its own verb forms, `estar a` + infinitive, default ênclise `dá-me`,
`autocarro`/`telemóvel`). European forms are *recognised, labelled, and confined to the C2
register point*, where each drill sentence carries an explicit `(European)` or `(spoken BR)` tag —
that is the pattern to copy, never an unlabelled mix.

**Gender:** two classes, masculine and feminine, no neuter. `data/pt_morphology.json` carries a
`Gender` chip on 3577 of its 3667 nouns (1831 m / 1746 f) and `Plural` on 4172; four adjectives
carry a stray `Feminine` chip, a label the rest of the file does not use — harmless today, but
either populate it for all 986 adjectives or drop it. Three features dominate drill quality:
(1) **contraction** — `em/de/a/por` + article fuse into `no, na, do, da, à, pelo, dele, neste`, so
a blank before a noun tests the fusion, not the preposition; (2) **crase**, an accent that changes
meaning and that the grader forgives by design; (3) **clitic placement** — próclise, ênclise,
mesóclise — where the answer is sometimes a bound form (`-me`) rather than a word.


**Wrong-lexeme glosses corrected 20 Aug 2026** (`CHECKS.md` §3b): rank 286 `ia` read “AI (artificial intelligence)” where it is the imperfect of *ir*; rank 143 `pelo` read “hair; fur” where it is the contraction *por + o* this page teaches; rank 606 `irá` read “meliponine”, a stingless bee. Also `demônio` — the Brazilian spelling this page makes authoritative — carried a pointer to the European `demónio`, which held the actual meaning; the authoritative spelling now carries it.

## Hint standards

A hint narrows the answer without containing it: never the answer as a whole word; never a gloss
already in the drill's own translation; never the `answer — explanation` template; one hint
resolves to exactly one answer inside a point (allomorph sets excepted where the sentence
disambiguates); hints are in English, and quoting a Portuguese base form is fine while whole Portuguese sentences
are not.

0. **`lemma — person` is house style and legitimate** (`study — I (estudar)` → `estudo`), with zero
   collisions in the file, so the checker must use lookarounds, not `\b`.
1. **The hint is never the answer.** Portuguese owns the purest leak in the repo.
   - GOOD: `direct object — first person, before the verb` for `me` in `Ela {{answer}} viu no
     shopping ontem.`
   - BAD: `me` — the hint *is* the answer. And `me (before the verb)` in the próclise point is the
     same failure with a parenthesis bolted on.
2. **Never quote the Portuguese construction that contains the answer** — nine drills, all this
   shape.
   - GOOD: `since — causal, opens the clause, pairs with que` for `Já` in `{{answer}} que você
     está aqui, me ajuda?`
   - BAD: `since (já que)`. Same failure in `of (precisar de)` → `de`, `that (é que question)` →
     `que` (twice), `the (a gente = we)` → `A`, `that (que nem = just like)` → `que`.
3. **Noun answers mark gender — and the ones that need it most are the ones missing it.** The
   *Gender and number of nouns* point marks four of six.
   - GOOD: `book (masculine)` → `livro`; `house (feminine)` → `casa`; `cars (masculine plural)` →
     `carros`. Keep this; it is the best noun hinting in the Romance group.
   - BAD: `hands (mão → plural)` → `mãos` and `breads (pão → plural)` → `pães` — exactly the pair
     the point exists to contrast (`a mão` is feminine despite `-ão`, `o pão` masculine), and
     neither hint says so.
4. **Article and contraction hints name the source parts, not the gender under test.** The
   contraction point already does this well (`in the (em + o)` → `no`, `through the (por + o)` →
   `pelo`); the A1 *Articles* point does not (`the (feminine)` → `A`, `the (masculine plural)` →
   `Os`), which hands over the noun's gender.
5. **Crase hints must not print `a`.** `to (responder a — no article, no crase)` for answer `a`
   leaks; write `no article follows, so no crase` instead.

## Question / drill standards

A good drill is a sentence a Brazilian would actually say, one blank fixed by sentence + hint
together, and a translation that renders the *completed* sentence in natural English. Pitfalls:

- **Never let the accent be the only thing tested.** `PortugueseNLP` inherits `AccentFoldingNLP`,
  so — verified by running it — `a` for `à` grades `CORRECT_SLOPPY`, and so do `tem` for `têm`,
  `esta` for `está`, `e` for `é`. Ten drills are in this position, three of them the C1 *Crase*
  drills whose entire subject is that accent. Such a drill cannot fail a learner who ignores the
  thing it teaches; either the grader gets a strict mode for these points, or the point must
  contrast crase against a form differing by more than a mark.
- **The fronted topic must not print the answer.** `A Maria? Eu {{answer}} encontrei na feira.`
  shows a capitalised `A` before asking for `a`; `O que é {{answer}} está acontecendo ali?` prints
  `O que` while asking for `que`.
- **A bound clitic is part of the answer, and the drill must make that visible.** `Entregue{{answer}}
  o documento amanhã. (formal)` expects `-me`; typing `me` grades `WRONG` (verified). Fine for a C1
  ênclise point whose hint says "attached after the verb" — as it does — but no A1/A2 point should
  use this shape.
- **Keep multi-word answers to genuine lexical units.** Only `O que` and `Por que` exist, both
  right. Capitalisation is not tested (grading lowercases), but `Porque` for `Por que` is `WRONG`,
  which is correct and worth preserving.
- **Keep the register tag on any non-Brazilian drill**, as the C2 point does with `(European)`,
  `(spoken BR)`, `(formal)`, `(literary)`.

## Translation & definition standards

- **No bare one-word gloss for a polysemous word.** `data/pt_frequency.tsv` has 429 one-word noun
  glosses, and several longer ones are wrong by omission: `banco` → *bank (financial institution)*
  (also *bench*), `cabo` → *cape (piece of land)* (also *cable*), `manga` → *sleeve; pipe* (also
  *mango*), `canto` → *singing* (also *corner*).
- **Noun definitions carry gender.** `(m.)`/`(f.)` on every learner-facing noun gloss; where the
  gender selects the sense (`o capital` money / `a capital` city, `o grama` gram / `a grama` grass)
  both go in. Today the vocab layer marks gender in **6 of 4127** noun rows in
  `data/pt_frequency.tsv` (columns `rank / word / pos / en` — no gender column) while
  `data/pt_morphology.json` knows it for 3577 words.
- **Register consistency:** a Brazilian translation for a Brazilian sentence. If a drill teaches a
  European form, both the sentence and the translation say so.

## Current measured state

From the crawl, re-verified by opening `data/grammar/pt_grammar.json`.

- **42 points, 274 drills** — the smallest drill count in the Romance group — every point
  `source: contributor`, `reviewed: true`, A1→C2 (12/12/7/6/3/2 by level). **Zero** empty hints,
  translations or explanations; zero vague translations; zero `answer — explanation` templates;
  zero duplicate hints.
- **`leak_hard`** — 7 on 19 Aug 2026 (`data/quality/baseline.json` agrees), not the 2 this page
  used to claim; only one of the two drills named here is among them. Run `python -m backend.services.quality.audit_content --language pt` for the current figure; this page previously froze one and it drifted.
  (`ans='me' hint='me'` in *Object pronouns*, `ans='me' hint='me (before the
  verb)'` in *Pronoun placement*). **`construction_quote` (warn): 9** — `Já` → `since (já que)`;
  `de` → `of (precisar de)`; `que` → `that (é que question)` ×2; `A` → `the (a gente = we)`;
  `a` → `at (estar a + infinitive)`; `que` → `that (que nem = just like)`; `a` → `to (responder a —
  no article, no crase)`; `por` → `for (por isso = therefore)`.
- **`giveaway_by_gloss`: 23.** Worst: `ans='me' hint='me' trans='She saw me at the mall
  yesterday.'` — leak and giveaway in one drill; `ans='Onde' hint='where' trans='Where is the metro
  station?'`; `ans='o' hint='him' trans='Do you know my boss? I respect him a lot.'`
- **One-word hints: 29. The crawl says 28; the file says 29 — trust the file.** Six are the
  `não` / `not` drills, where the hint adds nothing the translation does not already give.
- **Accent-only-distinct answers: 10** — `é` ×2, `está` ×2, `têm` ×3, `à` ×3, all amber on the
  accentless form. **Answer printed in its own sentence: 2.**
- **Gender marking on noun-answer hints: 4 of 6 genuine noun drills** — the best in the Romance
  group. The crawl's "10 of 46 (22%)" counts pronouns and verb forms `pt_morphology.json`
  mis-records as nouns (`Eu`, `Ele`, `é`, `estudo`); the honest reading is that *Gender and number
  of nouns* marks `livro`, `casa`, `carros`, `meninas` and misses `pães`, `mãos`.
- **Structural gap: no curated sentence file.** `data/sentences/` has one for `it`, `fr` and `ro`
  but none for `pt`; the language runs on the 25,112-row `data/pt_sentences.tsv` alone. Frequency
  file 10,000 rows; morphology 5396 entries; gym manifest at `data/gym/pt.json`.

## Testing checklist

```bash
python -m backend.services.quality.audit_content --language pt
.venv/bin/pytest backend/tests/test_nlp_latin.py -q   # PortugueseNLP lives here
```

There is no `test_nlp_portuguese.py`; `PortugueseNLP` is in `backend/services/nlp/latin_base.py`,
covered only through shared `AccentFoldingNLP` behaviour — a crase case (`a` vs `à`) and a
`tem`/`têm` case belong beside the Catalan and French ones. Portuguese is not in `TRANSLIT_LANGS`
(`frontend/src/features/keyboards/translit.ts`), so the transliteration suite does not apply; check
instead that `ã õ ê ô ç à` survive the answer box. A reviewer pulls 10 random drills (`--sample 10`)
and asks:

1. **Is the hint the answer, or a phrase containing it?** 11 drills fail; `me` → `me` first.
2. **Could I answer this knowing no Portuguese?** 23 fail.
3. **Answer is a noun — does the hint say masculine or feminine?** `pães` and `mãos` fail, and they
   are the two that matter most.
4. **Would the unaccented spelling be a different real form?** 10 fail; the three crase drills
   cannot fail a learner who omits the grave. **Is the answer visible in the sentence?** Two fail.
5. **Is the variety Brazilian, and is any European or formal form tagged in both sentence and
   translation?** Untagged `tu`-conjugation, `estar a` + infinitive, or default ênclise below C1
   is out of scope and fails.
6. **Does a contraction blank test the contraction, not the preposition?** A blank before a
   masculine noun forces `no`/`do`/`pelo`, never bare `em`/`de`/`por`.

## Wrong-lexeme sweep, top 500 (25 Aug 2026)

**28 rows reglossed**, of which **14 were fatal** — the card named a
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
| 37 | `estou` | I am (temporary states, feelings and locations — from estar); (European, ans |
| 43 | `à` | to the, at the (a + a, feminine singular — the crase à: à noite, à casa dela |
| 63 | `era` | was, used to be (I, he, she, it, você — imperfect of ser); (as a noun, f.) e |
| 70 | `são` | they are; you are (plural — from ser); it's (telling the time: são 9h15); al |
| 136 | `tinha` | had; used to have (I, he, she, it, você — imperfect of ter); tinha que = had |
| 155 | `lhe` | (to) him, (to) her, (to) you (indirect object of the verb: eu lhe disse = I  |
| 167 | `vão` | they go, they're going; you (plural) go (from ir); they're going to (forms t |
| 194 | `olha` | look!, look at (olha isso = look at this); look, hey (opening a remark in sp |

Fixes are in `data/gloss_overrides.tsv` as well as `data/pt_frequency.tsv`, because
glosses regenerate from kaikki and a TSV-only edit would be undone by the next seed.

Re-run with `python -m backend.services.quality.audit_wrong_lexeme --lang pt --band 500` — remaining candidates are rows a reviewer
deliberately kept, plus anything added since.
