# Pricing and launch — nine decisions before the app takes money

*Decision memo, 17 August 2026. Companion to `BUSINESS_PLAN.md`, which sets
the strategy; this file makes the nine calls the owner asked for and shows
the arithmetic. Every price and cap traces either to code in this repository
or to an assumption stated beside it. Not legal or investment advice.*

The through-line: the product is ready enough to charge for, but the meter
isn't — **one Reader text can cost thirty times one tutor message and draws
the same single unit from the allowance pool.**

---

## 1. What to charge

| Plan | Price | AI pool | Reader cap | Median AI cost | Why |
|---|---|---|---|---|---|
| Free | $0 | 20 units/mo | 2 | ~$0.25 | Learn/Review forever; a real taste of the AI |
| Starter | $8/mo · $59/yr | 120 | 8 | ~$1.10 | The on-ramp, and the downsell |
| **Standard** | **$14/mo · $119/yr** | **300** | **16** | **~$2.50** | The hero plan |
| Immersion | $24/mo · $199/yr | 600 | 25 | ~$5.50 | For the daily learner; where routing matters most |
| Top-up pack | $6 one-off | +120 | +8 | ~$2.40 | Deliberate purchase, never surprise overage |
| Lifetime | $249, 50 seats | 300/mo | 16 | ~$30/yr | Front-loads cash; never promise unlimited AI |

Plus a **founder rate of $89/yr locked for life for the first 100
subscribers** — it buys testimonials and review recruits, not just revenue.

The pools are sized so median AI cost stays under 25% of price and the
absolute cap under 70%. **The appendix at the end of this memo shows the
whole cost stack** — per-action costs, the unit weights that make the meter
honest, fixed costs, and what each rung contributes — and answers the
follow-up question of how much revenue this produces at what subscriber
count.

### The arithmetic

Per-action model cost, all four drawing **one** unit from the same pool
(`repositories/tutor.py` counts `chat`, `gym_gen`, `gym_chart`, `recs`):

