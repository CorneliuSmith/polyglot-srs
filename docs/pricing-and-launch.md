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

| Plan | Price | AI pool | Median AI cost | Why |
|---|---|---|---|---|
| Free | $0 | 20 msg/mo | ~$0.30 | Learn/Review forever; a real taste of the tutor |
| Single language | $8/mo · $59/yr | 100 | ~$1.10 | The downsell; exists to make all-access look right |
| **All languages** | **$14/mo · $99/yr** | **300** | **~$1.80** | The hero plan. Breadth is the differentiator |
| Tutor+ add-on | +$12/mo | +1,000 | ~$9–15 | Only sound *after* the two fixes below |
| Lifetime | $249, 50 seats | 300/mo | ~$22/yr | Front-loads cash; never promise unlimited AI |

Plus a **founder rate of $69/yr locked for life for the first 100
subscribers** — it buys testimonials and review recruits, not just revenue.

### The arithmetic

Per-action model cost, all four drawing **one** unit from the same pool
(`repositories/tutor.py` counts `chat`, `gym_gen`, `gym_chart`, `recs`):

| Action | Cost | Why |
|---|---|---|
| Tutor message | ~$0.009 | ~3k in / ~450 out, and the system block is already cached (`services/tutor.py`) |
| Gym set | ~$0.05 | Uncached generation |
| Weekly picks | ~$0.05 | One batch |
| Reader text, typical | ~$0.10 | ~3.5k output tokens plus the contract grader |
| Reader text, worst | ~$0.30 | Long C2: up to two full generations at the 16,384-token ceiling (#287), graded |

So 300 messages spent entirely on chat costs ~$2.80; spent entirely on long
Reader texts it costs up to **$90 against $99 of annual revenue**. That is a
metering problem, not a pricing one:

1. **Weight the draw** — a Reader text should cost 3 units and a Gym
   generation 2. The learner still sees one honest number; the cap then
   actually bounds cost. Small change to the counted-kinds query.
2. **Cache the Reader and Gym prompts** the way the tutor's are, and route
   the grading pass to Haiku — a fixed-rubric yes/no judgement does not need
   the expensive model.

Model rates used: Opus 5 $5/$25 per MTok, Sonnet 5 $3/$15 (intro $2/$10
through 2026-08-31), Haiku 4.5 $1/$5; cached input reads ≈ 0.1×.

$99/yr sits at the top of the indie band (Bunpro/LingQ/Migaku anchor roughly
$50–155/yr). Holding the top of that band needs the bundle *and* reviewed
content — which is why §6 comes before the Stripe switch. Sell the year, not
the month: $99 against $168 is a 41% saving, deep enough to move buyers and
worth twelve months of retention you'd otherwise re-earn monthly.

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
| Revenue per subscriber | $99/yr | Blended toward annual all-access |
| Less AI (~22%), Stripe (~4%), hosting share | −28% | At median usage |
| **Contribution per subscriber** | **~$71/yr** | **Break-even ≈ 70–100 subscribers, ever** |

Monthly cash-flow break-even arrives far earlier, around 15–20 subscribers.
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
