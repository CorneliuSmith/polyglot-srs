# Seed data — sources, licensing, and regeneration

Vocabulary and sentence seed files in this directory are built by the
sourcing pipeline, not scraped:

```sh
python -m backend.services.seeder.source_data --language tr            # frequency + translations
python -m backend.services.seeder.source_data --language sw
python -m backend.services.seeder.source_data --language tr --sentences  # + graded Tatoeba examples
python -m backend.services.seeder.source_data --language tr --source kaikki  # best coverage (large download)
```

Then load into the database:

```sh
python -m backend.services.seeder.run --language tr
python -m backend.services.seeder.run --language sw
python -c "import asyncio, os; from pathlib import Path; \
  from backend.services.seeder.source_data import load_example_sentences; \
  asyncio.run(load_example_sentences(os.environ['DATABASE_URL'], 'tr', Path('data/tr_sentences.tsv')))"
```

## How progression grading works

- **Word order**: words are ranked by corpus frequency; inflected forms are
  folded onto their dictionary headword (Turkish suffix stripping, Swahili
  verb-prefix stripping) so a verb's rank reflects all of its conjugations.
  `rank_to_level()` maps rank bands to CEFR levels (top 500 = A1, etc.).
- **Sentence difficulty**: each Tatoeba sentence is scored by the frequency
  rank of its *rarest* word — a sentence is only as easy as its hardest
  word. Sentences containing words outside the vocabulary are pushed to the
  end. This lets the app serve "i+1" examples: sentences fully inside the
  learner's level except the card being studied
  (`example_sentences.difficulty_rank`).

## Sources and licenses

| Data | Source | License | Notes |
|---|---|---|---|
| Turkish frequency | [HermitDave FrequencyWords](https://github.com/hermitdave/FrequencyWords) (OpenSubtitles 2018) | CC-BY-SA-4.0 | |
| Swahili frequency | [christos-c/bible-corpus](https://github.com/christos-c/bible-corpus) Swahili NT | Public domain | Bootstrap only — register-skewed. Prefer a [Leipzig Corpora](https://wortschatz.uni-leipzig.de/en/download) or [An Crúbadán](http://crubadan.org/) list (CC-BY) for production. |
| Translations (bundled TSVs) | [FreeDict](https://github.com/freedict/fd-dictionaries) tur-eng / swh-eng | **GPL-2.0-or-later** | OK for server-side use; **re-source from kaikki before distributing the data** (e.g. in a mobile app bundle). |
| Translations (`--source kaikki`) | [kaikki.org](https://kaikki.org/dictionary/) Wiktionary extracts | CC-BY-SA-3.0 | Best coverage (10-50x more words). Requires attribution to Wiktionary + share-alike on the data. |
| Example sentences | [Tatoeba](https://tatoeba.org/en/downloads) per-language exports | CC-BY-2.0-FR | Attribution required; stored per-row in `example_sentences.license`. |
| Russian | OpenRussian TSV dumps | CC-BY-SA | see `seed_russian.py` |
| English | NLTK WordNet + bundled frequency list | WordNet License | see `seed_english.py` |

**Attribution requirements for production**: a "Data sources" page crediting
Wiktionary (CC-BY-SA), Tatoeba (CC-BY), OpenSubtitles/FrequencyWords
(CC-BY-SA), and OpenRussian satisfies the attribution clauses. Share-alike
applies to the *data*, not your application code.

`data/raw/` holds cached downloads and is gitignored. The committed
`sw_frequency.tsv` / `tr_frequency.tsv` were generated with
`--source freedict` (this environment cannot reach kaikki.org); regenerate
with `--source kaikki` for production coverage and friendlier licensing.
