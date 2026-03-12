# PolyglotSRS

## What This Is

A web-based spaced repetition learning platform supporting Russian, Arabic, and English from launch. Users import their own notes (Markdown + PDF), get them auto-parsed into grammar and vocabulary cards, and study via SRS review and fill-in-the-blank drills with language-aware answer validation. Modeled on Bunpro's UX. Built to host, monetize, and scale — each language is a "pack" users subscribe to independently.

## Core Value

Smart SRS review loop with language-aware answer checking — users type answers and get nuanced feedback (correct / sloppy / wrong form / wrong) powered by per-language NLP backends, not naive string comparison.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Supabase schema with RLS policies, language-parameterized throughout
- [ ] SM-2 SRS algorithm (language-agnostic, Anki-compatible)
- [ ] 4-tier answer validation: exact → normalized → lemma → morphological family
- [ ] Russian NLP backend (pymorphy3): morphology, lemmatization, aspect partner detection, Latin→Cyrillic transliteration fallback
- [ ] Arabic NLP backend (camel-tools): tashkeel stripping, alef normalization, root extraction, verb form detection
- [ ] English NLP backend (spaCy): lemmatization, article stripping, irregular verb handling
- [ ] Fill-in-the-blank drill mode with language-aware checking
- [ ] SRS review session (Bunpro-style card queue, quality rating)
- [ ] Markdown note import → auto card extraction via Claude API
- [ ] PDF note import → auto card extraction
- [ ] Russian seed data from OpenRussian TSV dumps (100k+ words)
- [ ] Arabic seed data from Arabic Wordnet + OpenSubtitles frequency list
- [ ] English seed data from COCA + WordNet
- [ ] Wiktionary integration (definitions, inflection tables, cached in DB)
- [ ] Forvo audio integration (with Web Speech API fallback)
- [ ] Tatoeba example sentences integration
- [ ] RTL layout support for Arabic (dir="rtl", Noto Naskh Arabic font)
- [ ] Per-language dashboard (due cards, streak, heatmap, CEFR progress)
- [ ] Supabase Auth (email + Google OAuth)
- [ ] Stripe subscriptions (per-language pricing + all-access tier)
- [ ] On-screen keyboards (Cyrillic + Arabic)

### Out of Scope

- Mobile native app — web-first, PWA later (v2)
- Real-time multiplayer/social features — not core to SRS value
- User-generated content sharing — v3 after community exists
- Languages beyond Russian/Arabic/English — architecture supports it, but not v1 scope
- Listening comprehension mode — v2 after core review loop is solid

## Context

### Language-Specific Grammar as First-Class Concepts

Each language has unique grammar dimensions that must be deeply modeled, not treated as afterthoughts. As more languages are added, the system must capture each language's grammar family and structural features:

- **Russian**: Verb aspect pairs (imperfective/perfective), 6 grammatical cases, 3 declension patterns, gender (m/f/n), animacy. Answer validation must understand aspect partners and case inflections.
- **Arabic**: Dual number (not just singular/plural), 3 cases, verb forms I-X, broken plurals vs sound plurals, trilateral root system (ك-ت-ب), tashkeel (diacritics) as learning aid. Never fail on diacritic presence/absence.
- **English**: Irregular verbs (go/went/gone), phrasal verbs, article system (the/a/an — hardest for Russian/Arabic speakers). Accept British and American spellings.

The `morphology JSONB` field on vocabulary stores language-specific features. The NLP abstraction layer (`BaseNLP`) defines the interface; each language backend implements analysis, lemmatization, morphological family enumeration, and answer checking with language-appropriate rules.

### Initial Users & ESL Strategy

Initial users are the founder's Arabic and Russian-speaking friends learning English (ESL), plus the founder learning Russian and Arabic. The platform serves both directions from day one. English pack is positioned for ESL learners — definitions, translations, and drill prompts must render in the learner's native language, not English-only. Supported UI/native languages for ESL: Russian, Arabic, Spanish, and Portuguese. A translations table stores vocabulary definitions per UI language.

### Progressive Grammar Curriculum (Bunpro Model)

The content model is Bunpro-style progressive grammar, not flat vocabulary lists. Like Bunpro structures Japanese around JLPT levels (N5→N1), each language needs grammar concepts ordered by CEFR level with prerequisite chains. Each grammar point requires multiple varied drill sentences testing the concept in different contexts — comprehension, not rote memorization. Grammar curriculum sourcing (what concepts at what level, what order, what example sentences) is an open research question for each language and should be investigated during the relevant phase.

### Seed Data Strategy

Baseline language data is downloaded from open sources (OpenRussian, Arabic Wordnet, COCA/WordNet), transformed to fit our schema, and stored in our Supabase database. Scripts handle download → transform → load. Data lives in our DB shaped for our needs, not as raw external dumps.

### Existing Specs

- `polyglot-srs-spec.md` — full product spec with schema, API integrations, backend/frontend structure
- `answer-validation-spec.md` — 4-tier answer validation system with per-language edge cases

## Constraints

- **Stack**: FastAPI (Python 3.11+) + React/Vite/Tailwind + Supabase (PostgreSQL + Auth) + Stripe — per spec
- **DB access**: Raw `asyncpg` with thin repository pattern — no ORM overhead, closest to SQL
- **Async**: Async for I/O (DB, HTTP); sync for CPU-bound NLP (pymorphy3, camel-tools, spaCy). Use `run_in_executor` when calling NLP from async context
- **camel-tools deploy**: Bake model data (~1.5GB) into Docker image for predictable Railway deploys
- **Russian NLP**: pymorphy3 (local, no API quota)
- **Arabic NLP**: camel-tools (MSA morphology + root extraction)
- **English NLP**: spaCy en_core_web_sm
- **Hosting**: Vercel (frontend) + Railway (backend)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Raw asyncpg over SQLAlchemy/supabase-py | Best performance with FastAPI, no ORM overhead, full SQL control | — Pending |
| Sync NLP backends, async I/O | NLP is CPU-bound (pymorphy3, camel-tools, spaCy); async adds complexity without benefit for local computation | — Pending |
| Bake camel-tools models into Docker | Predictable deploys on Railway; avoids 1.5GB cold-start download | — Pending |
| PolyglotSRS as v1 name | Most descriptive and clear; can rebrand later | — Pending |
| Seed data transformed into own DB | Baseline language data lives in Supabase shaped for our schema, not raw external dumps | — Pending |
| Language grammar as first-class | Each language's unique grammar dimensions (aspect pairs, duals, cases) modeled in schema and NLP layer, not bolted on | — Pending |

---
*Last updated: 2026-03-12 after initialization*
