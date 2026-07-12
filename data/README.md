# Seed data — sources, licensing, and regeneration

## Quick start — seed offline (no API key, no internet)

The bundled files in this directory are enough to populate a working corpus
without any external calls. Against your `DATABASE_URL` (e.g. Supabase):

```sh
# Vocabulary (bundled frequency+translation TSVs). Auto-assigns CEFR levels
# from frequency rank AND creates a vocabulary content_list per level, so the
# words are immediately subscribable by onboarding and "Learn Vocabulary".
python -m backend.services.seeder.run --language sw   # 1204 words
python -m backend.services.seeder.run --language tr   # 766 words

# Grammar (bundled curriculum JSON: reviewed points + cloze drills + a grammar
# content_list per level). Reviewed drills also feed placement.
python -m backend.services.seeder.seed_grammar --language ru
python -m backend.services.seeder.seed_grammar --language tr
```

After this, onboarding/placement and the learn loop work end-to-end for those
languages. Everything below regenerates or extends this data and needs internet
(sourcing) or an Anthropic API key (AI grammar/curriculum generation).

### Curated starter seeds

`{es,fr,de,it,ca,mi,yo,ha,xh}_frequency.tsv` and `grammar/es_grammar.json` are
small, **hand-authored** A1/A2 starter sets (~30 words each), not sourced
frequency corpora — enough to make onboarding, placement, and the learn/review
loop work per language for a demo. Replace them by running the sourcing
pipeline below for a full, frequency-ranked corpus.

## Full pipeline — sources, licensing, and regeneration

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
| Spanish/Italian/French/German/Catalan | HermitDave FrequencyWords (OpenSubtitles 2018) | CC-BY-SA-4.0 | frequency; merged with kaikki Wiktionary (`--source kaikki`). |
| Māori (mi) | **you supply** `data/mi_frequency.tsv` | — | No OpenSubtitles list; drop a CC-licensed frequency TSV (e.g. from a Māori corpus) plus kaikki glosses. |
| Russian | HermitDave FrequencyWords + kaikki Russian extract | CC-BY-SA | The OpenRussian download host (downloads.openrussian.org) no longer resolves (2026-07); Russian now rides the generic pipeline (`--language ru --source kaikki`) with pymorphy3 morphology enrichment in `RussianFrequencySeeder`. |
| English | NLTK WordNet + bundled frequency list; per-locale word translations from the kaikki ENGLISH extract (`--language en`); per-locale example sentences from reversed Tatoeba links (`--language en --sentences`) | WordNet License / CC-BY-SA / CC-BY | see `seed_english.py`; powers "learning English from <language>" (user_profiles.support_locale) |

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

For languages without a hand-authored curriculum, AI-generate one (points +
drill sentences). Every generated drill is self-validated through that
language's own NLP backend — only drills whose answer actually validates (and
whose blank matches its answer) are kept; the rest are dropped. Everything is
written as `ai` / unreviewed for a specialist to approve in `/contribute`:

```sh
python -m backend.services.seeder.generate_curriculum --language sw --dry-run    # validate + report
python -m backend.services.seeder.generate_curriculum --language sw --generate   # write to DB
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

Specialists can also author notes **in-app**: grant a role and they edit
grammar explanations at `/contribute` (submissions land `reviewed = false`;
an admin approves them). Bootstrap the first admin with SQL, then grant the
rest via the API:

```sql
-- first admin (run once against the DB):
INSERT INTO contributor_roles (user_id, role) VALUES ('<auth-user-id>', 'admin');
```

```sh
# CLI JSON import is still available for bulk hand-off:
python -m backend.services.seeder.generate_grammar --language ru \
    --import-file data/ru_grammar_notes.json
```

All three sources (AI, contributor, open) share the `explanation_source` +
`reviewed` columns so they coexist without clobbering each other.
