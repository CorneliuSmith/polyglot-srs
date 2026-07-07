# Grammar path design — research grounding

How the grammar paths (the `/grammar` page and the ordering inside
`data/grammar/*_grammar.json`) are structured, and the models they follow.

## The models

**1. CEFR criterial-feature inventories.** The [British Council–EAQUALS Core
Inventory for General English](https://www.eaquals.org/wp-content/uploads/EAQUALS_British_Council_Core_Curriculum_April2011.pdf)
and the [English Grammar Profile](https://languageresearch.cambridge.org/images/pdf/theenglishprofilebooklet.pdf)
level grammar by what learners **actually produce** at each CEFR level, and
describe each structure **function-first** ("can say where something is").
Applied here: every grammar point carries a `function_note` (a can-do line)
shown on the path, and levels are cumulative — A2 assumes everything in A1.

**2. Official per-language inventories.** Orders are taken from each
language's authoritative syllabus rather than invented:

- **Spanish** — the [Plan Curricular del Instituto Cervantes, Gramática A1–A2](https://cvc.cervantes.es/ensenanza/biblioteca_ele/plan_curricular/niveles/02_gramatica_inventario_a1-a2.htm):
  pronouns and noun gender first, then articles, ser/estar, the present-tense
  verb families, negation, hay, interrogatives, adjective agreement.
- **Turkish** — the CEFR-aligned [Yedi İklim (Yunus Emre Institute)](https://www.yee.org.tr/en/node/10561)
  and İstanbul curricula: 'to be' suffixes and demonstratives first, then
  plural, the question particle, locative, var/yok, possessives, present
  continuous (+ negation), and the accusative last (definiteness-driven).
- **Russian** — the [TORFL elementary level](https://en.wikipedia.org/wiki/Test_of_Russian_as_a_Foreign_Language)
  inventories: gender and это-sentences before any morphology, then present
  tense, the first cases in communicative order (prepositional for place →
  accusative for objects), possessives, past tense, genitive of absence.

**3. Processability / Teachability (Pienemann).** SLA research
([overview](https://en.wikipedia.org/wiki/Teachability_Hypothesis),
[teaching-order discussion](https://gianfrancoconti.com/2025/02/12/in-which-order-should-we-teach-grammar-structures-manfred-pienemanns-answer/))
shows learners acquire processing stages in a fixed order — lexical items →
canonical word order → morphology within a phrase → agreement across phrases →
subordination — and instruction can't skip stages. Applied here: within a
level, `display_order` is strictly cumulative, and **every drill only requires
machinery taught earlier in the path** (e.g. Spanish adjective agreement comes
after gender, articles, and ser; the Turkish accusative comes after the
suffix system is established).

**Languages without an official CEFR inventory** (Swahili, Yoruba, Hausa,
Xhosa, Māori): levels are CEFR-*equivalent*, assigned by structural complexity
following the Core Inventory's functional progression and the processability
stages — e.g. Bantu verb extensions (passive/causative/applicative) sit at B2
the way Romance subjunctive does. Sources are the standard reference grammars
cited on each point.

**4. Bunpro's product model.** An ordered path of **readable grammar-point
pages** (explanation, examples, sources), grouped by level, with per-point
"add to reviews". Applied here: the `/grammar` page, `GET /api/curriculum/…`,
and `POST /api/curriculum/learn`.

**Content depth targets** (owner-decided): paths run A1→**C2** per language;
**6 drills per grammar point** (minimum 4) and **6–10 graded example sentences
per vocabulary word** (minimum 4; vocab ≥ grammar). A card shows a different
sentence on every appearance — never the one shown last time.

**Paradigm points scale past the floor.** A point whose answer space is a
morphological paradigm — subject pronouns (Spanish has NINE: yo, tú, él,
ella, usted, nosotros, vosotros, ellos, ustedes), a conjugation table, case
or gender agreement — is really N questions wearing one card. Such points
declare `"paradigm": [cells…]` and each drill carries `"cell"`; the seeder
**fails** if any cell has no drill, so the drill count is
max(6, paradigm size). Rotation is **gap-hunting**, not uniform: unseen
sentences come first (full paradigm exposure before any repeats), then the
sentences the learner keeps missing (highest miss rate from
`review_log.prompt_sentence`), then uniform — always deterministic and
reload-stable, never the last-shown. One card, one FSRS schedule (FSRS's
per-card difficulty already absorbs aggregate hardness; splitting the
paradigm into N cards would flood reviews), but the card *behaves* like N
questions because it hunts the learner's gaps.

## Language-shaped cards (typology principle)

**Point counts SHOULD differ across languages — do not equalize them.**
Bunpro's Japanese needs ~900 grammar points because Japanese externalizes
meaning into thousands of distinct analytic phrase patterns. Synthetic
languages (Russian, Turkish, the Bantu languages) pack the same meaning into
morphology instead, so they legitimately have fewer phrase-pattern points —
and the missing depth must be carried by **richer vocabulary cards that link
back to grammar**, not by inventing filler points.

Concrete per-typology rules for authors and agents:

- **Russian aspect pairs** (читать/прочитать) are ONE vocabulary card: the
  imperfective is the headword, the perfective partner lives in
  `alternatives` + `morphology.aspect_partner` (the NLP layer already accepts
  partners via `get_aspect_partner`), and the card links to the aspect
  grammar point for learners confused about which to use. Same treatment for
  **motion-verb pairs** (идти/ходить) → the verbs-of-motion point.
- **Case-language nouns** (ru, de): the vocab card's `morphology` carries a
  mini declension sample (nom/acc/gen at minimum) shown on the item page,
  linking to the relevant case points. The learner meets the forms where the
  word lives, and the rule where the pattern lives.
- **Turkish (agglutinative)**: vocab cards show 2–3 harmonized suffixed forms
  (evim, evde, evler) in `morphology`; the grammar path owns the suffix
  system itself. Sneak vocabulary variety into grammar drills — every suffix
  drill is also a vocab exposure.
- **Bantu nouns** (sw, xh): the card always shows the class pair
  (mtoto/watoto) and its concords, linking to that class's grammar point.
- **Tonal languages** (yo): every form carries tone marks; tone-stripped
  answers grade as CORRECT_SLOPPY (coach, don't fail — already enforced).

The bridge mechanism is `vocabulary.morphology` (JSONB) + `alternatives` +
the Related links planned in WP13(c), extended to vocab→grammar. Follow
Bunpro's card model, but make informed per-language decisions so each word
type teaches everything a learner needs about it.

## Invariants the code enforces

- Visibility on the path = human-reviewed, or AI-passed when the language's
  review policy is `ai_ok` (same gate as learning).
- A point with no drills is **readable but never quizzable** ("Reading only").
- `display_order` within a level is the path order; the path page numbers
  points per level.
- Re-seeding upserts by (language, title) — editing a point's explanation or
  order in the JSON and re-running `seed_grammar` updates in place.

## Extending a path

Add points to `data/grammar/{code}_grammar.json` with `function` (can-do),
`explanation`, `references` (include the official inventory), and ≥2 drills
whose answers only need already-taught structures; keep `display_order`
cumulative. Then `python -m backend.services.seeder.seed_grammar --language
{code}`. AI-generated candidates (generate_curriculum) enter as drafts and
appear on the path only after linguist approval or an `ai_ok` policy.
