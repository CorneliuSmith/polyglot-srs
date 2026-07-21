# PolyglotSRS — Business Plan

*Working draft, 2026-07. This is a product/market strategy document, not
investment advice. Every revenue figure is a scenario with stated
assumptions — a way to reason about the business, not a forecast.*

---

## 1. Executive summary

PolyglotSRS is a serious-learner language app built around **spaced
repetition (FSRS), CEFR grammar paths, and AI-assisted practice** across 22
languages. It is not a gamified beginner funnel (Duolingo's market); its
natural user is the **intermediate learner who finished a beginner app and
still can't read a newspaper or hold a conversation.**

The product's edge is not any single feature — it is the **bundle in one
place**: grammar-path SRS + an AI graded reader + an AI tutor grounded in the
learner's own cards + a conjugation/declension "Gym," across many languages.
No mainstream competitor combines all of these.

The business does **not** live or die on the product. It lives or dies on
**distribution and content quality**. The recommended strategy is to pick one
**wedge** (either the intermediate-plateau serious learner, or specific
underserved languages the app already serves well), nail quality there, and
sell an all-access plan at ~$100/year — rather than marketing "22 languages,
everything," which is an unwinnable fight with Duolingo/Babbel on ad spend.

**Realistic aspirational comp: Bunpro** (a loyal, profitable niche tool), not
Duolingo (an unreachable ceiling).

---

## 2. Product

### What exists today
- **Learn / Review** — FSRS spaced repetition over vocabulary and grammar;
  teach-before-quiz; per-card memory model; daily goals.
- **Grammar paths A1→C2** — hand-authored CEFR curricula per language, with
  plain-language explanations, references, and drills.
- **The Reader** — AI-generated graded reading at the learner's level;
  tap-to-gloss; add unknown words straight to reviews.
- **The Tutor** — per-language AI chat, grounded in the learner's actual
  cards and weak areas; practice vs. reference modes; token/cost caps by tier.
- **The Gym** — pick a tense/case/mood and drill conjugation/declension in a
  mixed set, with a collapsible chart; 12 inflected languages.
- **Supporting**: Letters & Sounds (script/alphabet), neural TTS, adaptive
  placement test, personal decks, morphology charts, dark mode, PWA install,
  email review reminders.
- **Ops**: contributor/reviewer/admin roles, inline change requests with
  voting, engagement analytics, Stripe wiring (Single / All plans).

### Maturity
Several languages are **draft-tier** (AI-checked, not yet native-reviewed).
Turning draft → charge-ready via native review is the gating quality work —
and the reason the reviewer/change-request tooling exists.

---

## 3. Market

- **Category**: online language learning. Large and growing, but dominated at
  the top of the funnel by Duolingo (~600M registered, ~8M paying) and a
  crowded middle (Babbel, Busuu, Rosetta Stone, Memrise).
- **The underserved segment**: **intermediate learners**. Duolingo is
  optimized for retention and beginners; it famously abandons people at the
  "intermediate plateau." Tools that serve this segment — Bunpro, LingQ,
  Migaku, Clozemaster, Anki, Speak — are smaller but have **loyal, paying**
  users who already spend money on learning (italki lessons, textbooks).
- **A second underserved segment**: **low-resource / under-served languages**.
  The app already ships Swahili, Yoruba, Hausa, Xhosa, Jamaican Patois, Māori,
  Thai, Hindi, Korean, etc. These have small markets but near-zero quality
  competition and passionate diaspora/learner communities.

---

## 4. Competitive landscape & uniqueness

The individual capabilities all exist elsewhere. The **combination** is rare.

| Capability | Who owns it today | PolyglotSRS |
|---|---|---|
| Grammar-path SRS (A1→C2) | Bunpro (JP; recently ES) | 22 languages |
| Cloze / sentence SRS | Clozemaster, Anki | Built-in, curated |
| AI graded reading + tap-to-gloss | LingQ, Readlang, Migaku | Built-in (Reader) |
| AI tutor / conversation | Speak, TalkPal | Built-in, **grounded in your cards** |
| Conjugation/declension drilling | Cooljugator (reference) | Built-in, SRS-fed (Gym) |

**Genuine differentiator**: one integrated tool that takes a serious learner
from A1 grammar through reading real text, drilling forms, and conversing
with an AI that knows what they've studied — across many languages.

**Honest caveat**: the AI features are **not a moat**. Any competitor can
add an AI reader/tutor quickly. The durable moat, if built, is:
1. **Content quality** — hand-verified CEFR grammar and faithful sentences
   per language. Expensive and slow → hard to copy.
2. **The specific languages served well** — especially the ones nobody else
   bothers with.

---

## 5. Pricing & packaging

The serious-learner segment supports real pricing (these users already pay
for tutoring and textbooks).

| Plan | Price | Notes |
|---|---|---|
| Free | $0 | SRS + Learn/Review; **AI features gated** (caps AI cost exposure) |
| Single language | $6–9/mo or ~$60/yr | Entry tier |
| **All languages** | **$12–15/mo or $99–120/yr** | **Hero plan** — breadth is the differentiator |
| Lifetime | $150–250 | Strong early cash-flow + loyalty lever (Bunpro precedent) |

**Principles**
- Gate the **AI** (Tutor, Reader), not the SRS — aligns price with the
  variable cost you actually incur (Claude tokens).
- Lead with the **All-languages** annual plan; let single-language be the
  downsell.
- Consider **lifetime** early: it front-loads cash from your most committed
  users while the base is small.

---

## 6. Unit economics — the AI margin warning

The Tutor and Reader cost real API tokens **per use**. This is the single
biggest threat to margin and must be modeled continuously:

- A heavy "Plus" user must **never cost more in AI than they pay.**
- Per-tier caps (free monthly / plus daily) already exist — keep them.
- Route models by need (cheaper models for scaffolded coaching; stronger only
  where accuracy is critical). The per-language model override and admin cost
  view are the levers.
- Track **AI cost per paying user per month** as a first-class metric.

Rule of thumb: if AI COGS exceeds ~20–30% of a plan's price for the median
paid user, the pricing or the caps need to change.

---

## 7. Revenue scenarios

Blended ARPU assumption: **~$100/year**. Everything hinges on distribution.

| Scenario | Paying subs | ARR | When | Notes |
|---|---|---|---|---|
| Median indie edtech | ~0–100 | ~$0–10k | — | Most apps never get traction. Named honestly. |
| Modest traction | 300–1,000 | **$30k–100k** | Y1–2 | A couple of channels working |
| Indie-niche success | 2,000–5,000 | **$200k–500k** | Y2–3 | Owning a wedge + consistent marketing |
| Bunpro-class niche leader | 10,000+ | $1M+ | Y3–5+ | Requires a defensible wedge + brand |

**Reality check**: the median outcome for a solo-founder edtech app is near
zero — not because the product is weak, but because the first 1,000 true fans
are brutally hard to acquire. The gap between "great product" and "revenue"
is **entirely distribution and quality**, not features.

---

## 8. Go-to-market — pick a wedge

Do **not** sell "22 languages, everything." Two viable wedges:

### Wedge A — the intermediate plateau (broadest)
Position as *"the app for when Duolingo stops working."* Compete with
Bunpro/LingQ/Migaku on **depth**: real grammar, real reading, AI that knows
your cards. SEO/content around "how to get past intermediate [Spanish/French/
German]"; partnerships with language YouTubers and subreddits (r/languagelearning,
per-language subs); the multi-language breadth becomes the upgrade surprise,
not the pitch.

