# Feature Landscape

**Domain:** Multi-language SRS learning platform (spaced repetition + NLP answer validation)
**Researched:** 2026-03-12
**Confidence:** MEDIUM (based on extensive training knowledge of Anki, Bunpro, WaniKani, Memrise, Clozemaster, LingQ; no live web verification available)

## Competitive Landscape Summary

The SRS platform market splits into three tiers:

1. **Power tools** (Anki): infinitely flexible, terrible UX, no language intelligence
2. **Curated single-language** (Bunpro, WaniKani): beautiful UX, deep grammar, locked to Japanese
3. **Mass-market multi-language** (Memrise, Duolingo): gamified, shallow, no morphological intelligence

PolyglotSRS occupies a gap: **Bunpro-depth UX across multiple languages with NLP-powered answer validation**. No platform currently does this well for Russian + Arabic together.

---

## Table Stakes

Features users expect. Missing any of these means users leave immediately or never convert from free trial.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| SRS scheduling (SM-2 or equivalent) | Core value proposition of any SRS app. Users compare intervals against Anki. | Medium | SM-2 is well-documented. Must feel predictable -- users get anxious if scheduling feels random. Already specced. |
| Card review session | Anki, Bunpro, WaniKani all have this. Users expect a queue of due cards they work through. | Medium | Must show progress (12/20 done), session summary at end. Already specced. |
| Quality rating buttons | Every SRS app has Again/Hard/Good/Easy (or equivalent). Users expect to control their own scheduling. | Low | Bunpro uses Again/Hard/Good/Easy. WaniKani auto-rates. Let users choose. Already specced. |
| Due card count on dashboard | Users check "how many reviews do I have?" daily. This is the hook. | Low | Show prominently. Badge/notification-worthy. Already specced. |
| Streak tracking | Duolingo proved streaks drive retention. Every competitor has them now. | Low | Daily streak with visual indicator. Streak freeze (paid feature) is optional but expected. Already specced. |
| Audio pronunciation | Users expect to hear words spoken. Memrise, WaniKani, Bunpro all have audio. | Medium | Forvo integration + Web Speech API fallback. Already specced. Must not block card display if audio fails to load. |
| Example sentences | Context is king. Raw vocab cards without sentences feel incomplete vs competitors. | Medium | Tatoeba integration already specced. Show 1-2 sentences per card minimum. |
| Search / browse content | Users want to look up specific words or grammar points, not only encounter them in review. | Medium | Browse by CEFR level, search by word/grammar title. Already partially specced (Grammar.jsx, Vocabulary.jsx pages). |
| User authentication + cloud sync | Data must not be lost. Users expect to resume on another device. | Low | Supabase Auth already specced. Email + Google OAuth covers 95% of users. |
| Mobile-responsive design | Most SRS review happens on phones (commute, waiting). Web must work on mobile. | Medium | Tailwind responsive classes. Not a native app, but must be thumb-friendly. Touch targets 44px+. |
| RTL support for Arabic | Non-negotiable for an Arabic learning platform. Broken RTL = instant uninstall. | High | dir="rtl", mirrored layouts, Noto Naskh Arabic font, bidirectional text handling in mixed-script cards. Already specced but implementation is complex. |
| On-screen keyboards (Cyrillic + Arabic) | Desktop users cannot type Russian/Arabic without script input. Blocking issue. | Medium | Already specced. Must be dismissable, not cover the answer field. Position matters. |
| Free tier with meaningful usage | Users expect to try before paying. Every competitor offers free access. | Low | 1 language, 20 cards/day cap. Enough to feel the product, not enough to replace paying. Already specced. |
| Definitions and translations | Cards must show meaning. Users coming from Anki expect definitions. | Low | Wiktionary integration for definitions. Already specced. |
| Progress tracking | Users want to see how far they've gotten. CEFR levels, percentage complete, words learned count. | Medium | Already specced (CEFR progress bars). Must feel rewarding -- numbers going up. |

