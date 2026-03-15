# Phase 3 Research: Seed Data Pipeline

## Data Sources

### Russian — OpenRussian.org TSV Dumps
- **URLs**: `https://downloads.openrussian.org/ru/words.tsv`, `https://downloads.openrussian.org/ru/translations.tsv`
- **Format**: TSV with headers
- **words.tsv fields**: id, position (frequency rank), bare (word without stress), accented (with stress mark ́), derived_from_word_id, rank, disabled, audio, usage_percent, number_of_translations
- **translations.tsv fields**: id, word_id, lang (en/de/fr/etc), tl (translation text), example, info, position
- **Size**: ~100k words, translations in multiple languages
- **License**: Creative Commons, freely downloadable
- **Morphology enrichment**: Use pymorphy3 at seed time to populate morphology JSONB (gender, aspect, animacy, POS)
- **Aspect partners**: pymorphy3 doesn't provide aspect partners directly; store aspect from pymorphy3 tag, aspect_partner field left for manual/future enrichment or card_context

### Arabic — Synthetic Seed + OpenSubtitles Frequency
- **Arabic Wordnet**: Available from globalwordnet.org but XML format is complex and unstable URLs
- **OpenSubtitles frequency**: Top 10k frequency-ranked Arabic words — available as text lists
- **Practical approach**: Create a curated seed file (JSON/TSV) with ~500-1000 high-frequency Arabic words covering A1-B1 levels, with root, form, POS pre-populated. This is more reliable than parsing unstable external datasets.
- **Morphology enrichment**: Use camel-tools Analyzer at seed time to extract root, pattern, form for each word
- **Pitfall**: camel-tools requires `camel_data` download (~3GB). Scripts must handle missing camel_data gracefully.

### English — WordNet (NLTK) + Frequency Data
- **WordNet**: Available via `nltk.corpus.wordnet` — provides definitions, synonyms, POS
- **COCA frequency**: Full list requires license. Alternative: use a free frequency list (e.g., top 5000 English words from various open sources)
- **Practical approach**: Use NLTK WordNet for definitions + a bundled frequency ranking file
- **Morphology enrichment**: Use spaCy for lemma and POS at seed time
- **Dependencies**: `nltk` package + `wordnet` corpus download (`nltk.download('wordnet')`)

## Schema Mapping

External data must map to these tables:

### vocabulary table
| Column | Source |
|--------|--------|
| language_id | Lookup by language code |
| word | OpenRussian `bare` / Arabic word / English word |
| reading | OpenRussian `accented` / Arabic with tashkeel / null for English |
| part_of_speech | pymorphy3 POS / camel-tools POS / spaCy/WordNet POS |
| level | Estimated from frequency_rank (top 500→A1, 500-1500→A2, etc.) |
| frequency_rank | OpenRussian `rank` or `position` / frequency list rank |
| morphology | JSONB from NLP analysis |
| alternatives | Empty initially, populated later |

### translations table
| Column | Source |
|--------|--------|
| vocabulary_id | FK to inserted vocabulary row |
| locale | 'en' (primary), other locales from OpenRussian translations.tsv |
| definition | Translation text |

## Architecture Decisions

1. **Seeder location**: `backend/services/seeder/` per spec
2. **Base class**: `BaseSeeder` with download(), transform(), load() template methods
3. **CLI entry point**: `python -m backend.services.seeder.run` with `--language` flag
4. **Idempotency**: Use `INSERT ... ON CONFLICT (language_id, word) DO UPDATE` (UPSERT)
5. **Data directory**: `data/` at project root for downloaded/bundled files, gitignored except small seed files
6. **Batch inserts**: Use asyncpg `executemany()` for performance
7. **Level assignment**: Frequency-rank-based CEFR estimation:
   - Rank 1-500: A1
   - Rank 501-1500: A2
   - Rank 1501-3000: B1
   - Rank 3001-5000: B2
   - Rank 5001+: C1

## Pitfalls

1. **Network dependency**: Scripts download from external URLs that may be slow/unavailable. Include retry logic and allow local file fallback.
2. **Encoding**: OpenRussian TSVs are UTF-8 but may have BOM. Use `encoding='utf-8-sig'`.
3. **camel-tools heavy**: Arabic morphology analysis is slow (~1 word/sec with full analysis). Batch and show progress.
4. **NLTK download**: WordNet corpus must be downloaded before use. Handle in script.
5. **Database connection**: Seeders need DATABASE_URL. Use same pool infrastructure from Phase 1.
6. **Testing**: Can't test with real DB in CI. Use unit tests with mock data + fixture files.

## Wave Structure

- **Wave 1**: 03-01 — Base infrastructure + Russian seeder (establishes patterns, largest dataset)
- **Wave 2**: 03-02 (Arabic) and 03-03 (English) can run in parallel (independent languages, same base class)
