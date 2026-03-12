# Project Research Summary

**Project:** PolyglotSRS
**Domain:** Multi-language spaced repetition system (SRS) with NLP-powered answer validation
**Researched:** 2026-03-12
**Confidence:** MEDIUM (architecture HIGH, stack/features/pitfalls MEDIUM — no live web verification available)

## Executive Summary

PolyglotSRS is a language-learning SRS platform occupying a genuine market gap: Bunpro-depth UX extended across Russian, Arabic, and English with NLP-powered morphological answer validation. Competitors either cover many languages shallowly (Memrise, Clozemaster) or go deep on a single language (Bunpro for Japanese, WaniKani for Japanese). The core architectural challenge is integrating three CPU-bound NLP backends (pymorphy3, camel-tools, spaCy) into an async Python API without blocking the event loop, while supporting RTL Arabic rendering, Unicode-correct answer comparison across three scripts, and a provably correct SRS scheduling algorithm.

The recommended stack is FastAPI + asyncpg + Supabase PostgreSQL on the backend and React/Vite/Tailwind on the frontend — a well-understood pairing with no exotic dependencies except the NLP layer. The architecture follows a layered pattern: Routers → Services (SRS, Parser, Enrichment) → NLP Layer (Strategy/Registry pattern) → Repository functions → asyncpg pool → Supabase. The NLP abstraction is the most important architectural decision: a `BaseNLP` abstract class with language-specific subclasses means adding a fourth language requires one new file, not changes across the codebase.

The critical risks are operational, not conceptual. Arabic RTL support is a front-end rewrite if added after the fact — it must be baked into the component library from the first component. Supabase RLS policies have documented gaps in the spec (missing `WITH CHECK` clauses) that would allow data leaks if not corrected before any user-facing features ship. The camel-tools models (~1.5GB) must be baked into a multi-stage Docker image or Railway deploys will fail. SM-2 ease factor behavior needs an explicit recovery mechanism or users will hit "ease hell" (review overload) within weeks. Address all five of these before moving to differentiation features.

---

## Key Findings

### Recommended Stack

The backend is Python 3.11+ with FastAPI (async-native, Pydantic v2 integration), asyncpg (direct PostgreSQL connection — 2-5x faster than supabase-py for SRS review loops), and Supabase for managed Postgres + Auth + Storage. Raw SQL via asyncpg is the right call over an ORM because JSONB morphology fields and language-parameterized queries are cleaner without ORM translation overhead. The NLP layer uses pymorphy3 for Russian morphology, camel-tools for Arabic (the only comprehensive open-source Arabic NLP toolkit), and spaCy `en_core_web_sm` for English. The frontend is React 18 + Vite + TypeScript + Tailwind, with TanStack Query for server state and zustand for SRS session state.

The main stack risk is version currency: all version numbers are from training data (May 2025 cutoff). camel-tools in particular is less mainstream and needs live PyPI verification before pinning. One critical integration note: use the Supabase PgBouncer pooler URL (port 6543) for asyncpg in production and the direct URL (port 5432) only for migrations. The free tier's 60-connection limit can be hit when asyncpg pool + migrations + Supabase dashboard all connect simultaneously.

**Core technologies:**
- **FastAPI + Uvicorn**: Async Python API — async-native, automatic OpenAPI docs, production-grade
- **asyncpg**: PostgreSQL driver — 2-5x faster than alternatives; direct connection bypasses HTTP overhead
- **Supabase (PostgreSQL 15+)**: Database + Auth + Storage — managed Postgres with RLS, eliminates custom auth
- **pymorphy3**: Russian morphology — lemmatization, POS, aspect analysis; runs locally with small footprint (~30MB)
- **camel-tools**: Arabic NLP — morphological analysis, disambiguation, root extraction; ~1.5GB models
- **spaCy en_core_web_sm**: English NLP — industry standard, 12MB, sufficient for lemma + POS
- **React 18 + Vite + TypeScript**: Frontend — standard SPA stack, Tailwind RTL variant for Arabic layout
- **Stripe**: Subscriptions — per-language pricing maps cleanly to Stripe Products/Prices

### Expected Features

The product requires two categories of features: table stakes that match or exceed Anki/Bunpro expectations, and differentiators that justify the existence of the platform over those incumbents.

