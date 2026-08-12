# Arabic (ar) — Content Quality Standards

## Language profile
Arabic script, right-to-left, cursive with positional letter forms.
**The authoritative variety is Modern Standard Arabic (الفصحى)** — the register of news,
textbooks and formal writing, and the register `backend/services/nlp/arabic.py` grades
against (its camel-tools MSA analyser supplies lemmas and roots; a colloquial form usually
has no analysis at all and drops to the bare-string fallback).
Explicitly out of scope in `sentence`, `answer`, `translation`, `hint` and vocabulary
definitions: **Egyptian, Levantine, Gulf, Iraqi and Maghrebi colloquial**, plus
Classical/Qurʾanic forms MSA no longer uses productively. Dialect belongs in exactly one
place — a `culture_note` on a grammar point, clearly labelled ("in Egyptian this is …").
Gender is two-way (m./f.) on nouns, adjectives, verbs and 2nd/3rd persons; number is
three-way (sg./dual/pl.), plurals split sound vs broken. Three features dominate drill
quality here:
1. **Root-and-pattern morphology** — meaning in the consonantal root, form in the vowel
   pattern; wrong-form answers share the root, so `check_answer` returns `WRONG_FORM` with
   the root rather than a flat WRONG.
2. **Tashkeel is not graded.** `normalize()` runs `dediac_ar` first, so every short vowel,
   tanwīn and shadda is stripped before comparison. A contrast carried only by tashkeel is
   invisible to the grader.
3. **Look-alike folding.** `fold_arabic_script` folds ى/ي/ی, ك/ک, ة/ه and all alef seats,
   maps ؤ→و and ئ→ي, drops standalone ء and tatweel, and maps Arabic-Indic digits to ASCII.
   A drill whose only contrast is one of those cannot be failed.

## Hint standards
Universal rules, once: a hint narrows the answer without containing it. Never the answer as
a whole word; never a gloss that already sits in the drill's own `translation`; never the
`answer — explanation` template; one hint resolves to exactly one answer inside a point
(allomorph sets excepted where the sentence disambiguates); hints are written in English —
quoting a base form in Arabic script is fine, whole Arabic sentences are not.

Arabic-specific:
- **Quote at most one Arabic base form, never the construction the answer sits in.** 45 of
  274 hints quote Arabic and that convention is good. GOOD `books (كتاب)` — one singular
  token, answer absent. BAD `none but (ما…إلا)` for answer `إلا` ("Fronting & restriction")
  — the quoted construction contains the answer.
- **The SENTENCE must fix the referent; the hint must not spell out the features.**
  Where `أنتَ`, `أنتِ` and `أنتم` are answers in the same point, a bare `you` is
  underdetermined — but `you — feminine singular` is the leak the Romance files
  ban (it picks the answer outright). Fix the drill, not the hint: the sentence
  has to say who is addressed. GOOD sentence `{{answer}} طالبةٌ في الجامعة` — the
  feminine predicate settles it, hint `you`. BAD: leaving the sentence ambiguous
  and disambiguating in the hint.
  This rule USED to read "name person, gender and number, since the vowel that
  distinguishes them does not survive normalization". That premise is gone: the
  grader now treats a deliberately vocalized answer on a form drill as a form
  drill, so `أنتَ` no longer passes for `أنتِ` (backend/services/nlp/arabic.py).