---

## Differentiators

Features that set PolyglotSRS apart from competitors. Not expected, but once experienced, hard to leave.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **4-tier NLP answer validation** | No competitor does this. Anki has no answer checking. Bunpro does basic string matching. Clozemaster is exact-match only. This is the core moat. | High | exact -> normalized -> lemma -> morphological family. Already deeply specced. This is the number one differentiator. |
| **Aspect partner detection (Russian)** | Russian learners constantly confuse imperfective/perfective. No SRS app explains the distinction in context. | High | WRONG_FORM feedback explaining which aspect is needed and why. Unique to PolyglotSRS. |
| **Arabic verb form feedback** | Arabic Form I-X system is the hardest part of the language. No SRS app gives form-specific feedback. | High | Show root + form table when wrong form is used. Combined with tashkeel handling, this is the Arabic moat. |
| **Tashkeel-aware validation** | Arabic learners are terrified of diacritics. Accepting answers with/without tashkeel while still teaching correct pronunciation removes a massive friction point. | Medium | dediac normalization + tashkeel toggle on cards. No competitor handles this gracefully. |
| **Note import -> auto card extraction** | Users have existing study notes (Markdown, PDF). Turning them into SRS cards automatically via Claude API is a huge time-saver. No SRS app does this well. | High | Claude API for structured extraction. Differentiator, but also a cost center (API calls). Gate behind paid tier. |
| **Fill-in-the-blank drills** | Bunpro's best feature. Forces active recall (typing) instead of passive recognition (flipping cards). Most SRS apps only do flip cards. | Medium | Already specced. Must feel fast -- instant feedback, no page reload. |
| **Transliteration fallback (Russian)** | Latin -> Cyrillic auto-detection means users learning Cyrillic script can still practice vocabulary without keyboard frustration. | Low | Already specced. Small feature, big QoL. Clozemaster does this too, but poorly. |
| **Per-language subscriptions** | Most competitors force all-or-nothing pricing. Per-language pricing lets users pay only for what they study. Lower barrier to entry. | Low | Stripe already specced. Business model differentiator, not a technical one. |
| **Trilingual ecosystem positioning** | Russian + Arabic + English together is unique. Most platforms are single-language or spread thin across 20+ languages. Deep support for 3 languages beats shallow support for 30. | Low | Marketing/positioning, not a feature per se. But the NLP depth per language IS the feature. |
| **Word-by-word breakdown** | Toggling literal/word-for-word translation helps learners understand sentence structure. LingQ does this, but no SRS app does. | Medium | Already specced in answer-validation-spec. Requires pre-computed breakdowns or Claude API extraction. |
| **UI language independence** | Arabic speaker learning Russian sees UI in Arabic. Russian speaker learning English sees UI in Russian. Most competitors are English-UI only. | High | i18n infrastructure needed. High effort but opens non-English-speaking markets. Spec mentions this but implementation is substantial. |
| **Morphology display on vocab cards** | Showing gender, case patterns, verb aspects (Russian) or root + form (Arabic) directly on vocabulary cards. WaniKani does this for kanji radicals. Nobody does it for Russian/Arabic. | Medium | morphology JSONB already in schema. Rendering it language-specifically is the work. |

---

## Anti-Features