**Must have (table stakes):**
- SM-2 SRS scheduling with quality rating buttons — the core loop every SRS user expects
- Typed fill-in-the-blank drills — active recall vs. passive card flipping
- RTL support for Arabic — non-negotiable; broken RTL means instant user loss
- On-screen Cyrillic + Arabic keyboards — desktop users cannot type without them
- Streak tracking + due card count on dashboard — the daily hook that drives retention
- Mobile-responsive design — most SRS review happens on phones
- Audio pronunciation (Forvo + Web Speech API fallback) — users expect to hear words
- Example sentences via Tatoeba — context is required; raw vocab cards lose to competitors
- CEFR progress tracking — users need to feel advancement
- Supabase Auth (email + Google OAuth) — cloud sync is expected

**Should have (differentiators):**
- 4-tier NLP answer validation (exact → normalized → lemma → morphological family) — the core moat; no competitor does this
- Aspect partner detection for Russian (imperfective/perfective feedback) — unique; explains the most common Russian learner error
- Arabic verb form feedback (Form I-X with root display) — unique; addresses the hardest part of Arabic vocabulary
- Tashkeel-aware validation (accept with/without diacritics) — removes a major friction point
- Morphology display on cards (gender, case, root, form) — WaniKani-style but for Russian/Arabic
- Note import → auto card extraction via Claude API (Markdown + PDF) — paid feature, major time-saver
- Per-language subscriptions via Stripe — lower barrier to entry than all-or-nothing pricing

**Defer (v2+):**
- UI language localization (Arabic/Russian interface) — high effort, validate market first
- PWA + offline review mode — v2 after core loop is stable
- Listening comprehension mode — audio-input complexity, already marked out-of-scope in spec
- Conjugation/declension table pages — nice-to-have, not core to SRS loop
- Word-by-word breakdown toggle — requires pre-computed data pipeline, add after content is stable

### Architecture Approach

The architecture follows a clean 5-layer stack: React/Vite frontend (Vercel) → FastAPI routers (Railway) → Services + NLP Layer + External APIs → Repository functions → Supabase PostgreSQL. The most architecturally significant pattern is the NLP Strategy + Registry: a `BaseNLP` abstract class with `analyze()`, `normalize()`, `lemmatize()`, `get_morphological_family()`, and `check_answer()` methods. Language-specific backends (RussianNLP, ArabicNLP, EnglishNLP) are registered once at startup in an `NLP_BACKENDS` dict. Since NLP is CPU-bound and synchronous, it is called from async endpoints via `asyncio.to_thread()`. The SRS state is server-authoritative (the client never computes intervals). The session state lives entirely on the client (zustand store), keeping the server stateless between requests.

**Major components:**
1. **NLP Layer (Strategy + Registry)** — `BaseNLP` ABC with language-specific subclasses; loaded once at startup; called via thread executor from async context
2. **Repository Layer** — module-level async functions over asyncpg; raw SQL with parameterized queries; no ORM; transactions for multi-table writes (review submission updates `user_cards` + inserts into `review_log`)
3. **Services/SRS** — pure SM-2 functions with no I/O; called synchronously from async routers after repository fetches card state
4. **Seed + Enrichment Pipeline** — separate CLI scripts (not API endpoints); Download → Transform → Load pattern; enrichment (Wiktionary/Forvo/Tatoeba) is a separate incremental pass after base seeding
5. **Frontend Review Session** — card queue fetched once at session start; separate `/check` (NLP validation) and `/submit` (quality rating + SRS update) endpoints; `useReviewSession` hook holds session state

### Critical Pitfalls

1. **SM-2 ease factor death spiral** — Add an ease recovery mechanism (after 3 consecutive correct answers on a low-ease card, bump EF by 0.15) and interval fuzzing (5% random jitter) from day one in the SRS engine. Without this, 20-40% of mature cards become trapped at minimum ease, causing review overload and churn.

2. **Supabase RLS policy gaps** — The spec uses `FOR ALL USING (auth.uid() = user_id)` which lacks `WITH CHECK` for writes. Split into per-operation policies with explicit `WITH CHECK` clauses. Public tables (vocabulary, grammar_points) need a `USING (true)` read policy or they return no rows to authenticated users. Write RLS integration tests with two test users before shipping any user-facing feature.

3. **Arabic RTL is not just `dir="rtl"`** — Mixed-direction text (Arabic + English on the same card), CSS directional properties, bidirectional form inputs, and mirrored icons all require explicit handling via Tailwind logical properties (`ms-*`/`me-*`), `<bdi>` elements, `dir="auto"` on inputs, and `rtl:scale-x-[-1]` for icons. Must be built into the component library from the first component — retrofitting is a rewrite.

