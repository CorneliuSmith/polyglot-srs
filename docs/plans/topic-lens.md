# Topic Lens: learn by meaning, not only by rank

A plan, not an implementation. Status: **awaiting owner approval** of the
taxonomy below (the owner has seen this plan and the bucket list in chat,
2026-08-31; implementation starts on their go).

The owner's request, verbatim: *"instead of adding purely based on language
ranking category, there could be the ability to swap to more granular
semantic meaning separations."*

The instinct maps exactly onto the code. A curriculum "deck" is not a
collection — it is a CEFR level: membership is derived
(`vocabulary.level = content_lists.level`, no membership table), and the
learn batch picks new words by `row_number() PARTITION BY level ORDER BY
frequency_rank` (`_vocab_candidates`, backend/repositories/cards.py). Pure
ranking category, no meaning anywhere.

This plan was produced from a three-design study (minimal-delta,
first-class second deck axis, learner-experience-first) judged from
learning-science, engineering, and product lenses; all three judges ranked
the lens shape first and the first-class axis last. The full research dump
is not in the repo; the decisions it produced are below.

## The design in one paragraph

Semantic grouping is a **lens over the existing queue, not a second deck
system**. One migration adds `vocabulary.topic` + `topic_source
('ai'|'curated')` — a direct clone of the `level`/`level_source` pattern.
Topic "decks" are virtual, computed at read time from the learner's
already-subscribed level lists, so a beginner's *Food & drink* deck is
A1-food-sized. The deck panel (dashboard + Decks page) gets a two-way
toggle — **By level | By topic** — and a topic Learn session is the
existing flow with a `topic` scope, ordered by frequency *within* the
topic (ranking is subordinated to meaning, not discarded). SRS state is
per-word (`user_cards`), so swapping views or re-tagging a word can never
reset, duplicate, or lose progress.

## What was explicitly rejected

A first-class topic axis (a `topics` table, membership join, own
subscription rows, parity with level decks everywhere). ~2–2.5 weeks,
rewrites the hottest selection path, creates double-count and
cross-axis-dedupe hazards — wrong stage for an invite-only beta whose
bottleneck is content. The `topic` column carries forward unchanged into
that design if real usage ever justifies it; starting small throws
nothing away.

## The taxonomy (freezes on owner approval)

One app-global set for all 27 languages — "Food & drink" means the same
thing everywhere. Display names are i18n'd in all six locales and free to
reword forever; the **set of slugs** bakes into a CHECK constraint, two
code constants, and the classifier prompt, so merging/splitting later is a
migration plus a re-sort. That makes the list itself the approval object.

22 learner-visible buckets:

| slug | display (en) | contents |
|---|---|---|
| food_drink | Food & drink | meals, cooking, ingredients, restaurants, taste |
| home_living | Home & daily life | house, rooms, furniture, chores, routines |
| family_people | Family & people | family members, ages, describing people |
| relationships_social | Friends & social life | friendship, love, invitations, celebrations, politeness |
| body_health | Body & health | body parts, illness, doctors, fitness |
| clothing_appearance | Clothes & appearance | garments, style, beauty |
| travel_transport | Travel & transport | trips, vehicles, directions, hotels |
| city_places | Town & places | buildings, shops, streets, landmarks |
| nature_weather_animals | Nature, weather & animals | landscapes, plants, animals, seasons, climate |
| time_dates | Time & dates | clock time, days, months, frequency |
| numbers_measure | Numbers & amounts | counting, quantities, sizes |
| work_professions | Work & jobs | professions, offices, business |
| school_learning | School & learning | education, studying, exams, languages |
| sports_leisure | Sports & free time | games, hobbies, exercise |
| arts_media | Arts & entertainment | music, film, books, news, TV |
| technology | Technology | computers, phones, internet, machines |
| communication | Talking & communication | speaking, writing, asking, opinions |
| shopping_money | Shopping & money | buying, prices, banks, possessions |
| emotions_mind | Feelings & thinking | emotions, personality, thoughts, memory |
| society_politics | Society & politics | government, law, news events, community |
| religion_culture | Culture, customs & beliefs | traditions, holidays, religion, history |
| science_world | Science & the world | basic science, materials, space |

2 hidden buckets — every word must classify somewhere, but these make
terrible decks. They never render in topic view; the words stay reachable
in level view as always:

| slug | display (en) | contents |
|---|---|---|
| abstract_general | General words | very common words belonging to no subject: *thing, way, important, become* |
| function_words | Grammar glue words | the little words that hold sentences together: *the, of, and, but, she, if* — stand-ins for names (*she, it*), position words (*in, on, under*), joining words (*and, but, if*) |

Polyseme rule (a *polyseme* is a word with more than one meaning — *orange*
the fruit and the color): v1 gives each word its ONE most-common meaning's
bucket, reviewers adjudicate disputes; multi-topic membership is a possible
later migration, not v1.

## The learning-science guardrail

