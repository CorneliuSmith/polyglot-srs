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
**6 drills per grammar point** (minimum 4) and **4 example sentences per
vocabulary word**, so sentence rotation gives varied exposure on every review.

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
