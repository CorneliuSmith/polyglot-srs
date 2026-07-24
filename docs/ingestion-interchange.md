# Ingestion interchange (extra-agent → PolyglotSRS)

Content that comes from **documents** (a PDF coursebook, a grammar reference, a
scanned worksheet) is extracted by [`extra-agent`](https://github.com/corneliusmith/extra-agent)
into a single, versioned **interchange document** and then lowered onto the seed
files this repo already knows how to load. This page documents that contract from
the *consumer* side: what shapes we accept, and which reader ingests each one.

The canonical model — the `polyglot_interchange` Pydantic package, its
validation, gap analysis, and the adapter that emits the files below — lives in
extra-agent. Nothing here changes; the interchange is designed *against* our
existing ingest surface, so an interchange document produces the same files a
contributor would hand-author.

## What the extractor produces, and who reads it

| Interchange section | Seed file it emits | Reader in this repo |
| --- | --- | --- |
| `grammar[]` — points, charts, drills, **prerequisites** | `data/grammar/{code}_grammar.json` | `backend/services/seeder/seed_grammar.py` |
| grammar drill `hint_translations` | `data/grammar/{code}_drill_hints.{locale}.json` | `seed_grammar.py` (`_attach_hint_translations`) |
| `vocabulary[]` — word, translations, morphology | `data/{code}_vocabulary.csv` | `backend/services/seeder/csv_importer.py` |
| `sentences[]` — example sentences per word | `data/sentences/{code}_sentences.tsv` | `backend/services/seeder/seed_sentences.py` |
| grammar `gym` — form-category picker entries | `data/gym/{code}.json` | `backend/routers/gym.py` (read live) |
| vocabulary at level `A0` — alphabet letters | `data/alphabet/{code}.json` | `backend/services/seeder/seed_alphabet.py` |
| grammar `pitfalls` — common learner errors | `backend/services/tutor_skills/{code}/ERRORS.extracted.md` | review artifact (fold into `ERRORS.md` by hand) |

Once the files are in place, seeding is the usual path — no new tooling:

```bash
python -m backend.services.seeder.seed_grammar   --language {code} --db-url "$DATABASE_URL"  # incl. prerequisites
python -m backend.services.seeder.run --file data/{code}_vocabulary.csv --language {code}
python -m backend.services.seeder.seed_sentences --language {code} --db-url "$DATABASE_URL"
python -m backend.services.seeder.seed_alphabet  --language {code} --db-url "$DATABASE_URL"  # if data/alphabet/{code}.json present
```

The Gym reads `data/gym/{code}.json` at request time (no seeding step). `ERRORS.extracted.md`
is a **review artifact**, not seeded — a human folds it into the tutor's `ERRORS.md`.

Because these seeders **upsert by natural key**, re-running them is idempotent —
loading the same file twice updates in place rather than duplicating. The
extractor leans on that: it keeps an audit trail of every extraction run and can
re-emit these exact files and re-run the seeders at any time (`extra-agent-repush`),
so recovering from an interrupted seed or a reset checkout needs no re-extraction.

## The contract the extractor mirrors

The interchange model deliberately reuses *our* controlled values, so a document
that validates on the extractor side loads here without translation:

- **CEFR levels** — `A1`–`C2` on grammar; vocabulary also allows **`A0`** for
  alphabet cards (the `CHECK` widened in `alphabet_level.sql`). The CSV importer
  still only accepts `A1`–`C2`, so A0 letters are emitted to
  `data/alphabet/{code}.json` (consumed by `seed_alphabet.py`), never the CSV.
- **Level provenance** — the vocabulary CSV may carry an optional `level_source`
  column (`frequency` | `curated` | `ai`, migration
  `20260820000000_vocab_level_source.sql`). The extractor only sets it to `ai`,
  for a level its `--fill` pass *generated* — so a provisional AI estimate is
  gated out of learners' decks (Strict) and routed through a reviewer, exactly
  like generated drills. A level taken from the document leaves it blank, and the
  importer lowers that to the objective `frequency` default. A reviewer's
  `curated` confirmation survives re-seeding (the loader never downgrades it).
- **Part of speech** — the `VALID_POS` set in `seeder/validators.py`.
- **Prerequisites** — a grammar point may list the *titles* of points to learn
  first; `seed_grammar.load` resolves them to `grammar_points.prerequisites`
  ids in a second pass (unresolved titles are dropped, like `related`).
- **Gym form-categories** — a point whose chart is a drillable paradigm may
  carry `gym` (column + label + usage + example), lowered to the
  `data/gym/{code}.json` manifest `gym.py` reads.
- **Cloze marker** — every grammar drill sentence contains `{{answer}}`, with the
  inflected `answer` stored explicitly (`drill_sentences.answer`).
- **Paradigm coverage** — a grammar point tagged with a paradigm has **≥ 2
  drills per cell** and no stray cells, exactly as `seed_grammar.transform`
  enforces. A grammar *chart* extracted from a document lowers into this shape;
  an under-covered chart is reported as a gap, not shipped with a hole.
- **Provenance** — extracted rows carry a `source` from the sentence-provenance
  vocabulary (`seed`/`human`/`ai`/`tatoeba`/`kaikki`/`imported`) plus an
  `origin_detail` naming the document, so imported content stays distinguishable
  from ours (migration `20260813000000_sentence_provenance.sql`).

## "Fill the gaps"

A document rarely arrives seed-complete. The extractor's gap report enumerates
what is missing against these requirements — a word with no English definition (a
hard block, since `csv_importer` requires one), a grammar point with no level, a
chart cell short of its two drills, an example sentence whose word we don't have.
That report is the work list for the extractor's generation pass and, ultimately,
for our own AI content pipeline (the maker→checker seam in
`backend/services/models.py`). The interchange draws the line clearly: emit in
**strict** mode for a fully-filled document (CI-safe), or **lenient** mode to
seed the loadable subset now and fill the rest later.

## Versioning

Interchange documents carry a `schema_version` (currently **0.3.0** — it added
vocabulary `level_source`; 0.2.0 added `A0`, `gym`, `pitfalls`, and
`prerequisites`). When a migration changes one of the controlled values above,
the corresponding constant in the extractor's `enums.py` is updated and the
version is bumped — so a mismatch is visible rather than silently loading wrong
data.
