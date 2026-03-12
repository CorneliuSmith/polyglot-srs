# Domain Pitfalls

**Domain:** Multi-language SRS learning platform (Russian, Arabic, English)
**Researched:** 2026-03-12
**Overall confidence:** MEDIUM (training data only -- WebSearch unavailable for verification)

---

## Critical Pitfalls

Mistakes that cause rewrites, data corruption, or security breaches.

---

### Pitfall 1: SM-2 Ease Factor Death Spiral

**What goes wrong:** The SM-2 ease factor formula progressively punishes cards a user struggles with. Each "Again" (quality 0-2) drops the ease factor, and the 1.3 floor means once a card hits minimum ease, it stays there permanently -- the card shows up constantly but the user never recovers. Anki calls this "ease hell." Over weeks, a significant percentage of a user's deck becomes trapped at 1.3 ease, causing review overload and user churn.

**Why it happens:** The spec's SM-2 implementation uses the standard Wozniak formula: `EF = max(1.3, EF + 0.1 - (5-q) * (0.08 + (5-q) * 0.02))`. A quality=0 response drops EF by 0.8. It takes eight consecutive quality=5 responses to recover 0.8 of EF. Users rarely give eight perfect responses in a row on a card they already struggle with.

**Consequences:**
- 20-40% of mature cards stuck at 1.3 EF after months of use
- Daily review counts inflate, session times grow, users quit
- Users blame themselves ("I'm bad at this") rather than the algorithm

