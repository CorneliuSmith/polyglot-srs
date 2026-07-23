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
| `grammar[]` — points, inflection charts, drills | `data/grammar/{code}_grammar.json` | `backend/services/seeder/seed_grammar.py` |
| grammar drill `hint_translations` | `data/grammar/{code}_drill_hints.{locale}.json` | `seed_grammar.py` (`_attach_hint_translations`) |
| `vocabulary[]` — word, translations, morphology | `data/{code}_vocabulary.csv` | `backend/services/seeder/csv_importer.py` |
| `sentences[]` — example sentences per word | `data/sentences/{code}_sentences.tsv` | `backend/services/seeder/seed_sentences.py` |

Once the files are in place, seeding is the usual path — no new tooling:

```bash
python -m backend.services.seeder.seed_grammar  --language {code} --db-url "$DATABASE_URL"
python -m backend.services.seeder.run --file data/{code}_vocabulary.csv --language {code}
python -m backend.services.seeder.seed_sentences --language {code} --db-url "$DATABASE_URL"
```

## The contract the extractor mirrors

The interchange model deliberately reuses *our* controlled values, so a document
that validates on the extractor side loads here without translation:

- **CEFR levels** — `A1`–`C2` (the `CHECK` on `grammar_points`/`vocabulary`).
- **Part of speech** — the `VALID_POS` set in `seeder/validators.py`.
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

Interchange documents carry a `schema_version`. When a migration changes one of
the controlled values above, the corresponding constant in the extractor's
`enums.py` is updated and the version is bumped — so a mismatch is visible rather
than silently loading wrong data.
