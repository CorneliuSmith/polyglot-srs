# Demo checklist

A foolproof path to a working demo, plus what to watch for and report back.

> **Headline languages: Turkish and Spanish.** Both have vocabulary **and**
> grammar **and** a real (mixed) placement test. Every other language has at
> least starter vocabulary once seeded (see §1d for exactly what's where).

---

## 1. One-time setup

### 0. Python — use 3.11 or 3.12 (NOT 3.13/3.14)

The full install pins NLP libraries (camel-tools, spaCy) that don't build on
Python 3.13+. On 3.11/3.12 this works:

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

**On a newer Python (3.13/3.14) — or if the full install fails** — you can
still run the whole demo with a lean install. Everything works except the
heavyweight per-language lemmatizers (grading falls back to string/morphology
matching, which the demo languages barely notice):

```bash
pip install fastapi "uvicorn[standard]" pydantic pydantic-settings asyncpg \
    PyJWT cryptography httpx anthropic redis numpy scipy stripe
pip install nltk   # only needed to seed English (WordNet glosses)
```

Do the steps below **in this order**: env → migrations → (optionally source
fresh data) → seed → run. Seeding before migrations, or running before
seeding, is what produces an app with nothing in it.

### a. Backend env (`.env`)
Copy `.env.example` → `.env` and fill in the Supabase values (URL, anon key,
service role key, JWT secret, `DATABASE_URL`). Then pick your demo mode:

- **Show the AI tutor chatting:** `TUTOR_DEV_MOCK=true` (canned replies, no key
  or cost) **or** a real `ANTHROPIC_API_KEY`; keep `TUTOR_FREE_ACCESS=true`.
- **Show the Stripe upgrade flow instead:** `TUTOR_FREE_ACCESS=false` +
  `STRIPE_DEV_MOCK=true` (Subscribe grants instantly, no real Stripe).

You can't show both in one session — free access hides the paywall.

### b. Frontend env (`frontend/.env.local`)
Copy `frontend/.env.example` → `frontend/.env.local`. `VITE_SUPABASE_URL` /
`VITE_SUPABASE_ANON_KEY` must point at the **same** Supabase project as the
backend.

### c. Apply migrations to Supabase
```bash
supabase db push                      # with the Supabase CLI
# OR, no CLI — apply each file in order:
for f in supabase/migrations/*.sql; do psql "$DATABASE_URL" -f "$f"; done
```

### d. Seed content (offline — no API key or internet)
```bash
# Large frequency-sourced vocab:
python -m backend.services.seeder.run --language sw   # Swahili (~1204)
python -m backend.services.seeder.run --language tr   # Turkish (~766)
python -m backend.services.seeder.run --language ar   # Arabic (curated)
python -m backend.services.seeder.run --language en   # English (WordNet glosses)

# Curated A1/A2 starter vocab (~30 words each):
for L in es fr de it ca mi yo ha xh; do
  python -m backend.services.seeder.run --language $L
done

# Russian starter vocab (~58 words, offline — aspect-pair cards with
# declension samples; the full OpenRussian corpus in §1e still applies):
python -m backend.services.seeder.run --file data/ru_starter.tsv --language ru

# Grammar (reviewed points + cloze drills; also feeds placement) — seeds ALL
# 14 languages: es 43 · tr 40 · ru 51 · sw 32 · yo 24 · xh 24 · ha 22, plus
# 12-point A1 paths for fr/de/it/ca/mi/ar/en
python -m backend.services.seeder.seed_grammar --language all

# Example sentences — vocab is taught IN A SENTENCE (word blanked) when these
# exist, not as a bare flashcard. Curated starters ship for every curated lang:
for L in es fr de it ca mi yo ha xh tr ru sw; do
  python -m backend.services.seeder.seed_sentences --language $L
done
```
Verify it landed:
```bash
psql "$DATABASE_URL" -c "select count(*) from vocabulary;"        # a few thousand
psql "$DATABASE_URL" -c "select count(*) from content_lists;"     # > 0  (KEY)
psql "$DATABASE_URL" -c "select count(*) from drill_sentences;"   # > 0
```
If `content_lists` is 0, onboarding can't subscribe you to anything and "Learn"
will be empty — re-run the seeders.

> **Which languages have content?**
> - **Full** (vocab + grammar + placement): **Turkish, Spanish, Russian**
>   (Russian A2–C2 grammar ships as drafts pending verification; A1 is live).
> - **Every other language** now has a grammar tab too (12-point A1 path)
>   on top of its vocabulary: Swahili, Arabic, English corpora and curated
>   starters for French, German, Italian, Catalan, Maori, Yoruba, Hausa, Xhosa.
>
> The curated starters (~30 words) are enough to demo onboarding → placement →
> learn → review per language, but they're small.

### e. Optional: pull full corpora (needs open internet)

`scripts/refresh_seed_data.sh` rebuilds `data/*_frequency.tsv` and
`data/*_sentences.tsv` from kaikki.org (Wiktionary) and Tatoeba. Notes:

- Per-language failures **warn and continue** — a bad language no longer kills
  the run.
- **Hausa** needs a manually supplied corpus (drop plain text under
  `data/raw/hausa_corpus/` — see `data/README.md`); until then its frequency
  step warns and is skipped.
- Sentences exist for **tr, sw, yo, xh, ha** (Tatoeba); the Romance/German
  languages warn "no Tatoeba pipeline yet" — expected.
- The files it writes are just TSVs — **nothing reaches the app until you
  re-seed**:

```bash
./scripts/refresh_seed_data.sh
python -m backend.services.seeder.run --language all        # vocab → DB
for L in tr sw yo xh ha; do
  python -m backend.services.seeder.seed_sentences --language $L
done
```

---

## 2. Run it
```bash
uvicorn backend.main:create_app --factory --reload      # backend :8000
cd frontend && npm install && npm run dev               # frontend :5173
```

---

## 3. Golden-path walkthrough (do this once before friends arrive)

Sign up with a fresh account and walk the whole path. Expected behavior — and
**what to look for**:

1. **Onboarding appears** for the new account (not an empty dashboard).
   Pick **Turkish**.
2. **Placement** — choose "take a quick placement check". You should see ~9
   items mixing vocabulary (English prompt → type the Turkish word) and grammar
   (a sentence with a `____` blank). Type a few, submit, see an estimated level.
   *(If it instead asks you to self-report a level, content didn't seed — see 1d.)*
3. **Confirm level → "Start learning"** lands you on the dashboard with a due
   count > 0.
4. **Learn Vocabulary / Learn Grammar** queues cards; **Review Due Cards** runs
   a session. Answer one right and one wrong.
5. **Grammar path** (dashboard → "Grammar path") — the full ordered syllabus
   grouped by level, each point readable with a can-do line, explanation,
   examples, and sources; "Add to my reviews" pulls a single point into your
   queue. (Try Spanish or Turkish — full A1→C2 paths, 43 and 40 points.)
6. **After answering**, the feedback panel shows the correct answer with a 🔈
   **speaker button** — click it; Turkish should be spoken aloud. Expand
   **"Show grammar"** for the explanation + example sentences (also speakable).
7. **Learn from your own text** — paste a Turkish sentence, tap a word, add a
   card; it enters your reviews.
8. **AI Tutor** — opens and responds (mock or real), or shows the **Subscribe**
   button if you configured the billing demo.

---

## What to look for and tell me

Report any of these back and I'll fix them:

- **Anything blank that shouldn't be** — empty placement, "no cards to learn",
  empty due list, a card with no sentence. (Usually a seeding/migration gap.)
- **A red error screen or a request that spins forever** — note which screen and
  what you clicked.
- **Audio**: which languages spoke vs. stayed silent, and on what device/browser.
  (Turkish/Spanish/French/German should speak; African languages + Maori likely
  silent — that's expected, but tell me what you saw.)
- **Wrong-feeling grading** — an answer marked wrong that looks right (or vice
  versa), and for which language/word.
- **Anything confusing in the flow** — a step where a friend hesitated or didn't
  know what to do.
- **The tutor**: did it respond? Did the paywall/Subscribe behave as you set it?

A screenshot + the language + what you clicked is enough for me to chase it down.

---

## Troubleshooting — errors we've actually seen

- **500 on the grammar path (`UndefinedColumnError: column gp.function_note
  does not exist`)** → the database is behind on migrations. Re-run §1c (the
  migration loop is safe to repeat — every migration is idempotent), then
  restart uvicorn.
- **500 on tutor chat (`KeyError`/`avg_ease` in `repositories/tutor.py`)** →
  fixed in code. Pull the latest and restart uvicorn — a `--reload` server
  usually picks it up, but a plain `uvicorn` won't.
- **`pip install -e ".[dev]"` fails building camel-tools / spaCy** → you're on
  Python 3.13/3.14. Use a 3.11/3.12 venv, or the lean install in §1.0.
- **500 on "Learn" (`UniqueViolationError … user_cards_user_id_card_type_card_id_key`)**
  → fixed; the learn endpoint is now idempotent under double-fired requests.
  If you still see it you're running an old build — pull this branch and
  restart uvicorn.
- **`refresh_seed_data.sh` output shrinks (e.g. Turkish 10000 → 766 words) or
  aborts at Hausa** → fixed; the sentences pass no longer rebuilds/overwrites
  the frequency file, and per-language failures warn instead of aborting.
  Re-run the script on this branch, then **re-seed** (§1e) — TSVs alone don't
  change the app.
- **App runs but everything is empty** (no placement items, "nothing to
  learn") → the database wasn't seeded, or was seeded before migrations.
  Check §1d's verify queries; `content_lists = 0` is the giveaway. Re-run
  migrations, then all of §1d.
- **Signup/login fails or every API call is 401** → frontend and backend point
  at different Supabase projects, or the JWT settings in `.env` don't match
  the project's. Recheck §1a/§1b.

---

## Known limitations (not bugs — don't be surprised)

- Content coverage today — grammar paths: **Spanish 43 (6 drills/point) and
  Turkish 40 (full A1→C2)**; **Russian 51 (full A1→C2, 6 drills/point — A2+
  are drafts pending verification, hidden until approved)**; Swahili 32,
  Yoruba 24, Xhosa 24, Hausa 22 (A1→C1-equivalent). Vocab:
  Swahili/Turkish/Arabic/English corpora + curated starters elsewhere
  (~30 words; Russian ~58 with aspect-pair cards). See docs/ROADMAP.md for
  the build-out plan.
- **FSRS personalization** (per-language weight tuning) does nothing until real
  review history accumulates — everyone starts on solid defaults. Correct.
- **Audio** uses the device's built-in voices, so quality/coverage varies by
  device; it's free and has a seam to add higher-quality cached audio later.
- **Grammar in placement** only appears for languages with *reviewed* grammar
  (all seven languages with a path, after `seed_grammar --language all`).