| Action | Cost | Why |
|---|---|---|
| Tutor message | ~$0.009 | ~3k in / ~450 out, and the system block is already cached (`services/tutor.py`) |
| Gym set | ~$0.034 | Uncached generation, items plus chart |
| Weekly picks | ~$0.024 | One batch |
| Reader text, typical | ~$0.075 | ~3.5k output tokens plus the contract grader |
| Reader text, worst | ~$0.28 | Long C2: up to two full generations at the 16,384-token ceiling (#287), graded |

So 300 messages spent entirely on chat costs ~$2.80; spent entirely on long
Reader texts it costs up to **$84 against $119 of annual revenue**. That is a
metering problem, not a pricing one:

1. **Weight the draw** — a Reader text should cost 3 units (5 for a long one)
   and a Gym generation 2, with a visible monthly cap on Reader texts. The
   learner still sees one honest percentage; the pool then bounds volume and
   the sub-cap bounds shape. Small change to the counted-kinds query.
2. **Cache the Reader and Gym prompts** the way the tutor's are, and route
   the grading pass to Haiku — a fixed-rubric yes/no judgement does not need
   the expensive model.

Model rates used: Opus 5 $5/$25 per MTok, Sonnet 5 $3/$15 (intro $2/$10
through 2026-08-31), Haiku 4.5 $1/$5; cached input reads ≈ 0.1×.

$119/yr sits at the top of the indie band (Bunpro/LingQ/Migaku anchor roughly
$50–155/yr). Holding the top of that band needs the bundle *and* reviewed
content — which is why §6 comes before the Stripe switch. Sell the year, not
the month: $119 against $168 is a 29% saving, and annual billing also cuts
Stripe's per-charge fee from $8.52 a year to $3.75 while handing you the cash
before you incur that year's AI cost.

## 2. When to ship native iOS/Android

**Android first, not before ~100 paying subscribers; iOS one release later.
Sell on the web, apps read entitlement, no in-app purchase at launch.**

`docs/native-apps.md` already has both Capacitor shells committed and lists
what remains (icons, signing, permission strings, deep-link association,
screenshots, real-device RTL testing). Two to four focused weeks, no rewrite.

The only thing the stores give you that the PWA doesn't is **push
notifications** — which for a spaced-repetition habit product is the biggest
retention lever there is. So the trigger is the week daily-return rate
becomes the number you're trying to move. Signals: >half of sessions on a
handset, ~100 paying subs, week-2 return plateaued, buyers asking for it.

Costs beyond the weeks: release drag (web ships on deploy, apps ship on
review — plan pricing changes around the slower one), 15% store commission
under both small-business programmes, store data-disclosure work covering
what the tutor sends the model provider, $99/yr Apple + $25 once Google, and
a Mac. The rules on steering buyers to external checkout have changed twice
in two years — read the current App Review guideline 3.1.3 the month you
submit.

## 3. A better name

**Vantage.** It is the Council of Europe's own official name for B2 — the
exact band the app targets — it means a place you can see from, and a learner
in Brazil or Indonesia can hear it once and spell it. Runner-up:
**Threshold**, CEFR's official name for B1.

Two things are wrong with "PolyglotSRS": *SRS* names the mechanism to an
audience that doesn't have the word, and *Polyglot* is the most crowded term
in the category (a club, a conference, a Microsoft product) with no
defensible mark. Fine codename, weak brand.

Test any candidate: say it to five non-native speakers and have them spell it
back; check it isn't an awkward word in the 22 languages taught; check
trademark classes 9 and 41, not just the domain (Vantage is in use by
unrelated software — expect to need a modifier); check it survives "I've been
doing my ___ reviews"; and make sure it doesn't promise fluency. Rename
before the store listings — the bundle identifier `com.polyglotsrs.app` is
committed in both native projects and is annoying to change after a
submission.

## 4. How far locale costs separate

**Per-language variable cost is already measurable.** `tutor_usage` tags
every model call with language, model, kind and full token counts, and
`aggregate_tutor_usage` rolls it up.

| Cost | Separable? | How |
|---|---|---|
| Tutor, Reader, Gym, picks | Today | `tutor_usage.language_id` + token columns |
| Content generation runs | Today | The CLI is invoked per language |
| Speech (TTS chars, STT minutes) | With effort | Tag synthesis calls the way `tutor_usage` is tagged — do it **before** auto-listening speaking mode makes STT continuous |
| Native review hours | By definition | Track against subscribers-per-language |
| UI localisation | Per locale | Six locales; auto-translate spend is per support locale |
| Hosting, Stripe fees, your time | No | Joint and fixed — allocate, never pretend it's measured |

About a third of the cost base is genuinely per-language. Don't build a
per-language P&L; build **cost per active learner by language** and act on
outliers — the `languages.tutor_model` override is the lever that makes the
measurement actionable.

**Regional pricing** is the other reading, and it's worth real revenue given
where Swahili/Yoruba/Hausa/Persian/Thai/Indonesian learners are. Three Stripe
bands (full; ~55% for LatAm/Eastern Europe/SE Asia; ~35% for South Asia and
Sub-Saharan Africa), set from billing country and locked at signup. The trap:
**model cost is identical in every band**, so in the lowest band cut the pool
(120 messages, not 300) as well as the price, and say so on the pricing page.

## 5. Representing AI imperfection in the terms

Three artefacts before charging: **Terms with an AI-content clause**, a
**Privacy policy naming the model provider**, and a plain-language **"AI in
this app"** page. Then the part that actually protects you.

In the terms: content is generated in part by third-party language models and
may contain errors; it is educational, and explicitly not professional
translation nor legal, medical, immigration or safety-critical advice, and
not to be relied on for exams, certification or official correspondence. No
warranty of accuracy or fitness; liability capped at fees paid in the last
twelve months; a model-provider clause reserving the right to change
providers.

Know the limit of that: in the EU and UK you cannot disclaim the statutory
obligation that digital content matches its description. **The disclaimer is
not the defence — the accuracy of the description is.** Calling AI-drafted
content "expert-verified" is what would bite; the AI being imperfect is not.

In the product, which matters more:

- **Per-language quality badges** — "Native-reviewed" vs "AI-drafted — tell
  us when it's wrong". The data already distinguishes them; surfacing it turns
  a legal risk into a credibility asset.
- **Report buttons** on cards, sentences and drills (they exist) with visible
  follow-through.
- **Say what the tutor remembers and let learners delete it** — the memory
  panel from #284 shows each fact tagged stated-vs-guessed with per-fact
  delete. Cite it in the privacy policy rather than burying it.
- Marketing discipline: "AI-assisted", never "perfect", "native-quality" or
  "guaranteed correct"; no CEFR-certification or exam-equivalence claims.

Both stores require an accurate data-collection disclosure covering tutor and
audio data; get a DPA with each provider. Budget a few hundred to ~$1,500 for
a lawyer to review a consumer-SaaS template before taking EU/UK money.

## 6. Paying linguists to review

**Yes — roughly $750 per language (15–25 hours), for the three wedge
languages only. ~$2,000–4,000 buys a charge-ready beachhead.** Reviewers work
inside the existing review inbox and change-request tooling, so the output
lands as data rather than a document, and they get a credit line in the app.

Review in this order and stop when the money runs out:

1. **A1–B1 grammar explanations and their drills** — the trust-killing error,
   read by everyone.
2. **Seeded vocabulary** — forms, definitions, register.
3. **Example sentences: sample, don't exhaust.** A 20% audit with a defect
   rate tells you whether to regenerate a batch.
4. **Alphabet and letters data** for non-Latin scripts — small, highly
   visible, and where a romanisation inconsistency gets spotted first.
5. **Spot-check live output** — a few Reader texts and tutor conversations for
   register and dialect.

Qualified native reviewers run roughly $20–45/hour (or ~$0.02–0.04/word for
proofreading-style work); rates vary widely by pair, so get three quotes per
language. Recruit through per-language subreddits, diaspora communities and
university departments, and run candidates through the **trial-reviewer role
first** — you see their judgement before paying for hours. Pay for a fixed
deliverable ("audit these 200 items, file change requests"), not open-ended
hours. Credit them by name: it lowers the rate, raises the care, and markets
to the exact community you want.

Do not buy review for a language before it has learners.

## 7. When the money comes back

| Item | Assumed | Note |
|---|---|---|
| Hosting, domain, email | $700/yr | Supabase, DigitalOcean, sender domain |
| Content generation spend to date | $300–1,500 | The admin cost panel knows the real figure |
| Native review, 3 languages | $2,250 | §6 |
| Legal review of terms | $500–1,500 | §5 |
| Developer accounts | $124 | Only once §2 says go |
| **Cash to recover** | **$4,000–7,000** | The actual payback target |
| Revenue per subscriber | $119/yr | Blended across the three rungs (appendix §5) |
| Less AI, Stripe, speech | −32% | At median usage |
| **Contribution per subscriber** | **~$81/yr** | **Break-even ≈ 50–90 subscribers, ever** |

Monthly cash-flow break-even arrives far earlier, around 10 subscribers —
$675 of annual fixed cost against $81 of contribution each.
Expect the cash back within the first six to twelve months of charging if any
channel works at all.

Two caveats. Priced at any market rate, twelve months of evenings is north of
$40,000 of foregone billing, and recovering *that* needs ~2,000 subscribers
and three years — an outcome most solo edtech never reaches (`BUSINESS_PLAN.md`
§7 says so plainly). Treat the cash as the target and the time as the bet.
And the predictive number isn't cost, it's **paid conversion across the first
500 signups**: below 2% the positioning or price is wrong; 4–8% is a working
niche tool.

## 8. The niche

**B1→C1 in the languages that stop having materials at B1.** Don't choose
between "intermediate learners" and "underserved languages" — sell the
intersection. For Spanish at B1 the app is the fortieth option; for
**Persian, Swahili and Hebrew** at B1 there is essentially nothing but
somebody's Anki deck.

"Intermediate" isn't marketable because nobody searches for it. Name the
moment: *the learner who can read a menu but not a news article, has ~1,500
words and no reliable grammar, and has already quit two apps.* That person
knows what's wrong with their study and already spends money on it.

Why those three: large heritage/diaspora populations that reach B1 through
family and stall; all three non-Latin, where the keyboard/transliteration/
letters work is real engineering nobody will replicate for a small market
(Korean is in the app but crowded); and no intermediate-level commercial
product to displace.

Roadmap implications: at B1 the bottleneck is input volume and speaking
confidence, not more flashcards — so Reader nonfiction quality, per-sentence
audio and the speaking mode in progress are the highest-value work, and all
three are already queued. Don't add languages (22 is already more than can be
reviewed) and don't chase A1 beginners. Line to test in public: *"You
finished the beginner app. Now read the news."*