**Prevention:**
1. Add an ease recovery mechanism: after 3 consecutive correct answers on a low-ease card, bump EF by 0.15 (Anki's "Easy Bonus" concept)
2. Never let EF drop below 1.3 (already in spec -- good), but consider 1.5 as the practical floor with a gradual recovery to 2.5
3. Track cards at minimum EF per user and surface a "struggling cards" dashboard widget
4. Consider FSRS (Free Spaced Repetition Scheduler) as a future upgrade path -- it uses machine learning on actual review history and dramatically outperforms SM-2, but adds complexity

**Detection:** Monitor: `SELECT COUNT(*) FROM user_cards WHERE ease_factor <= 1.35 AND repetitions > 10`. If more than 25% of a user's mature cards hit this, the algorithm is failing them.

**Phase relevance:** Address in the SRS engine phase. Build with SM-2 but add the recovery mechanism from day one. Log review data granularly so FSRS migration is possible later.

**Confidence:** HIGH -- this is the most well-documented SM-2 limitation, confirmed by Anki community, SuperMemo forums, and the FSRS research papers.

---

### Pitfall 2: SM-2 Interval Rounding Creates Review Clustering

**What goes wrong:** `round(interval * ease_factor)` can produce the same integer for nearby cards. If a user adds 50 cards on day 1, many will cluster to the same review dates. Day 7 might have 40 due cards, day 8 has 2, then day 14 has 38 again.

**Why it happens:** Integer rounding of `interval * 2.5` means many different starting intervals converge. Cards with intervals 2 and 3 both round to 5 or 6 after the first multiplication.

**Consequences:**
- Spiky review loads (40 cards one day, 5 the next)
- Users skip heavy days, compounding the backlog
- Feels unfair and unpredictable

**Prevention:**
1. Add interval fuzzing: `interval = round(interval * EF * uniform(0.95, 1.05))` -- a 5-10% random jitter spreads cards across days
2. Cap daily new cards (the spec mentions 20/day for free tier -- enforce this for paid too as a default with user override)
3. Store interval as float internally, only round for display. Use `next_review` timestamp with hour-level precision, not just date

**Detection:** `SELECT DATE(next_review), COUNT(*) FROM user_cards WHERE user_id = $1 GROUP BY 1 ORDER BY 2 DESC` -- if top day has 5x the median, clustering is occurring.

**Phase relevance:** SRS engine phase. Implement fuzzing in the initial `sm2_update` function.

**Confidence:** HIGH -- standard Anki/SM-2 knowledge.

---

### Pitfall 3: Supabase RLS Policy Gaps Leak User Data

**What goes wrong:** The spec defines `FOR ALL USING (auth.uid() = user_id)` on user tables. This is a start, but has gaps:
- `FOR ALL` combines SELECT, INSERT, UPDATE, DELETE into one policy. A user could UPDATE another user's row if they know the UUID, because `USING` only filters reads -- `WITH CHECK` is needed for writes.
- Service role key in the backend bypasses RLS entirely. If the backend ever passes the service role key to the client, all RLS is void.
- The `languages`, `grammar_points`, `vocabulary`, and `drill_sentences` tables have NO RLS in the spec -- they are shared/public data. But if RLS is enabled without a permissive policy, they become invisible to all users.

**Why it happens:** RLS policies are easy to write incorrectly because the mental model is confusing: `USING` controls which rows are visible for SELECT and which rows are affected by UPDATE/DELETE, while `WITH CHECK` controls which rows can be INSERTed or UPDATEd-to. Missing `WITH CHECK` means the default is to reject all writes.

**Consequences:**
- User A reads User B's review history, subscription status, or imported notes
- Users cannot insert their own cards because `WITH CHECK` is missing
- Public tables (languages, vocabulary) return empty results to authenticated users

**Prevention:**
1. Split policies by operation:
   ```sql
   -- READ
   CREATE POLICY "users_read_own" ON user_cards FOR SELECT USING (auth.uid() = user_id);
   -- WRITE
   CREATE POLICY "users_write_own" ON user_cards FOR INSERT WITH CHECK (auth.uid() = user_id);
   CREATE POLICY "users_update_own" ON user_cards FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
   CREATE POLICY "users_delete_own" ON user_cards FOR DELETE USING (auth.uid() = user_id);
   ```
2. For shared/public tables, either do NOT enable RLS, or add a permissive read-all policy:
   ```sql
   CREATE POLICY "public_read" ON vocabulary FOR SELECT USING (true);
   ```
3. NEVER expose the Supabase service role key to the frontend. The backend should use the service role key server-side only and pass the user's JWT for client-side Supabase calls.
4. Write RLS integration tests: create two test users, have User A attempt to read/write User B's data, assert failure.

**Detection:** Automated test suite that runs as User A and attempts `SELECT * FROM user_cards WHERE user_id = [User B's ID]`. Must return 0 rows.

**Phase relevance:** Schema/database phase -- must be correct before any user-facing features. Test immediately.

**Confidence:** HIGH -- well-documented Supabase behavior.

---

### Pitfall 4: camel-tools 1.5GB Model Data Breaks Railway Deploys

**What goes wrong:** `camel_data -i defaults` downloads ~1.5GB of morphology databases. If this runs at container start (or during `pip install`), it will:
- Exceed Railway's build step memory/time limits
- Create non-reproducible builds (download may fail mid-way)
- Cause 60-90 second cold starts if models are downloaded on first request
- Potentially exceed Railway's free tier disk limits (1GB slug by default)

**Why it happens:** camel-tools stores model data in `~/.camel_tools/` by default. The `camel_data` CLI downloads from a remote server. Docker builds that run this as a build step bake it into the image, but the resulting image is 2-3GB+ which is slow to push and pull.

**Consequences:**
- Deploys time out or fail silently
- First Arabic request takes 60+ seconds (or crashes with OOM)
- Railway bills for egress on every deploy if models are re-downloaded

**Prevention:**
1. Multi-stage Docker build: download models in a builder stage, copy only the needed files to the runtime stage
   ```dockerfile
   FROM python:3.11-slim AS builder
   RUN pip install camel-tools && camel_data -i morphology-db-msa-r13

   FROM python:3.11-slim
   COPY --from=builder /root/.camel_tools /root/.camel_tools
   ```
2. Only download the specific model needed (`morphology-db-msa-r13` for MSA analysis), not `defaults` which includes dialect models, NER, sentiment, etc. This cuts size from ~1.5GB to ~300-500MB.
3. Set `CAMEL_TOOLS_DATA` env var to control the data directory location
4. Consider a dedicated model volume on Railway that persists across deploys
5. Test the exact Docker image locally with `docker build` before pushing to Railway

**Detection:** If `docker images | grep polyglot` shows an image over 2GB, models are bloating the build. If Arabic endpoints return 500s with "model not found" errors, the data download failed.

**Phase relevance:** Infrastructure/deployment phase. Must be solved before Arabic NLP integration is testable in production.

**Confidence:** MEDIUM -- camel-tools deployment specifics based on training data. The `morphology-db-msa-r13` model name should be verified against current camel-tools documentation.

---

### Pitfall 5: Arabic RTL Support Is Far More Than dir="rtl"

**What goes wrong:** Developers add `dir="rtl"` and call it done. Then:
- Numbers inside Arabic text display incorrectly (Arabic uses Western digits in many contexts, but Eastern Arabic numerals in others)
- Mixed-direction content (Arabic sentence with an English word) causes "bidi reordering" -- the visual order of characters does not match logical order
- CSS `margin-left` and `padding-right` are backwards -- every spacing utility is inverted
- Text input cursors jump erratically in mixed-direction fields
- Icons that imply direction (arrows, progress bars, navigation) point the wrong way
- Tailwind's `space-x-*` utilities add spacing on the wrong side

**Why it happens:** The Unicode Bidirectional Algorithm (UBiDi) handles character reordering automatically for simple cases, but breaks down with:
- Punctuation at boundaries between RTL and LTR text
- Nested directional contexts (Arabic paragraph containing an English quote containing an Arabic word)
- Form inputs where the user types mixed-direction text

**Consequences:**
- Arabic UI looks broken even when functionally correct
- Users cannot trust what they see in text inputs (cursor position lies)
- Fill-in-the-blank drills with mixed Arabic/English become unusable
- Heatmap, progress bars, and navigation feel "mirrored wrong"

**Prevention:**
1. Use Tailwind's `rtl:` variant prefix for ALL directional properties:
   ```html
   <div class="ml-4 rtl:mr-4 rtl:ml-0">
   ```
   Or better: use logical CSS properties (`margin-inline-start` instead of `margin-left`). Tailwind v3.3+ supports `ms-4` (margin-start) and `me-4` (margin-end).
2. Wrap mixed-direction text with explicit `<bdi>` elements or Unicode direction markers (LRM `\u200E`, RLM `\u200F`) at boundaries
3. For text inputs: set `dir="auto"` on `<input>` elements so the browser auto-detects direction from the first strong character
4. Mirror ALL directional icons (back arrow, chevrons, progress) using `rtl:scale-x-[-1]` or separate RTL icon variants
5. Test with REAL Arabic content, not just "RTL test" placeholder text. Get an Arabic reader to verify.
6. Use `unicode-bidi: isolate` on inline elements that contain text from the opposite direction

**Detection:** Visual QA with actual Arabic sentences in every component. Automated screenshot comparison tests between LTR and RTL modes.

**Phase relevance:** Frontend phase, but must be baked into the component library from the very first component. Retrofitting RTL into an existing LTR-only codebase is a rewrite.

**Confidence:** HIGH -- RTL challenges are extremely well-documented.

---

### Pitfall 6: asyncpg Without ORM Means Manual Migration Discipline

**What goes wrong:** With raw asyncpg and no ORM, there is:
- No automatic migration generation (no `alembic revision --autogenerate`)
- No schema diffing -- the codebase and database silently diverge
- No model-to-table mapping -- Python dataclasses and SQL schema are two separate sources of truth that must be manually synchronized
- Typos in SQL strings are only caught at runtime

**Why it happens:** The spec explicitly chose raw asyncpg for performance. This is a valid trade-off, but the cost is that every schema discipline must be manually enforced.

**Consequences:**
- A column rename in `schema.sql` that is not updated in `repository.py` causes runtime crashes
- Migrations run in wrong order, or are forgotten, leaving dev and prod schemas diverged
- New developers add columns in Python code but forget the SQL migration
- No rollback path for failed migrations

**Prevention:**
1. Use Alembic for migrations even without SQLAlchemy ORM. Alembic supports "raw SQL" migrations:
   ```python
   # alembic/versions/001_add_column.py
   def upgrade():
       op.execute("ALTER TABLE user_cards ADD COLUMN last_quality INT")
   def downgrade():
       op.execute("ALTER TABLE user_cards DROP COLUMN last_quality")
   ```
2. Keep a single `schema.sql` as the source of truth for the full schema. Migrations are incremental changes, but `schema.sql` always reflects the target state.
3. Add a CI check that applies all migrations to an empty database and then diffs against `schema.sql` -- they must produce identical schemas.
4. Use Pydantic models as the Python-side source of truth for column names. Write a helper that validates SQL column names against Pydantic field names at startup.
5. Type-check SQL queries with something like `pgtyped` or at minimum, write integration tests that execute every query against a real (test) database.

**Detection:** If `SELECT column_name FROM information_schema.columns WHERE table_name = 'user_cards'` returns different columns than what the Python code expects, you have schema drift. Catch this in CI.

**Phase relevance:** Database/schema phase. Set up Alembic and the CI check before writing any repository code.

**Confidence:** HIGH -- standard software engineering practice.

---

### Pitfall 7: Unicode Normalization Across Three Scripts

**What goes wrong:** User input in three different scripts (Latin, Cyrillic, Arabic) hits subtle Unicode issues:
- Cyrillic `a` (U+0430) looks identical to Latin `a` (U+0061) but they are different codepoints. A user with a Latin keyboard who types what looks like a Cyrillic word is actually typing Latin characters.
- Arabic text can be NFC or NFD normalized -- the same visual character has multiple byte representations. `dediac_ar` only strips known combining marks, not all decomposed forms.
- Homoglyph attacks: Cyrillic `c` (es) looks identical to Latin `c`. A user typing a Russian word might have one Latin character mixed in.
- Python string `.lower()` is locale-dependent for some edge cases (Turkish dotless i is the classic example, but Cyrillic has similar quirks with the letter yo)

**Why it happens:** Unicode has multiple representations for visually identical characters. Users switch keyboards mid-word, copy-paste from different sources, or use autocorrect that introduces wrong-script characters.

**Consequences:**
- Correct answers marked wrong because of invisible Unicode differences
- User frustration: "I typed exactly the right thing and it said wrong"
- Database duplicates: the same word stored in NFC and NFD forms are different strings

**Prevention:**
1. Apply `unicodedata.normalize('NFC', text)` to ALL user input AND all stored correct answers before any comparison
2. For Russian: detect Latin lookalikes and auto-transliterate. The spec already has transliteration fallback, but extend it: scan for mixed-script strings and warn the user ("Did you mean to type in Cyrillic?")
3. For Arabic: apply `dediac_ar` AFTER NFC normalization, not before. The order matters because decomposed tashkeel may not be recognized by `dediac_ar` in composed form.
4. Store all text in NFC form in the database. Add a CHECK constraint or trigger:
   ```sql
   CREATE OR REPLACE FUNCTION normalize_nfc() RETURNS trigger AS $$
   BEGIN
     NEW.word = normalize(NEW.word, NFC);
     NEW.lemma = normalize(NEW.lemma, NFC);
     RETURN NEW;
   END;
   $$ LANGUAGE plpgsql;
   ```
   (PostgreSQL 13+ supports the `normalize()` function)
5. Build a `detect_script(text)` utility that flags mixed-script input before it reaches the NLP layer

**Detection:** Test with copy-pasted text from various sources (WhatsApp, Google Translate, PDF extraction). If answers that look correct get rejected, Unicode normalization is the likely cause.

**Phase relevance:** NLP/answer validation phase. Must be the FIRST step in every `check_answer` pipeline, before any language-specific logic.

**Confidence:** HIGH -- Unicode normalization issues are well-understood.

---

## Moderate Pitfalls

---

### Pitfall 8: camel-tools Analyzer Returns Multiple Ambiguous Analyses

**What goes wrong:** `analyzer.analyze(word)` returns a LIST of possible analyses, often 5-15 for a single Arabic word. The spec takes `analyses[0]` -- the first result. But camel-tools does not guarantee ordering by likelihood. The first analysis might be a rare interpretation.

For example, the Arabic root k-t-b could analyze as:
- kutub (books, plural noun)
- kataba (he wrote, past tense verb)
- kuttib (was made to write, passive)

Taking `[0]` arbitrarily picks one.

**Prevention:**
1. Use camel-tools' disambiguator (`CamelTools MorphDisambiguator`) which uses context (surrounding words) to pick the most likely analysis. This requires the full sentence, not just the word.
2. If disambiguation is too heavy, score analyses by: (a) matching the expected POS from the card's `pos` field, (b) matching the expected root from `morphology.root`, (c) frequency heuristics.
3. When displaying morphological info on cards, show the analysis that matches the card's stored metadata, not a fresh re-analysis.

**Detection:** Arabic answer validation incorrectly rejects valid answers or shows wrong grammatical feedback. Test with highly ambiguous Arabic words.

**Phase relevance:** Arabic NLP backend phase.

**Confidence:** MEDIUM -- based on camel-tools training data knowledge. Verify disambiguator API with current docs.

---

### Pitfall 9: pymorphy3 Aspect Partner Detection Is Not Built-In

**What goes wrong:** The spec's `get_aspect_partner` method has a `pass` body with a comment about querying the DB. pymorphy3 does NOT provide aspect partner data. If this is not built as a proper lookup table, Russian aspect checking (a core differentiator) silently does nothing -- all aspect-wrong answers fall through to `WRONG` instead of `WRONG_FORM` with the helpful explanation.

**Prevention:**
1. Build an aspect partner lookup table during seed data ingestion from OpenRussian. The OpenRussian TSV dump includes an `aspect_partner_id` column linking imperfective/perfective pairs.
2. Store aspect partners bidirectionally in the vocabulary table's `morphology` JSONB: `{"aspect": "impf", "partner_lemma": "napisat"}`
3. The `get_aspect_partner` method should query this JSONB field, not rely on pymorphy3
4. Seed this data BEFORE building the answer validation layer so it can be tested end-to-end

**Detection:** Test: answer with an imperfective verb when the perfective is expected. If the result is `WRONG` instead of `WRONG_FORM`, aspect detection is broken.

**Phase relevance:** Russian NLP backend and seed data phases must coordinate. Seed data must come first.

**Confidence:** HIGH -- pymorphy3's API is well-known, and aspect partners are definitively not part of its feature set.

---

### Pitfall 10: English Morphological Family Is Naive in the Spec

**What goes wrong:** The spec's English `get_morphological_family` uses string concatenation: `{lemma, lemma + 's', lemma + 'ed', lemma + 'ing'}`. This produces:
- "go" -> {"go", "gos", "goed", "going"} -- "gos" and "goed" are not words
- "run" -> {"run", "runs", "runed", "runing"} -- wrong doubling, wrong past tense
- "mouse" -> {"mouse", "mouses", "moused", "mousing"} -- misses "mice"

**Prevention:**
1. Use `lemminflect` library (or `pyinflect`) which generates correct inflections from spaCy tokens:
   ```python
   import lemminflect
   doc = nlp("go")
   token = doc[0]
   forms = set()
   for tag in ['VB', 'VBD', 'VBG', 'VBN', 'VBP', 'VBZ']:
       forms.update(token._.inflect(tag) or [])
   # {'go', 'went', 'going', 'gone', 'goes'}
   ```
2. For nouns, use `token._.inflect('NNS')` to get correct plurals (including "mice", "children", "phenomena")
3. Add `lemminflect` to the dependency list

**Detection:** Test irregular verbs: "go/went/gone", "be/was/were/been", "have/had". Test irregular nouns: "mouse/mice", "child/children".

**Phase relevance:** English NLP backend phase.

**Confidence:** HIGH -- the naive approach's failures are obvious by inspection of the spec code.

---

### Pitfall 11: Supabase Auth JWT in Backend Creates Dual-Auth Complexity

**What goes wrong:** The architecture has two auth paths:
1. Frontend uses Supabase client-side auth (JWT from `supabase.auth.signIn()`)
2. Backend FastAPI endpoints need to verify that same JWT

If the backend uses `SUPABASE_SERVICE_ROLE_KEY` to query the database, RLS is bypassed entirely. The backend must forward the user's JWT to Supabase for RLS to work, OR the backend must enforce authorization in application code.

**Prevention:**
1. Choose ONE strategy and be consistent:
   - **Option A (recommended):** Backend verifies the Supabase JWT (using `supabase-py` or manual JWT decode with the Supabase JWT secret), then uses the SERVICE_ROLE key for DB access with manual authorization checks in the repository layer.
   - **Option B:** Backend creates a Supabase client per-request using the user's JWT, so RLS applies automatically. This is simpler but creates a new DB connection per request unless connection pooling is handled carefully.
2. If using Option A, EVERY repository method must include `WHERE user_id = $1` for user-scoped tables. A single missed filter = data leak. Abstract this into a base repository class.
3. Write middleware that extracts and validates the JWT on every authenticated endpoint. Use FastAPI's `Depends()` system.

**Detection:** Call any user-scoped endpoint without auth. If it returns data, auth is broken. Call with User A's token requesting User B's data. If it returns data, authorization is broken.

**Phase relevance:** Auth/schema phase. Must be decided and implemented before any user-facing endpoints.

**Confidence:** HIGH -- standard Supabase + custom backend architecture concern.

---

### Pitfall 12: Railway Memory Limits with Three NLP Models Loaded Simultaneously

**What goes wrong:** Loading pymorphy3 + camel-tools MorphologyDB + spaCy en_core_web_sm simultaneously at startup consumes significant memory:
- pymorphy3: ~50-100MB
- camel-tools MorphologyDB: ~200-500MB (depending on which DB variant)
- spaCy en_core_web_sm: ~50MB
- Python overhead + FastAPI: ~100MB
- Total: potentially 500MB-1GB at idle

Railway's free tier provides 512MB RAM. Even the paid tier starts at 512MB with scaling.

**Prevention:**
1. Lazy-load NLP backends: do not instantiate all three at import time. Load each only when a request for that language arrives, then cache:
   ```python
   _nlp_cache = {}
   def get_nlp(lang: str) -> BaseNLP:
       if lang not in _nlp_cache:
           if lang == "ru":
               _nlp_cache["ru"] = RussianNLP()
           elif lang == "ar":
               _nlp_cache["ar"] = ArabicNLP()
           elif lang == "en":
               _nlp_cache["en"] = EnglishNLP()
       return _nlp_cache[lang]
   ```
2. If memory is still tight, consider running NLP backends in a separate worker process (celery/arq) so the web process stays lean
3. Profile actual memory usage with `tracemalloc` or `memory-profiler` before deploying
4. Budget for Railway's 1GB or 2GB RAM tier for production

**Detection:** Railway logs showing OOMKilled events. Endpoints returning 502/503 intermittently.

**Phase relevance:** Infrastructure/deployment phase. Must be profiled before going to production.

**Confidence:** MEDIUM -- memory estimates are approximate. Actual values depend on model variant.

---

### Pitfall 13: Taa Marbuta Normalization Is Context-Dependent

**What goes wrong:** The spec normalizes taa marbuta to ha. This is an aggressive normalization that conflates genuinely different words:
- "madrasa" (school) ends with taa marbuta
- The same letters with ha could mean "his school" in some dialects
- "wajh" (face) legitimately ends with ha

Normalizing all taa marbuta to ha would make semantically distinct words indistinguishable in answer validation.

**Prevention:**
1. Do NOT normalize taa marbuta by default. Only apply this normalization in a final fallback layer.
2. In the `normalize()` function, handle taa marbuta as a SLOPPY match, not an exact match:
   - If taa marbuta is the only difference, return `CORRECT_SLOPPY` with a note about taa marbuta
   - Do not treat them as identical in the primary comparison
3. Make taa marbuta strictness configurable per user level (lenient for A1-A2, strict for B2+)

**Detection:** Test: correct answer ends with taa marbuta, user types with ha. Should be `CORRECT_SLOPPY`, not `CORRECT`.

**Phase relevance:** Arabic NLP backend phase.

**Confidence:** HIGH -- Arabic linguistic fact.

---

### Pitfall 14: run_in_executor Blocks the Event Loop If Misconfigured

**What goes wrong:** The spec says "use `run_in_executor` when calling NLP from async context." But the default executor is a `ThreadPoolExecutor` with a limited number of workers. If multiple concurrent requests all call NLP (e.g., 10 users submitting Arabic answers simultaneously), the thread pool exhausts and subsequent requests queue up, effectively blocking the event loop.

Additionally, if NLP code uses global mutable state (e.g., a shared `MorphAnalyzer` instance), concurrent threads accessing it may cause race conditions.

**Prevention:**
1. Configure a dedicated thread pool with enough workers for expected concurrency:
   ```python
   import asyncio
   from concurrent.futures import ThreadPoolExecutor
   nlp_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="nlp")

   async def check_answer_async(nlp, user_input, correct, context):
       loop = asyncio.get_event_loop()
       return await loop.run_in_executor(nlp_executor, nlp.check_answer, user_input, correct, context)
   ```
2. Verify thread safety of pymorphy3, camel-tools, and spaCy. pymorphy3's `MorphAnalyzer` is documented as thread-safe. spaCy's `nlp()` is thread-safe for `nlp(text)` calls. camel-tools thread safety is less documented -- consider one instance per thread or use a lock.
3. Set a timeout on executor calls so a stuck NLP analysis does not permanently consume a thread.

**Detection:** Under load testing, response times degrade non-linearly. 10 concurrent requests take 10x longer than 1 request = thread pool exhaustion.

**Phase relevance:** Backend/NLP phase. Design the async bridge before implementing endpoints.

**Confidence:** MEDIUM -- thread safety of camel-tools specifically is uncertain.

---

## Minor Pitfalls

---

### Pitfall 15: Forvo API Free Tier Is 500 Requests/Day

**What goes wrong:** 500 requests/day sounds like enough, but during seed data enrichment, querying audio for even 1000 vocabulary words exhausts the daily limit. Then regular user traffic competes for the remaining quota.

**Prevention:**
1. Cache ALL Forvo responses in the database (`audio_url` column already exists). Never call Forvo twice for the same word.
2. During seed data loading, throttle Forvo requests to 400/day and spread enrichment over multiple days, or batch with a background job.
3. Implement Web Speech API fallback immediately -- do not treat Forvo as the primary audio source.
4. Consider pre-generating TTS audio with an offline TTS engine for seed data.

**Phase relevance:** API integration phase. Build the cache-first pattern from the start.

**Confidence:** HIGH -- Forvo rate limit is well-known.

---

### Pitfall 16: Wiktionary API Returns Inconsistent HTML Across Languages

**What goes wrong:** Wiktionary's REST API returns HTML-formatted definitions, not clean text. The HTML structure differs significantly between language sections. Russian entries have different formatting than Arabic entries. Parsing logic that works for English breaks for Arabic.

**Prevention:**
1. Store raw Wiktionary response in `wiktionary_data JSONB` (already in spec -- good).
2. Write per-language Wiktionary parsers, not one universal parser.
3. Treat Wiktionary as a "nice to have" enrichment, not a required data source. The core vocabulary definitions should come from seed data, with Wiktionary as supplementary.

**Phase relevance:** Enrichment/API integration phase.

**Confidence:** MEDIUM -- based on known Wiktionary API behavior.

---

### Pitfall 17: Stripe Webhook Race Conditions with Subscription Status

**What goes wrong:** Stripe sends multiple webhook events for a single subscription change (e.g., `customer.subscription.created`, `invoice.payment_succeeded`, `customer.subscription.updated`). If the backend processes these out of order, the subscription status can flicker between "active" and "past_due", temporarily locking a user out of their content.

**Prevention:**
1. Use Stripe's `created` timestamp on events to determine ordering. Only update local state if the event is newer than what is stored.
2. Implement idempotent webhook handling using Stripe's event ID.
3. For subscription status checks, always query Stripe as the source of truth (with caching), rather than relying solely on webhook-updated local state.

**Phase relevance:** Monetization/Stripe phase.

**Confidence:** HIGH -- standard Stripe integration challenge.

---

### Pitfall 18: PDF Parsing of Non-Latin Scripts Is Fragile

**What goes wrong:** `pypdf2` (now `pypdf`) extracts text from PDFs, but Arabic and Cyrillic text in PDFs is frequently:
- Stored as glyph IDs without proper Unicode mapping (text extraction returns gibberish)
- Right-to-left reading order scrambled (Arabic words appear reversed)
- Ligatures not decomposed (Arabic connected letters stored as single glyphs)

**Prevention:**
1. Use `pymupdf` (fitz) instead of `pypdf` -- it has significantly better non-Latin text extraction.
2. Add a post-extraction validation step: detect the expected script and reject/warn if the extracted text does not match.
3. For Arabic PDFs specifically, consider OCR fallback (`pytesseract` with Arabic model) when text extraction fails.
4. Clearly communicate to users that PDF import quality varies -- Markdown import is the reliable path.

**Phase relevance:** Note import phase. This is a Phase 2 feature per the spec, so there is time to iterate.

**Confidence:** MEDIUM -- PDF handling specifics may have improved in recent library versions.

---

### Pitfall 19: On-Screen Keyboard State Management

**What goes wrong:** Custom on-screen keyboards (Cyrillic and Arabic) need to:
- Insert characters at the cursor position, not append to the end
- Handle backspace correctly within the virtual keyboard
- Work with the browser's built-in text input (focus, selection, undo)
- Not conflict with physical keyboard input

Building this from scratch is surprisingly complex and fragile across browsers.

**Prevention:**
1. Use an existing virtual keyboard library (e.g., `simple-keyboard` for React) rather than building custom.
2. Use `HTMLInputElement.setRangeText()` for cursor-aware insertion.
3. Test on mobile Safari (iOS) specifically -- it has unique focus/keyboard interaction behavior.

**Phase relevance:** Frontend phase, but can be deferred to a later iteration. Physical keyboard input + system-level keyboard switching is sufficient for MVP.

**Confidence:** MEDIUM -- virtual keyboard libraries may have improved.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation | Severity |
|---|---|---|---|
| Database schema | RLS policies incomplete (Pitfall 3) | Split policies by operation, test with two users | Critical |
| Database schema | Schema drift without ORM (Pitfall 6) | Use Alembic for raw SQL migrations, CI check | Critical |
| SRS engine | Ease factor death spiral (Pitfall 1) | Add recovery mechanism, interval fuzzing | Critical |
| SRS engine | Interval clustering (Pitfall 2) | Add 5% random jitter to intervals | Moderate |
| Russian NLP | Aspect partners not in pymorphy3 (Pitfall 9) | Build lookup table from OpenRussian seed data | Moderate |
| Arabic NLP | camel-tools ambiguous analysis (Pitfall 8) | Use disambiguator or POS-guided selection | Moderate |
| Arabic NLP | Taa marbuta over-normalization (Pitfall 13) | Make normalization context-dependent, not blanket | Moderate |
| English NLP | Naive morphological family (Pitfall 10) | Use lemminflect library | Moderate |
| Answer validation | Unicode normalization (Pitfall 7) | NFC normalize all input before any comparison | Critical |
| Frontend (RTL) | RTL is more than dir="rtl" (Pitfall 5) | Use logical CSS properties, test with real Arabic | Critical |
| Auth/backend | Dual auth complexity (Pitfall 11) | Pick one strategy, enforce consistently | Critical |
| Deployment | camel-tools model size (Pitfall 4) | Multi-stage Docker, download only MSA model | Critical |
| Deployment | Memory with 3 NLP models (Pitfall 12) | Lazy-load, budget 1-2GB RAM on Railway | Moderate |
| API integrations | Forvo rate limit (Pitfall 15) | Cache-first, Web Speech API fallback | Minor |
| Monetization | Stripe webhook races (Pitfall 17) | Idempotent handlers, event timestamp ordering | Moderate |
| Note import | PDF non-Latin extraction (Pitfall 18) | Use pymupdf, OCR fallback, set expectations | Moderate |

---

## Sources

- Project spec: `polyglot-srs-spec.md` (schema, architecture, NLP code)
- Answer validation spec: `answer-validation-spec.md` (validation pipeline, edge cases)
- SM-2 algorithm: Wozniak's original SuperMemo papers (training data knowledge)
- Supabase RLS: Supabase documentation patterns (training data knowledge)
- Unicode BiDi: W3C internationalization guidelines (training data knowledge)
- camel-tools: CAMeL Lab documentation (training data knowledge)

**Note:** WebSearch was unavailable during this research session. All findings are based on project specs and training data. Specific library versions and API behaviors should be verified against current documentation before implementation. Findings marked MEDIUM confidence are most in need of verification.