### Wedge B — underserved languages (defensible, smaller)
Own languages the majors ignore: Swahili, Yoruba, Hausa, Xhosa, Jamaican
Patois, Māori. Near-zero competition, passionate communities, diaspora
demand, and potential institutional/education angles. Smaller TAM, but you
can be *the* answer, which is worth more than being option #40 for Spanish.

**Recommendation**: start with **B as the beachhead** (defensible, community-
driven, cheaper to win) while **A is the growth engine** you expand into once
quality and word-of-mouth compound.

---

## 9. Risks

1. **Distribution** — the #1 risk. Product quality does not solve it.
2. **Content quality at scale** — draft-tier languages aren't charge-ready
   without native review; wrong content erodes trust fast.
3. **AI margin** — uncapped AI usage can turn a subscription unprofitable.
4. **Feature copyability** — AI reader/tutor are easily cloned; quality and
   language coverage are the only durable defenses.
5. **Solo-founder bandwidth** — content, engineering, and marketing compete
   for the same hours.
6. **Platform dependence** — Claude API pricing, Supabase, DigitalOcean.

---

## 10. Path to revenue (next 6–12 months)

1. **Quality first.** Native-review the wedge languages to charge-ready;
   the reviewer/change-request system is the pipeline.
2. **Instrument money.** Turn on Stripe for real; watch AI-cost-per-paid-user.
3. **Pick the wedge** (recommend B beachhead → A growth) and produce
   distribution content relentlessly for it.
4. **Ship a lifetime deal** to convert early superfans and fund runway.
5. **Measure the funnel** (signup → placement → first review → week-2 return)
   — the analytics already exist; act on the drop-offs.
6. **Only then** widen languages/features. Breadth is the reward for a
   working wedge, not a substitute for one.