Features to explicitly NOT build. Building these would waste time, dilute focus, or actively harm the product.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Gamification (XP, leaderboards, gems)** | Duolingo's gamification creates addiction without learning. SRS users are self-motivated adults. Gamification signals "not serious." | Streaks are enough. Focus on clear progress metrics (words known, CEFR level, review accuracy). |
| **Social features (friends, sharing, chat)** | Enormous engineering surface, low impact on core SRS value. Bunpro and WaniKani both prove you can succeed without social. | Out of scope per PROJECT.md. Revisit in v3 if community forms organically. |
| **Native mobile apps** | React Native / Flutter doubles the codebase. PWA covers 90% of mobile use cases for an SRS app. | PWA in v2 (offline review mode). Already in PROJECT.md out-of-scope. |
| **AI-generated cards (fully automatic)** | AI hallucinations in language content (wrong translations, incorrect grammar) destroy user trust instantly. The note import pipeline is semi-automatic (user provides source material). | Keep Claude API for parsing user notes, not for generating content from scratch. Curated seed data + user imports. |
| **20+ language support** | Spreading thin across languages means no language gets proper NLP depth. The moat is depth, not breadth. | 3 languages done deeply. Architecture supports adding more, but v1 is Russian + Arabic + English only. |
| **Anki deck import** | Anki's .apkg format is complex (SQLite + media files). Supporting it creates expectations of Anki-level customization. | Support Markdown + PDF import (covers the same content). Users can export Anki notes as text and reimport. |
| **Custom card templates** | Anki's template system is powerful but creates a support nightmare. Every template bug becomes your bug. | Fixed card types (vocabulary + grammar) with consistent, polished layouts. Opinionated is better than flexible here. |
| **Grammar chatbot / AI tutor** | LLM-as-tutor is trendy but expensive per-query and hard to make consistently accurate for grammar explanations. | Pre-written grammar explanations (curated). The NLP validation system IS the "smart" feature -- it operates at answer-check time, not chat time. |
| **Listening-only / speaking modes** | Speech-to-text for Russian/Arabic is unreliable. Building audio-input review adds massive complexity for questionable accuracy. | v2 listening comprehension (audio -> type) is already planned. Speaking practice is out of scope entirely. |
| **Spaced repetition for non-language content** | Becoming a general SRS tool means competing with Anki (impossible). Stay focused on language learning. | Language-specific NLP is the moat. Every feature should leverage it. |

---

## Feature Dependencies

```
Authentication (Supabase Auth)
  |
  +-> User Cards (SRS state)
  |     |
  |     +-> SRS Review Session
  |     |     |
  |     |     +-> Answer Validation (NLP backends)
  |     |     |     |
  |     |     |     +-> Fill-in-the-blank Drills
  |     |     |     +-> Aspect/Form Feedback
  |     |     |
  |     |     +-> Quality Rating -> SM-2 Update
  |     |     +-> Session Summary / Stats
  |     |
  |     +-> Dashboard (due counts, streak, heatmap)
  |
  +-> Subscriptions (Stripe)
  |     |
  |     +-> Per-language access gating
  |     +-> Note Import (paid feature)
  |
  +-> Note Import -> Claude API parsing -> Card Extraction -> Enrichment
  |
  +-> Browse Grammar / Vocabulary (public, no auth needed for browsing)

Language Data Pipeline (independent of auth):
  Seed Data Scripts -> vocabulary + grammar_points tables
  Wiktionary/Forvo/Tatoeba enrichment -> audio, definitions, examples

NLP Backends (must exist before review sessions work):
  pymorphy3 (Russian) -> answer validation + morphology display
  camel-tools (Arabic) -> answer validation + root/form extraction
  spaCy (English) -> answer validation + lemmatization

RTL Infrastructure (must exist before Arabic cards render correctly):
  RTLWrapper + dir="rtl" + Noto Naskh Arabic font + bidirectional text handling
  On-screen Arabic keyboard
```

### Critical Path

The dependency chain that blocks everything else:

1. **Database schema** (all features need tables)
2. **NLP backends** (answer validation needs them, which review sessions need)
3. **SRS engine (SM-2)** (review sessions need scheduling logic)
4. **Review session API + UI** (the core product loop)
5. **Dashboard** (the daily hook that brings users back)

Everything else (import, subscriptions, enrichment) layers on top.

---

## Platform-Specific Feature Analysis

### What Bunpro Does Right (model these)