4. **camel-tools 1.5GB model must be baked into Docker image** — Do NOT download at container start. Use a multi-stage Docker build to bake only the MSA model (`morphology-db-msa-r13`, ~300-500MB) into the image. Cold-start downloads on Railway will time out or hit memory limits.

5. **Unicode normalization across three scripts** — Apply `unicodedata.normalize('NFC', text)` to ALL user input AND all stored correct answers before any comparison. Cyrillic/Latin homoglyphs (visually identical but different codepoints) will cause valid answers to be marked wrong. This must be the first step in every `check_answer` pipeline.

---

## Implications for Roadmap

Based on the dependency chains identified in ARCHITECTURE.md and the critical path from FEATURES.md, the following phase structure is recommended.

### Phase 1: Foundation — Schema, Infrastructure, and NLP Backends

**Rationale:** Everything else depends on the database schema and NLP backends. Schema + RLS policies must be correct before any user data touches the database. NLP backends are pure computation with no I/O dependencies, so they can be built in parallel with schema work. camel-tools Docker strategy must be solved before any deployment attempts — this is infrastructure, not a feature.

**Delivers:** Correct PostgreSQL schema with RLS policies, asyncpg connection pool wired to FastAPI lifespan, all three NLP backends (RussianNLP, ArabicNLP, EnglishNLP) implementing BaseNLP, SM-2 pure functions with ease recovery + interval fuzzing, Alembic migration setup, multi-stage Docker build with camel-tools models baked in.

**Addresses:** Auth foundation (Supabase), database tables, NLP abstraction layer, SRS algorithm

**Avoids:** RLS policy gaps (Pitfall 3), schema drift without migrations (Pitfall 6), camel-tools deploy failure (Pitfall 4), SM-2 ease hell (Pitfall 1), Unicode normalization bugs (Pitfall 7), async NLP anti-pattern (async NLP backends)

**Research flag:** camel-tools version and exact model name (`morphology-db-msa-r13`) should be verified against current documentation before implementation. pymorphy3 Python 3.11+ compatibility should also be confirmed.

### Phase 2: Core Data — Seed Data Pipeline

**Rationale:** Review sessions require content to review. Seeder scripts depend on the NLP backends (Phase 1) to generate morphology JSONB during transform. Aspect partner data (critical for Russian WRONG_FORM detection) must be loaded from OpenRussian before answer validation is testable end-to-end. This phase has no frontend dependency.

**Delivers:** Vocabulary and grammar_points tables populated for Russian (OpenRussian TSV), Arabic (Arabic Wordnet + frequency list), and English (COCA + WordNet). drill_sentences seeded from Tatoeba. Aspect partner data loaded into Russian vocabulary morphology JSONB. NLP analysis (lemma, morphology) run on all seed records at load time.

**Addresses:** Content availability, aspect partner lookup table for Russian, frequency_rank for Clozemaster-style ordering

**Avoids:** Aspect partner detection gap (Pitfall 9 — pymorphy3 does not provide aspect partners, must come from OpenRussian)

**Research flag:** Standard ETL patterns — no additional research needed. OpenRussian, Arabic Wordnet, and COCA data formats are well-documented.

### Phase 3: Core Loop — Review Session API and Frontend

**Rationale:** This is the product. All Phase 1 and Phase 2 work exists to make this phase possible. The review session is the daily hook — without it there is no product to validate. Build the backend API (/due, /check, /submit, /session-summary) and the full frontend review UI including RTL support and on-screen keyboards. RTL infrastructure must be built here, not retrofitted later.

**Delivers:** Full review session loop: fetch due cards → display card with drill sentence → typed answer with 4-tier NLP validation → quality rating → SM-2 update persisted. Dashboard with due counts and streak. RTL support baked into Tailwind component library. On-screen Cyrillic and Arabic keyboards. Session summary. Supabase auth integrated end-to-end.

**Addresses:** SRS review session, 4-tier NLP answer validation, fill-in-the-blank drills, RTL support, on-screen keyboards, dashboard, authentication, aspect/form feedback for Russian and Arabic