## 9. Where to post for feedback

Before any post: **ten recorded thirty-minute calls** with intermediate
learners of the wedge languages. Then, ordered by expected value rather than
audience size:

| Where | Why | How to behave |
|---|---|---|
| Direct learner calls | The only channel that says *why* | Recruit from per-language communities; offer a free year |
| **language-learners.org** (HTLAL successor) | Small, expert; the crowd that already pays for tools | A learning log or a real methods question, never an announcement |
| Per-language subreddits (r/persian, r/swahili, r/hebrew) | The wedge audience, starved of intermediate material | Answer questions for weeks first |
| r/languagelearning, r/Anki, r/LanguageTechnology | Large and relevant; r/Anki engages seriously on FSRS | Read the self-promo rules literally; use the weekly thread |
| Small creators (5k–50k subs) | Highest conversion on this list | Lifetime account, honest review, no script |
| italki / tutoring communities | Teachers recommend tools daily; underused | Build a teacher referral path |
| Show HN | Good for the engineering story (FSRS, level-locking, scripts) | Expect hard AI-accuracy questions; §5 is the answer |
| Discords, general and per-language | Where learners are daily | Ask the mods first, always |
| Product Hunt | One-day spike, weak retention | Only after paywall and onboarding work |
| University departments, heritage schools | Institutional angle for the wedge languages | One professor per language, specific offer |

