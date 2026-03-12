# Phase 1: Schema, Auth, and SRS Engine - Context

**Gathered:** 2026-03-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Database foundation with RLS, Supabase Auth, and SM-2 scheduling algorithm. Users can create accounts, authenticate, and the system can schedule SRS reviews against a correct, secured database. No frontend in this phase — backend and schema only.

</domain>

<decisions>
## Implementation Decisions

### Schema Extensions
- **Translations table**: Claude's discretion on structure (separate table vs JSONB). Must support multiple translations per vocabulary item per UI language (en, ru, ar, es, pt).
- **User profiles**: Claude's discretion on where user settings live (dedicated table vs Supabase auth metadata). Must store: batch_size, ui_language, active_language_id.
- **Content subscriptions**: Claude's discretion on structure (join table vs JSONB). Must track which grammar/vocab level lists a user is subscribed to within a language.
- **Content lists**: Claude's discretion on whether lists are explicit DB rows or implicit from data grouping. Must support subscribing to e.g. "A1 Grammar (Russian)".

### Auth & Onboarding Flow
- After signup, user sees a **language picker** to select their first language to study
- Users **manually select** which grammar/vocab level lists to subscribe to (no auto-subscribe to A1)
- Users can study **multiple languages simultaneously** and switch freely between them — each language has its own dashboard/subscriptions
- UI language detection: Claude's discretion (browser locale detection with settings override is recommended)

### SM-2 Tuning & Quality Mapping
- **No quality rating buttons** — this is Bunpro-style, not Anki-style
- User types answer → NLP validates automatically → SRS scheduling is fully automatic
- CORRECT → card advances, next card. WRONG → show grammar explanation, examples, correct answer
- User can retry a wrong answer (with warning "not recommended unless it was a mistake") before moving to next card
- Quality auto-derived from AnswerResult: CORRECT=4(Good), CORRECT_SLOPPY=3(Hard), WRONG_FORM=2(user can retry or accept fail), WRONG=1(Again)
- **Ease floor + recovery**: Standard 1.3 floor PLUS gradual ease recovery (5+ consecutive correct → ease nudges toward 2.5) to prevent permanent "ease hell"
- Initial intervals: Claude's discretion (standard SM-2: 1 day, 6 days, then EF)

### Migration Strategy
- Migration tool and approach: Claude's discretion (evaluate dbmate, Supabase CLI migrations, or raw numbered SQL files for best fit with raw asyncpg + Supabase)
- Supabase integration: Claude's discretion on whether to use Supabase CLI migrations or manage independently
- Seed data (language rows ru/ar/en): Claude's discretion on whether in migration files or separate scripts
- **Three environments**: dev (local) + staging (Supabase project) + prod (Supabase project)

### Claude's Discretion
- Schema extension structural choices (translations table format, user profile location, subscriptions format, content lists approach)
- Migration tooling selection
- UI language detection approach
- Initial SM-2 intervals
- Seed data location (migration vs separate script)

</decisions>

<specifics>
## Specific Ideas

- "Just like Bunpro. They don't choose a number. They enter their answer and it gets sorted based on if they are right or wrong."
- Users see grammar explanation + examples + correct answer when wrong — this is a learning moment, not just a failure indicator
- Retry option exists but is explicitly discouraged ("not recommended unless it was a mistake")
- The Bunpro model: Learn adds new items from manually-subscribed lists; Review drills SRS queue. No quality buttons — everything is automatic.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project, no existing code

### Established Patterns
- polyglot-srs-spec.md has the base schema (can be used as starting point, but needs extensions)
- answer-validation-spec.md defines AnswerResult enum and check_answer flow

### Integration Points
- Schema must support all NLP validation flows from answer-validation-spec.md
- user_cards table is the bridge between SRS engine and review sessions
- Languages table is referenced by nearly every other table

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-schema-auth-and-srs-engine*
*Context gathered: 2026-03-12*