**Avoids:** Client-side SRS computation (keep server-authoritative), RTL retrofit (build from first component), camel-tools ambiguous analysis (Pitfall 8 — use POS-guided analysis selection or disambiguator), taa marbuta over-normalization (Pitfall 13 — treat as CORRECT_SLOPPY not CORRECT), naïve English morphological family (Pitfall 10 — use lemminflect), run_in_executor thread pool exhaustion (Pitfall 14 — configure dedicated NLP ThreadPoolExecutor)

**Research flag:** Needs research on `simple-keyboard` React library for on-screen keyboards (Pitfall 19 recommends existing library over custom). lemminflect API for English morphological family generation (Pitfall 10 fix) should be confirmed. Arabic MorphDisambiguator API in current camel-tools should be verified (Pitfall 8).

### Phase 4: Content Quality — Enrichment and Browse

**Rationale:** Once the core loop is working, content quality becomes the retention driver. Enrichment (Wiktionary definitions, Forvo audio, Tatoeba examples) makes cards feel complete. Browse/search enables content discovery beyond the SRS queue. Both are additive — they do not change the core data model.

**Delivers:** Incremental enrichment script (Wiktionary + Forvo + Tatoeba, rate-limited, resumable). Audio URLs cached in database (never call Forvo twice). Web Speech API fallback for audio. Browse grammar and vocabulary pages with CEFR filtering and search. Per-language search with alef normalization. Morphology display on vocabulary cards.

**Addresses:** Audio pronunciation, example sentences, definitions, progress tracking, browse/search, CEFR levels

**Avoids:** Forvo rate limit exhaustion (Pitfall 15 — cache-first, build Web Speech fallback immediately), Wiktionary inconsistent HTML (Pitfall 16 — per-language parsers, raw storage in JSONB)

**Research flag:** Standard API integration patterns — no additional research needed.

### Phase 5: Monetization — Stripe Subscriptions and Note Import

**Rationale:** Revenue and the paid-tier differentiator. Stripe integration gates the note import feature (Claude API costs money, must be behind paywall) and per-language access. Note import is Phase 2 per FEATURES.md because it is a paid differentiator that requires working core loop (Phase 3) to be useful.

**Delivers:** Stripe per-language subscription Products/Prices. Subscription status check middleware (gate free-tier language access to 1 language, 20 cards/day). Stripe webhook handling (idempotent, timestamp-ordered). Customer portal for self-service management. Note import pipeline: Markdown/PDF upload → PyMuPDF text extraction → Claude API card extraction → vocabulary/grammar tables. Import gated behind paid subscription.

**Addresses:** Per-language subscriptions, note import, paid tier access gating, CEFR progress heatmap

**Avoids:** Stripe webhook race conditions (Pitfall 17 — idempotent handlers with event timestamp ordering), PDF non-Latin extraction failures (Pitfall 18 — use pymupdf, warn users Markdown is more reliable)

**Research flag:** Claude API prompt engineering for card extraction from unstructured notes may need iteration. Stripe per-language pricing model (multiple Products vs. one Product with multiple Prices) should be confirmed against current Stripe docs.

### Phase 6: Polish — Session Stats, Progress, and Performance

**Rationale:** Post-launch retention features. Session summary statistics, progress heatmap, and CEFR advancement visualization make the product feel complete and reward continued use. Performance tuning (query indexes, connection pool sizing, NLP memory profiling) ensures the product can scale.

**Delivers:** Session summary statistics (accuracy, time spent, streak). Review history heatmap (recharts). CEFR level progress bars. Memory profiling of three NLP models under load (Pitfall 12 — budget Railway RAM tier accordingly). Query optimization (composite index on `user_id + next_review`, EXPLAIN ANALYZE on due-card query). Monitoring query: cards at minimum ease factor per user.

**Addresses:** Progress tracking, session feedback, retention features, scalability baseline

**Avoids:** Railway OOM with three NLP models (Pitfall 12 — profile and upgrade RAM tier as needed), review clustering (verify interval fuzzing from Phase 1 is working in production data)

**Research flag:** Standard patterns — no additional research needed.

### Phase Ordering Rationale

- Foundation before everything: schema + NLP backends have zero cross-dependencies but everything else depends on them
- Seed data before review session: the review loop needs content; Russian aspect partners must be in the database before NLP answer validation is testable
- Core loop before monetization: cannot gate features behind payment until features exist
- RTL infrastructure in Phase 3 (core loop), not as a separate phase: the pitfalls research is unambiguous that RTL retrofitting is a rewrite — it must be part of the first frontend work
- Enrichment before note import: content quality features are lower risk and validate the data pipeline before adding Claude API costs
- Performance polish last: premature optimization, but worth a dedicated phase before marketing the product