Framing that gets useful answers: not "here's my app, thoughts?" but *"how
did you get from B1 to B2 in Persian, and what was missing?"* Write the
answers down verbatim — the sentences learners use for their own plateau are
the landing-page copy.

---

## Appendix — the cost model, tier by tier

*Added after the owner's follow-up: "The AI feature is why I switched to
monthly percentages. Base prices plus AI addition versions plus AI with the AI
allowance, plus maybe additional add-ons for AI. I need to know how with the
TTS, Supabase, hosting, AI costs how to make a reasonable revenue."*

The monthly-percentage meter was the right call. It just needs one fix to be
honest, because the actions behind it differ in cost by 30×.

### 1. What each action actually costs

Sonnet 5 at $3/$15 per MTok, cached input read at ~0.1×, Azure Speech at
$16/1M neural TTS characters and $0.18/hour batch STT (rates from
`docs/plans/speak-speech.md`).

| Action | Model | Speech | Total |
|---|---|---|---|
| Tutor turn (system block cached) | $0.0093 | — | **$0.009** |
| Speak turn | $0.009 | STT $0.0008 + TTS $0.002 | **$0.012** |
| Reader text, medium (generate + grade) | $0.074 | — | **$0.075** |
| Reader text, long C2, graded + rewritten | $0.27 | — | **$0.28** |
| Reader text read aloud (whole text) | — | $0.022 | **$0.022** |
| Gym set (items + chart) | $0.034 | — | **$0.034** |
| Weekly picks | $0.024 | — | **$0.024** |
| Session summary (operator-side, not drawn) | $0.021 | — | **$0.021** |

Two things fall out immediately:

- **Speech is not the problem.** A whole 20-turn spoken conversation costs
  about 6¢ of Azure and 18¢ of model. Azure's free tier (5 STT hours and
  500K TTS characters a month) covers roughly the first 200 conversations
  each month at zero cost. TTS is a rounding error next to text generation.
- **The Reader is 8–30× a tutor message** and currently draws the same single
  unit from the pool. That is the whole margin risk in one line.

### 2. Make the meter weigh what it counts

Keep one number and one percentage — learners understand it. Weight what
draws it:

| Action | Units | Cost per unit |
|---|---|---|
| Tutor or Speak turn | 1 | $0.009–0.012 |
| Weekly picks | 2 | $0.012 |
| Gym set | 2 | $0.017 |
| Reader text, short/medium | 3 | $0.025 |
| Reader text, long | 5 | $0.056 |

Plan on **$0.02 per unit** for a normal mix and **$0.05** for an adversarial
one. Weights alone don't bound the worst case, so add the second mechanic:

**A visible sub-cap on Reader texts per month.** The pool bounds the volume;
the sub-cap bounds the *shape*. Without it, a learner can spend a 300-unit
pool entirely on long C2 texts and cost $17 against $10 of monthly revenue.
With it, the same account cannot exceed a known number.

### 3. Fixed costs

| Item | Monthly | Note |
|---|---|---|
| Supabase Pro | $25 | List price — verify on the invoice |
| DigitalOcean app + database | $20 | One small instance |
| Domain, transactional email | $11 | |
| Azure Speech | $0 | F0 free tier at current volume |
| **Total** | **~$56** | **~$675/year** |

Fixed cost per subscriber collapses with scale: $1.12/month at 50
subscribers, $0.11 at 500. It is not what decides this business — AI COGS is.

Stripe is the other fixed drag, and it argues for annual billing on its own:
2.9% + 30¢ means a $119 annual charge costs $3.75, while twelve $14 charges
cost $8.52. Annual billing saves nearly $5 a subscriber a year *and* hands
you the cash before you incur the AI cost that year.

### 4. The ladder

Free SRS stays free — it is the top of the funnel, and its variable cost is
capped at pennies. The paid rungs differ only in AI.