The vocabulary-acquisition literature (Tinkham 1993/1997; Waring 1997;
Erten & Tekin 2008) is consistent: introducing tight same-category sets
simultaneously — colors, fruits, days of the week — measurably *increases*
confusion between the new words (interference), while loose thematic
grouping is safe-to-helpful. Review-time spaced retrieval (FSRS) is
largely immune; the risk lives at introduction. Hence, all mitigations in
the batch builder, none in the scheduler:

1. **Grain**: the buckets above are broad thematic domains by design —
   there is deliberately no "Colors" deck.
2. **Word-type mixing**: in topic mode the ranked CTE partitions by part
   of speech (word types: thing-words/nouns, action-words/verbs,
   describing-words/adjectives) instead of by level, so *Food & drink*
   teaches *bread, cook, delicious* rather than five fruits in a row.
   The strongest documented interference is same-type coordinates
   (*peach/plum/cherry*).
3. **Adjacency backstop**: over-fetch ~3× and interleave in Python to cap
   consecutive same-(topic, word-type) items — covers noun-heavy topics
   where the partition alone degenerates. Default-on, not user-visible.
4. **Default stays mixed**: the dashboard Learn tile never silently
   becomes topic-scoped; topic sessions are the thing you swap *to*.
5. **Telemetry**: stamp whether a word was introduced in a topic vs level
   session so lapse/leech rates can later say whether interference shows
   up in practice (the judges' "measure the harm you mitigate" concern).

## Where topic labels come from

The established maker-checker pipeline, cloned from the AI level estimator
(`level_source` precedent end to end):

- New `-k topics` kind in the content generator: batched classification
  (~50–100 words+glosses per call) against the fixed slug enum via the
  JSON-schema pattern. `UPDATE ... WHERE topic IS NULL` for resumability.
- **Free priors**: kaikki sense topics/categories already sit in the
  downloaded JSONL for ~20 languages; WordNet lexnames for English. The
  African languages and Patois classify from word+gloss alone — decent but
  spot-check-worthy, which is what the review gate is for.
- Everything lands `topic_source='ai'` and rides the review machinery: a
  Topics queue cloned from AiLevelsPanel, an `_INBOX_QUEUES` entry, and —
  critical for reviewer throughput — **bulk confirm by (language, topic)**
  with a sampling expectation (inspect a sample before bulk-confirming,
  not rubber-stamp). Strict-policy languages show no topic decks until
  confirmed; `ai_ok` languages show immediately — the same gate all
  generated content uses.
- Scale and cost: ~170k vocabulary rows across 27 languages ≈ a few
  thousand batched calls — tens of dollars total, phased per language,
  behind the admin panel's existing dry-run cost preview. Small courses
  (jam ~483, xh ~1.2k, yo ~1.6k) tag fully in one run.

## Degrade rules (migrations are owner-applied)

- The `topic` clause is **interpolated into the selector only when the
  column probe passes AND a topic was requested** — a NULL-param clause
  referencing `v.topic` would fail planning on the pre-migration schema.
  Plain level learns must add zero extra queries.
- An unknown/stale topic id degrades to a plain level draw (a cached
  bundle must not 422), and the degrade is logged.
- `GET /topics` returns empty pre-migration; the By-topic toggle renders
  only when the language actually has confirmed topic data — no language
  ever shows an empty or broken topic view.
- Counts shown on topic decks must share the exact candidate CTE the
  learn selector uses (subscriptions, explicit gate, level_source gate,
  re-teachable rule) or the numbers will not reconcile with what Learn
  serves.
- Reseeds are safe with zero seeder changes: BaseSeeder's upsert only
  sets listed columns, so `topic` survives.

## Rollout — three PRs, each under the standing verify/merge bar

1. **Backend lens**: migration file, topic-scoped selector with word-type
   round-robin + adjacency backstop, `GET /topics` summary, degrade tests
   that run the selector against a schema WITHOUT the column.
2. **Classifier + review**: `-k topics` generator with priors, Topics
   review queue + bulk confirm-by-(language, topic), inbox badge, admin
   Content-panel run button with cost preview.
3. **Frontend**: By level | By topic toggle, topic deck rows
   (learned/total within subscribed levels), `?topic=` Learn scoping,
   introduction-context telemetry stamp, i18n ×6.

Owner's part, unchanged in kind from every other feature: `supabase db
push` once, then run the sorting per language from Workspace → Admin →
Content (cost preview shown first), then approve in the review queue or
leave the language on `ai_ok`. No scripts.

## Open items the implementation must answer (from the judge pass)

- Prove with a test that a single-level subscriber (the modal beginner)
  still gets word-type interleaving in a topic batch.
- Name the acceptance criterion for the noun-heavy residual case
  (batch_size 5 + sentence-context drills bound it; say so where the
  backstop lives).
- Bad-run recovery: `WHERE topic IS NULL` resumability hides a
  systematically bad classification run — the review queue is the
  detection surface; bulk-reject by (language, run) needs to exist.
- Pilot criteria for gloss-only languages (sw/yo/ha/xh/jam): what
  reviewer-correction rate disqualifies auto-classification for a course.