### Research Flags

Phases likely needing `/gsd:research-phase` during planning:

- **Phase 1:** camel-tools current version, exact model name, and Python 3.11+ compatibility need live verification before pinning in requirements.txt. pymorphy3 maintenance status (community fork) also needs checking.
- **Phase 3:** `simple-keyboard` React library API, lemminflect current API for spaCy integration, camel-tools MorphDisambiguator current API — all need live doc verification before implementation.
- **Phase 5:** Stripe per-language subscription data model (Products vs. Prices structure) and Claude API card extraction prompt strategy both benefit from targeted research.

Phases with standard, well-documented patterns (can skip research-phase):

- **Phase 2:** ETL from OpenRussian/Arabic Wordnet/COCA — standard file processing, no API research needed
- **Phase 4:** Wiktionary REST API, Forvo API, Tatoeba API — all have stable public documentation
- **Phase 6:** recharts charting, asyncpg query optimization, Railway resource configuration — established patterns

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | Core choices (FastAPI, asyncpg, React, Tailwind) are HIGH confidence. NLP library versions (camel-tools, pymorphy3) are LOW — less mainstream, training data only, need live PyPI verification |
| Features | MEDIUM | Feature set derived from project specs (HIGH confidence) + competitor knowledge from training data (MEDIUM — no live verification of current competitor features) |
| Architecture | HIGH | Derived directly from detailed product specs + well-established FastAPI/asyncpg/PostgreSQL patterns. Strategy+Registry pattern for NLP abstraction is sound and testable |
| Pitfalls | HIGH for well-known issues (SM-2, RLS, Unicode, RTL) / MEDIUM for library-specific issues (camel-tools thread safety, Railway memory limits) | SM-2 behavior, RLS policy structure, Unicode BiDi, and SQL migration discipline are documented facts. camel-tools specifics need live verification |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **camel-tools MSA model name and size:** The model identifier `morphology-db-msa-r13` and the ~300-500MB size estimate for MSA-only (vs. ~1.5GB for all models) need verification against current camel-tools documentation before building the Dockerfile.
- **pymorphy3 maintenance status:** pymorphy3 is a community fork of pymorphy2. Verify it is actively maintained and compatible with Python 3.11+ before committing to it as the Russian NLP backend.
- **Railway memory and image size limits:** Training data shows ~512MB RAM on free tier and ~8GB image limit. These change. Verify current limits before designing the deployment architecture.
- **Supabase connection pooler behavior:** The PgBouncer setup (port 6543 for pooler, port 5432 for direct) may have changed. Verify against current Supabase documentation.
- **Aspect partner data completeness in OpenRussian:** The OpenRussian TSV includes `aspect_partner_id` — but coverage may be incomplete. Plan for a supplementary curated aspect partner list if OpenRussian coverage is < 80% for common verbs.
- **English inflection library:** The spec's naive English morphological family (string concatenation) is wrong. `lemminflect` is the recommended fix — confirm it works with spaCy 3.7+ before adding to dependencies.

---

## Sources

### Primary (HIGH confidence)
- `polyglot-srs-spec.md` — schema, backend structure, API integrations, component inventory
- `answer-validation-spec.md` — 4-tier validation pipeline, per-language edge cases, NLP code sketches
- `PROJECT.md` — constraints, technology decisions, out-of-scope boundaries
- SM-2 algorithm (Wozniak/SuperMemo) — well-documented, stable since 1987

### Secondary (MEDIUM confidence)
- Training data knowledge of FastAPI, asyncpg, React, Tailwind, Stripe, Supabase — mainstream libraries, patterns well-documented
- Training data knowledge of Anki, Bunpro, WaniKani, Clozemaster — competitive feature comparisons
- camel-tools (CAMeL Lab documentation) — training data knowledge, needs live verification
- pymorphy3 documentation — training data knowledge, less mainstream than pymorphy2

### Tertiary (LOW confidence)
- Railway resource limits (memory, image size) — training data, subject to change; verify before deployment
- Tailwind v4 status — training data indicates release early 2025; verify stability before adopting over v3.4
- Supabase PgBouncer port configuration — training data; Supabase infrastructure changes; verify before configuring asyncpg

---
*Research completed: 2026-03-12*
*Ready for roadmap: yes*