| Rung | Monthly | Annual | Units/mo | Reader cap | Median AI cost | Cap AI cost |
|---|---|---|---|---|---|---|
| Free | $0 | — | 20 | 2 | $0.25 | $0.75 |
| **Starter** | $8 | **$69** ($5.75/mo) | 120 | 8 | $1.10 | $3.30 |
| **Standard** (hero) | $14 | **$119** ($9.92/mo) | 300 | 16 | $2.50 | $6.30 |
| **Immersion** | $24 | **$199** ($16.58/mo) | 600 | 25 | $5.50 | $11.30 |
| Top-up pack | $6 one-off | — | +120 | +8 | $2.40 | $3.30 |

Design rules behind those numbers:

- **Median AI cost ≤ 25% of price.** Comfortable.
- **Absolute-cap AI cost ≤ 70% of price.** The 1–2% of accounts that max
  their pool are near break-even, not loss-making, and a fair-use clause in
  the terms lets you throttle a true outlier.
- **Packs, never overage billing.** A surprise charge produces refunds and
  chargebacks; a deliberate $6 purchase does not. Price packs at roughly
  2.5× marginal cost.
- **Route by need.** Put the Reader's grading pass and the session summarizer
  on Haiku 4.5 ($1/$5) — both are fixed-rubric jobs — and about 20% of AI
  COGS disappears without a learner noticing.

### 5. What the revenue actually looks like

Contribution per subscriber per year, at median usage, after Stripe, AI and
speech:

| Rung | Price | Stripe | AI + speech | **Contribution** |
|---|---|---|---|---|
| Starter | $69 | $2.30 | $14 | **$52** |
| Standard | $119 | $3.75 | $32 | **$83** |
| Immersion | $199 | $6.07 | $70 | **$123** |

At a 25 / 60 / 15 mix, blended contribution is **~$81 per subscriber per
year**. Against $675 of fixed cost:

| Subscribers | Contribution | Less fixed | **Annual profit** |
|---|---|---|---|
| 10 | $810 | $675 | **~$135** — costs covered |
| 100 | $8,100 | $700 | **~$7,400** |
| 300 | $24,300 | $1,200 | **~$23,000** |
| 1,000 | $81,000 | $3,000 | **~$78,000** |
| 3,000 | $243,000 | $10,000 | **~$233,000** |

So the answer to "how do I make reasonable revenue" is a subscriber count,
not a price change:

- **Costs covered: ~10 subscribers.**
- **$1,000/month of side income: ~150 subscribers.**
- **Part-time salary ($30k): ~370 subscribers.**
- **Full-time ($80k): ~1,000 subscribers.**

The pricing above is not the constraint — at $81 of contribution per
subscriber, the business works at any of those scales. Distribution is the
constraint, which is why §8 and §9 matter more than this appendix does.

### 6. The two numbers to watch monthly

1. **AI cost ÷ subscription revenue.** Target under 25%. Over 30% for two
   months running means the pools are too generous or the mix has shifted
   toward the Reader.
2. **The p95 subscriber's AI cost.** The median is reassuring and useless; the
   95th percentile is what tells you whether the caps are doing their job.
   Both come out of `tutor_usage` with the token columns already there.

## The next thirty days

1. **Weight the allowance draw** (Reader 3, Gym 2) and cache the Reader/Gym
   prompts. The only engineering that blocks charging.
2. **Pick the three wedge languages**; get three review quotes each.
3. **Decide the name**; check the trademark before store listings exist.
4. **Ten learner calls** — recruit this week.
5. **Draft the three legal artefacts** together with the per-language quality
   badge; the badge is what makes the terms true.
6. **Turn Stripe on for the wedge languages only,** with the founder rate.
   Free elsewhere until reviewed.

## Numbers to instrument now

- **AI cost per paying subscriber per month** — whether the pricing works.
- **Cost per active learner by language** — drives review spend and model
  overrides.
- **Paid conversion of the first 500 signups** — below 2% is positioning.
- **Reader texts per subscriber per month** — the usage pattern that can
  invert the margin.
- **Week-2 return rate** — when it plateaus, §2 becomes urgent.
- **Speech spend per language** — before auto-listening ships.

## What to verify before acting

Competitor prices, Azure speech rates, reviewer hourly rates, store
commission programmes and App Review guideline 3.1.3 all move, and the
consumer-law points in §5 are a direction to take to a lawyer rather than
legal advice. Model rates and the allowance/ceiling figures are current as of
this memo's date and read from the repository respectively.