- **Don't restate the translation.** GOOD `1st person singular — subject of a verbless
  sentence` for `أنا`. BAD `I` under translation `I am a student.`
- **Grammatical labels in English, parenthesised, after the sense.** GOOD `in wisdom
  (tamyīz, acc.)`. BAD `تمييز منصوب` — metalanguage a beginner cannot read.
- **Dialect is never a hint.** BAD `want (عايز)`. GOOD `want — present tense of أراد`.

## Question / drill standards
- **MSA only, every field.** No `عايز/عاوز`, `مش`, `بدي/بدك`, `فين`, `إيه`, `دلوقتي`,
  `كده/كدا`, `هيك`, `شو`, `ليش`, `وين`, `بتاع`, `معلش`, `هاد/هاي`; also no `يلا` for "come
  on", `بكرة` for "tomorrow" (MSA `غدًا`), `كمان` for "also" (MSA `أيضًا`), `دي/ده` as
  demonstratives.
- **Exactly one blank**, and the sentence must force the answer *after* normalization, not
  merely on the page. If the learner can type the active verb, the masculine pronoun or the
  Form I stem and still match the stripped string, the drill does not test what it claims to.
- **Tashkeel policy.** Sentences are unvocalized (current practice: near-zero tashkeel in
  `sentence`). Vocalize an `answer` for display value only, never as the grading signal, and
  prefer a contrast that survives dediacritization — write the tanwīn alef (`علمًا` → `علما`,
  still distinct from `علم`) rather than a bare tanwīn over hamza or taa marbuta (`ماءً` →
  `ماء`, contrast gone). Point `explanation` text may be fully vocalized; it is read, not
  typed. Never half-vocalize a word.
- **Orthography, matching `arabic.py` / `arabic_script.py`** — content is canonical even
  though the grader is forgiving: correct hamza seats `أ إ آ` (never bare `ا` for `أنا`,
  `أنت`); word-final `ى` where MSA requires it (`على`, `إلى`, `مصطفى`), `ي` elsewhere; Arabic
  kaf `ك` (U+0643), never Persian keheh `ک`; taa marbuta `ة`, never `ه`; no tatweel `ـ`;
  ASCII digits in answers; Arabic punctuation `،` and `؟`, not `,` and `?`.
- **Never build a drill whose only contrast is ة↔ه, a hamza seat, ى↔ي or a standalone ء.**
  Those score `CORRECT_SLOPPY` or fold outright — the card cannot be failed, so it teaches
  nothing.
- Every drill carries a `transliteration` (274/274 today) and it must match its answer.

## Translation & definition standards
- No bare one-word gloss for a polysemous word. `زي` is not "like" — it is "uniform,
  costume (n.)"; the "like" sense is colloquial and out of scope.
- **Mark gender on every noun definition** (`m.`/`f.`), and plural where it is broken.
  `ar_morphology.json` carries a Gender chip on 4662 entries; definitions must not be poorer
  than the morphology file.
- **The translation must translate.** A conventional English equivalent stating something the
  Arabic does not say is a fail, not a liberty.
- Beware frequency-list homographs: a top-few-thousand entry is almost never the rare sense a
  dictionary dump picked. `مش` glossed "to suck the marrow from (a bone)" and `وين` glossed
  "black grape" are formally MSA but are not why those strings are frequent.
- Register consistency: neutral standard English on one side, MSA at the point's level on the other.

## Current measured state
40 grammar points (A1–C2), 274 drills, 274/274 transliterated, 96/274 with a `cell` label.
Corpus: `data/ar_sentences.tsv` 14671 rows, `ar_frequency.tsv` 8778, `ar_morphology.json` 6869.

**Dialect grep (the owner's complaint), 18 markers, over `data/grammar/ar_grammar.json` and
`data/ar_sentences.tsv`:**
- `ar_grammar.json`: **0 hits.** No marker appears anywhere in the file.
- `ar_sentences.tsv`: 4 raw hits, **all four false positives** where the marker is a substring
  split by a diacritic — `المحلّفين` and `الموظّفين` match `فين` (rows 6375, 13847), and row
  8204 is `مشّط شعرك قبل أن تخرج.` "Comb your hair before you go out." whose *word* column was
  mis-lemmatized to `مش`.
- Widening past the 18 found **three genuine register defects**, all outside the grammar file:
  - `data/ar_sentences.tsv:9805` — `ستقلي خطاب بكرة، أليس كذلك؟` / "You're giving a speech
    tomorrow aren't you?" — `بكرة` for "tomorrow" is colloquial (MSA `غدًا`); `ستقلي` is a typo
    for `ستُلقي`.
  - `data/ar_sentences.tsv:2060` — `صباح الخير, سيدي! كل سنه وانتا طيب.` / "Good morning, sir!
    A merry Christmas to you!" — colloquial `وانتا`, `سنه` for `سنة`, an ASCII comma, and a
    translation that does not translate.
  - `data/ar_frequency.tsv:6947` — `يلا  intj  come on, c'mon; let's go` — colloquial
    interjection in the MSA frequency list.
- Only 2 of 40 points have a non-empty `culture_note` and neither mentions dialect, so the
  "dialect only in labelled culture notes" rule has nothing to police in the grammar path.
  The register problem is in the sentence and frequency corpora, not the drills.

**Other fail-level violations:**
- Hint leak: **1** — `"answer": "إلا", "hint": "none but (ما…إلا)"`.
- Giveaway-by-gloss: **48**, verified against the file — "Personal pronouns" 11,
  "Prepositions" 6, "Comparative & superlative" 6, "Questions" 5, "inna and her sisters" 5.
  39 hints are a single word.
- Gender unmarked in noun hints: **26 of 34**. The crawl says 8/30; joining drill answers
  against `ar_morphology.json` gives 34 noun answers with the same 8 marked — trust the file.
  In `ar_frequency.tsv`, 8 of 4447 noun glosses mention gender at all.
- **Ungradeable after `normalize()`: 10 of 274.** Of 18 answers carrying tashkeel, ten lose
  the entire contrast they exist to test.
- `ar_sentences.tsv`: 85 rows use ASCII `,` inside the Arabic, 2 use ASCII `?`, 18 write `انت`
  without its hamza.
- Empty hints/translations/explanations: 0. Duplicate hints: 0.

Worst offenders:
1. `"answer": "أُعلن", "hint": "was announced (passive)"` — normalizes to `اعلن`, identical to
   active `أَعلَن`. Siblings `وُلد`, `طُبع`, `تُستخدم` fail the same way, in the one point whose
   explanation says "the passive changes the verb's vowels, not its letters".
2. `"answer": "أنتِ", "hint": "you — feminine"` beside `"answer": "أنت", "hint": "you"` in
   "Personal pronouns" — both normalize to `انت`, so the feminine drill cannot be failed and
   the masculine hint is underdetermined.
3. `"answer": "حكمةً", "hint": "in wisdom (tamyīz, acc.)"` — normalizes to `حكمة`; the
   accusative tanwīn that is the entire point is gone. `ماءً` → `ماء` fails identically; four
   siblings survive only because the tanwīn alef is a real letter.
4. `"answer": "يدرّس"` ("The professor teaches Arabic") — shadda stripped gives `يدرس`, so
   Form I "studies" is accepted on a Form II drill.

## Testing checklist
- `python -m backend.services.quality.audit_content --language ar` — the automated checker
  (lands with this change; may not exist in your tree yet).
- `.venv/bin/pytest backend/tests/test_nlp_arabic.py -q` and
  `.venv/bin/pytest backend/tests/test_seeder_arabic.py -q`
- Arabic is in `TRANSLIT_LANGS` (`frontend/src/features/keyboards/translit.ts`):
  `cd frontend && npx vitest run src/__tests__/translit`
- Human spot-check — 10 random drills read against the standards above. A drill fails if: any
  field contains a dialect form; the hint's English text also appears in the translation; the
  hint quotes a construction containing the answer; the tested contrast is tashkeel, ة↔ه, a
  hamza seat or ى↔ي only (type the plausible wrong answer into the grader and confirm it is
  refused); a noun answer's hint omits gender; the transliteration disagrees with the answer;
  ASCII `,` or `?` appears inside Arabic text; or the English states something the Arabic does
  not. Read the sentence aloud and ask whether a newsreader would say it — that is the
  register test.
