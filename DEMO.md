# Demo checklist

A foolproof path to a working demo, plus what to watch for and report back.

> **Headline languages: Turkish and Spanish.** Both have vocabulary **and**
> grammar **and** a real (mixed) placement test. Every other language has at
> least starter vocabulary once seeded (see §1d for exactly what's where).

---

## 1. One-time setup

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

# Grammar (reviewed points + cloze drills; also feeds placement):
python -m backend.services.seeder.seed_grammar --language tr
python -m backend.services.seeder.seed_grammar --language es
python -m backend.services.seeder.seed_grammar --language ru

# Example sentences — vocab is taught IN A SENTENCE (word blanked) when these
# exist, not as a bare flashcard. Curated starters ship for every curated lang:
for L in es fr de it ca mi yo ha xh tr; do
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
> - **Full** (vocab + grammar + placement): **Turkish, Spanish**.
> - **Vocab** (placement is vocab-only): Swahili, Arabic, English, and curated
>   starters for French, German, Italian, Catalan, Maori, Yoruba, Hausa, Xhosa.
> - **Grammar only**: Russian (its vocab needs an internet download).
>
> The curated starters (~30 words) are enough to demo onboarding → placement →
> learn → review per language, but they're small. For a full corpus, run the
> sourcing pipeline (`scripts/refresh_seed_data.sh`) from a machine with open
> internet, then re-seed.

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
   queue. (Try Spanish or Turkish — 12 and 10 points respectively.)
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

## Known limitations (not bugs — don't be surprised)

- Content coverage today — grammar paths: **Swahili 32, Yoruba 24, Xhosa 24,
  Hausa 22 points (A1→C1)**; Spanish 12, Turkish 10, Russian 8 (A1, deepening
  planned). Vocab: Swahili/Turkish/Arabic/English corpora + curated starters
  elsewhere (~30 words). See docs/ROADMAP.md for the build-out plan.
- **FSRS personalization** (per-language weight tuning) does nothing until real
  review history accumulates — everyone starts on solid defaults. Correct.
- **Audio** uses the device's built-in voices, so quality/coverage varies by
  device; it's free and has a seam to add higher-quality cached audio later.
- **Grammar in placement** only appears for languages with *reviewed* grammar
  (Turkish, Russian).
