# Seed data — sources, licensing, and regeneration

Vocabulary and sentence seed files in this directory are built by the
sourcing pipeline, not scraped:

```sh
./scripts/refresh_seed_data.sh   # everything, from the best sources (run with open internet)

# or per language:
python -m backend.services.seeder.source_data --language tr            # frequency + translations
python -m backend.services.seeder.source_data --language sw
python -m backend.services.seeder.source_data --language yo --source kaikki  # Yoruba needs kaikki
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
| Yoruba frequency | [Niger-Volta-LTI/yoruba-text](https://github.com/Niger-Volta-LTI/yoruba-text) (TheYorubaBlog, Iroyin news, Òwe proverbs) | GPL-3.0 | Fully diacritized, NFC-normalized contemporary text (~200k tokens). JW300 subfolder deliberately excluded (restrictive jw.org terms). Fetched via sparse git clone. |
| Yoruba translations | kaikki.org Yoruba extract | CC-BY-SA-3.0 | Only dictionary source — no FreeDict exists. Tone-stripped fallback matching folds corpus tokens onto diacritized Wiktionary headwords. |
| Xhosa frequency | [christos-c/bible-corpus](https://github.com/christos-c/bible-corpus) Xhosa | Public domain | Bootstrap (register-skewed, ~446k tokens). Prefer a Leipzig/Wikipedia CC-BY list for production. Verb conjugations fold onto stems via XhosaNLP. |
| Xhosa translations | kaikki.org Xhosa extract | CC-BY-SA-3.0 | No FreeDict exists. |
| Hausa frequency | **you supply** plain-text under `data/raw/hausa_corpus/` | — | No PD corpus is reachable from the pipeline. Use a **commercially-usable** source: Hausa Wikipedia (CC-BY-SA), [Leipzig Corpora](https://wortschatz.uni-leipzig.de/en/download) (CC-BY), or OPUS news. **Do NOT use the Masakhane `lacuna_pos_ner` Hausa corpus — it is CC-BY-NC (non-commercial).** |
| Hausa translations | kaikki.org Hausa extract | CC-BY-SA-3.0 | Irregular plurals from Wiktionary are stored as answer alternatives. |
| Example sentences | [Tatoeba](https://tatoeba.org/en/downloads) per-language exports | CC-BY-2.0-FR | Attribution required; stored per-row in `example_sentences.license`. Yoruba coverage on Tatoeba is thin; the Òwe corpus's parallel en/yo proverbs are a future supplement. |
| Russian | OpenRussian TSV dumps | CC-BY-SA | see `seed_russian.py` |
| English | NLTK WordNet + bundled frequency list | WordNet License | see `seed_english.py` |

**Attribution requirements for production**: a "Data sources" page crediting
Wiktionary (CC-BY-SA), Tatoeba (CC-BY), OpenSubtitles/FrequencyWords
(CC-BY-SA), and OpenRussian satisfies the attribution clauses. Share-alike
applies to the *data*, not your application code.

> ⚠️ **The non-commercial trap.** The best-known African-language NLP datasets
> are often **CC-BY-NC** (non-commercial) and cannot ship in a paid product:
> Masakhane's `lacuna_pos_ner` corpora and MENYO-20k (the strongest en-yo
> parallel set) are both NC. JW300 (jw.org) is also restricted. Always check
> the license before adding a source here — prefer Wikipedia (CC-BY-SA),
> Leipzig Corpora (CC-BY), Tatoeba (CC-BY), and Wiktionary/kaikki (CC-BY-SA),
> all of which are commercial-safe with attribution.

`data/raw/` holds cached downloads and is gitignored. The committed
`sw_frequency.tsv` / `tr_frequency.tsv` were generated with
`--source freedict` (this environment cannot reach kaikki.org); regenerate
with `--source kaikki` for production coverage and friendlier licensing.

## Grammar explanations (the review "Show grammar" panel)

When a learner answers a card they can optionally expand a panel showing a
grammar explanation, a culture note, and example sentences. That text lives
on `grammar_points` (`explanation`, `culture_note`) with provenance in
`explanation_source`, populated three ways:

The grammar curriculum itself (which points exist, their drill sentences, and
hand-authored explanations) is seeded from `data/grammar/{code}_grammar.json`:

```sh
# Load grammar points + drills + a grammar content_list per level.
# Ships accurate A1 starter curricula for Russian (ru) and Turkish (tr);
# add more by dropping a curriculum JSON in data/grammar/.
python -m backend.services.seeder.seed_grammar --language all
```

Then fill explanations for any points that lack them:

```sh
# AI-generated (Claude, grounded on the language's linguistics brief + drill
# sentences), cached in the DB; never overwrites contributor content:
python -m backend.services.seeder.generate_grammar --language ru --generate

# Hand-authored by a language specialist (marked reviewed + trusted):
python -m backend.services.seeder.generate_grammar --language ru \
    --import-file data/ru_grammar_notes.json
```

| Source (`explanation_source`) | How | Trust |
|---|---|---|
| `contributor` | `--import-file` JSON `[{title, explanation, culture_note}]` from a specialist | `reviewed = true` |
| `ai` | `--generate` (Claude); set `TUTOR_DEV_MOCK=true` to populate canned text with no key | `reviewed = false` — promote after a human checks it |
| `wiktionary` | open-source usage notes from kaikki | future |

A specialist-contributor **UI/role** (so non-engineers can author and approve
notes in-app) is a future step — today contributors hand off a JSON file. The
AI generator and importer share the provenance column so the two coexist
without clobbering each other.