| Feature | Bunpro Implementation | PolyglotSRS Equivalent |
|---------|----------------------|----------------------|
| Grammar-first SRS | Each card teaches one grammar point in context | grammar_points table + drill_sentences with fill-in-blank |
| Typed answers | Users type the answer, not just flip cards | Fill-in-the-blank mode with NLP validation (better than Bunpro's string matching) |
| Nuance hints | "Be careful of the particle" style hints before answering | hint field on drill_sentences, shown on demand |
| Reading passages | Integrated reading with grammar point callouts | Not in v1. Consider for v2 as reading mode. |
| Community sentences | Users submit alternative example sentences | Out of scope v1. Anti-feature for now (curation quality). |
| JLPT level filtering | Filter by proficiency level | CEFR level filtering (A1-C2). Already specced. |

### What WaniKani Does Right (model these)

| Feature | WaniKani Implementation | PolyglotSRS Equivalent |
|---------|------------------------|----------------------|
| Radical/component breakdown | Shows kanji components | Arabic root display (trilateral root system). Russian word families via morphology. |
| Mnemonics | Creative memory aids for each item | Not in v1. Could add user-created mnemonics field later. |
| Level-gated progression | Cannot access level N+1 until N is mastered | CEFR-gated progression optional. Do not hard-gate -- adult learners resent artificial blocks. Soft-suggest instead. |
| SRS stages named clearly | Apprentice -> Guru -> Master -> Enlightened -> Burned | Use clear stage names instead of raw interval numbers. "Learning -> Familiar -> Strong -> Mastered" |

### What Anki Does Wrong (avoid these)

| Anki Problem | Why It Fails | PolyglotSRS Approach |
|-------------|--------------|---------------------|
| Overwhelming configuration | 50+ settings per deck. Paralyzes new users. | Opinionated defaults. SM-2 with sensible parameters. No deck settings page. |
| No answer intelligence | Exact string match or nothing. No linguistic awareness. | 4-tier NLP validation. Core differentiator. |
| Ugly default UI | Cards look like 2005 HTML. No design system. | Tailwind + polished card components. Bunpro-level design. |
| No curated content | Users must find/make their own cards or use unreliable shared decks. | Seed data from OpenRussian, Arabic Wordnet, COCA. Curated grammar points. |
| Desktop-first | Mobile app exists but feels like afterthought. | Mobile-responsive web from day one. |

### What Clozemaster Does (partial competitor)

| Feature | Clozemaster | PolyglotSRS Advantage |
|---------|-------------|----------------------|
| Cloze deletion (fill-in-blank) | Core mechanic, multi-language | Same mechanic, but with NLP validation instead of exact match |
| Frequency-ranked sentences | Sentences ordered by word frequency | frequency_rank on vocabulary enables this. Good feature to replicate. |
| Many languages | 50+ languages, all shallow | 3 languages, all deep. Quality over quantity. |
| No grammar explanations | Just sentences, no teaching | Grammar points with explanations, structure formulas, related grammar links |

---

## Arabic-Specific Feature Requirements

Arabic has unique UX requirements that most platforms botch. These are table stakes for an Arabic learning platform, even if they are differentiators in the general market.

| Feature | Why Critical for Arabic | Complexity | Notes |
|---------|------------------------|------------|-------|
| Tashkeel toggle | Beginners need diacritics; intermediates need to read without them. Show/hide per card. | Low | Toggle button on card. Store both forms in DB. |
| Root display (trilateral) | The root system IS Arabic. Hiding it is like hiding radicals from kanji learners. | Low | Extract from camel-tools, display as spaced consonants (e.g., k-t-b). |
| Verb form table | Forms I-X are the backbone of Arabic vocabulary. Must be visible and linked. | Medium | Show form number on vocab cards. Link to form table page. |
| Alef normalization in search | Users will search for words with any alef variant. Must normalize. | Low | Already specced in answer validation. Apply same normalization to search. |
| Mixed-direction text | Arabic cards often contain English translations on the same card. Bidirectional text rendering must not break. | Medium | Unicode bidi algorithm + explicit direction marks. Test with actual mixed content. |
| Large font size for Arabic | Arabic script is less legible at small sizes than Latin. Noto Naskh helps but size must be larger. | Low | Tailwind text-xl or text-2xl for Arabic script. Font-size-specific breakpoints. |

---

## Russian-Specific Feature Requirements

| Feature | Why Critical for Russian | Complexity | Notes |
|---------|--------------------------|------------|-------|
| Stress marks on vocabulary | Russian stress is unpredictable and changes meaning. OpenRussian data includes stress. | Low | Display stress marks (accent over vowel) on cards. Never require them in answers. |
| Case display on drill prompts | If a fill-in-the-blank expects accusative, hint should indicate the case needed. | Low | Grammar tag in drill sentence metadata. |
| Aspect pair linking | Every Russian verb card should link to its aspect partner. | Medium | OpenRussian has some aspect pairs. Supplement with curated data. Store as related vocabulary. |
| Cyrillic keyboard with phonetic layout | Some learners use phonetic layout (A=A), others standard Russian layout. Support both or let users choose. | Medium | Two keyboard layouts as option in settings. Default to phonetic (more common among learners). |

---

## MVP Recommendation

### Must Ship (Phase 1 - Core)

Prioritize these. Without them, the product has no loop.

1. **SRS review session with SM-2** -- the core loop
2. **4-tier answer validation** -- the core differentiator
3. **Russian NLP backend** (pymorphy3) -- answer checking for Russian
4. **Arabic NLP backend** (camel-tools) -- answer checking for Arabic
5. **English NLP backend** (spaCy) -- answer checking for English
6. **Fill-in-the-blank drills** -- the primary interaction mode
7. **RTL support for Arabic** -- non-negotiable
8. **On-screen keyboards** (Cyrillic + Arabic) -- unblocks input
9. **Dashboard with due counts + streak** -- the daily hook
10. **Seed data loaded** (OpenRussian, Arabic frequency, COCA) -- content to review
11. **Authentication** (Supabase) -- user accounts
12. **Browse grammar + vocabulary** -- content discovery

### Ship Next (Phase 2 - Monetize)

1. **Stripe subscriptions** -- revenue
2. **Note import** (Markdown + PDF via Claude API) -- paid feature, differentiator
3. **Wiktionary/Forvo/Tatoeba enrichment** -- content quality
4. **Progress heatmap** -- retention/engagement
5. **CEFR progress tracking** -- feeling of advancement
6. **Session summary statistics** -- post-review feedback

### Defer (Phase 3+)

- **UI language localization** (Arabic/Russian UI) -- high effort, defer until market validates
- **PWA + offline mode** -- v2 after core loop is solid
- **Conjugation table pages** -- nice-to-have, not core to SRS loop
- **Word-by-word breakdown toggle** -- requires pre-computed data, add after content pipeline is stable
- **Reading mode** (passages with grammar callouts) -- v3 feature
- **Listening comprehension** (audio -> type) -- v2, already in out-of-scope

---

## Sources

- Training data knowledge of Anki (ankiweb.net), Bunpro (bunpro.jp), WaniKani (wanikani.com), Memrise (memrise.com), Clozemaster (clozemaster.com), LingQ (lingq.com), Duolingo (duolingo.com) -- LOW-MEDIUM confidence (based on training data, not live verification)
- Project specs: polyglot-srs-spec.md, answer-validation-spec.md -- HIGH confidence (direct source)
- SM-2 algorithm: well-documented, stable since 1987 -- HIGH confidence
- Arabic NLP (camel-tools): known library for MSA morphology -- MEDIUM confidence
- Russian NLP (pymorphy3): well-established Russian morphological analyzer -- MEDIUM confidence

**Note:** WebSearch was unavailable during research. Feature comparisons are based on training data knowledge of these platforms. Competitive landscape may have shifted since training cutoff (early 2025). Recommend spot-checking Bunpro and Clozemaster feature pages before finalizing roadmap.
