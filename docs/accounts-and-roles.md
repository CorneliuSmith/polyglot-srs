# Accounts, tiers & roles

## Creating accounts

Everyone self-serves through the login page:

- **Email + password** — Sign Up tab → confirmation email → confirmed account.
  This always works; it needs no configuration beyond the Supabase project
  itself. **Forgot password?** on the login page emails a recovery link that
  lands on `/reset-password`; for the link to work, add your app origin's
  `/reset-password` URL to Supabase → Authentication → URL Configuration →
  Redirect URLs (e.g. `http://localhost:5173/reset-password`).
- **Google (and other OAuth providers)** — the button exists in the UI, but a
  provider only works after it's enabled **in the Supabase dashboard**. Until
  then Supabase returns `validation_failed: Unsupported provider: provider is
  not enabled` (the login page now explains this instead of failing silently).

### Enabling Google sign-in (one-time, ~10 minutes)

1. **Google Cloud Console** (console.cloud.google.com) → APIs & Services →
   Credentials → *Create credentials → OAuth client ID* (type **Web
   application**).
   - Authorized JavaScript origins: your app origin(s), e.g.
     `http://localhost:5173` and your production URL.
   - Authorized redirect URI:
     `https://<your-project-ref>.supabase.co/auth/v1/callback`
   - You may need to configure the OAuth consent screen first (External,
     add your email as a test user while unverified).
2. **Supabase dashboard** → Authentication → **Providers** → Google →
   toggle **Enable**, paste the **Client ID** and **Client secret**, save.
3. **Supabase dashboard** → Authentication → **URL Configuration** → set the
   Site URL to your app origin and add `http://localhost:5173` to the
   redirect allow-list for local dev.

That's it — no code changes. Any other provider (GitHub, Apple, …) follows
the same pattern; the login page can grow more buttons when one is enabled.

## Account tiers & what money buys

**Principle: revenue never scales with AI conversation volume.** Pricing is
flat per tier; the tutor allowances below are fair-use cost protection and
are shown openly in the UI (a meter on the tutor page, an honest panel when
a cap is hit). Users are never charged per message, and the SRS itself —
reviews, learning, all content — is **never** paywalled.

| Tier | Price | SRS | AI tutor |
|---|---|---|---|
| **Free** (every sign-up) | $0 | everything, forever | **20 messages / month** — a real trial, resets on the 1st |
| **Plus** (per-language Stripe subscription) | flat monthly price | everything | **100 messages / day** fair-use cap, resets daily |
| Operator mode (`TUTOR_FREE_ACCESS=true`) | — | — | unlimited (demos/dev; default until Stripe is live) |

Limits are counted in **messages** (the unit people understand), configured
via `TUTOR_FREE_MONTHLY_MESSAGES` / `TUTOR_PLUS_DAILY_MESSAGES`. Every
answered message is logged to `tutor_usage` (per-user, RLS-protected), which
doubles as the operator's cost-monitoring feed (token columns reserved,
WP9b). Hitting a cap returns a structured `402` with the tier, the limit,
and the exact reset time — the UI turns that into "resets on August 1"
plus an upgrade button (free) or "resets tomorrow, nothing extra to pay"
(Plus). A brisk per-minute rate limiter rides on top to stop scripted abuse.

Why this shape: metered AI billing punishes exactly the engaged learners the
product wants, and invisible caps feel like fraud. A flat price with a
visible, generous allowance keeps the operator's Claude bill bounded while
letting the learner budget with certainty.

## Roles

Roles live in `contributor_roles` (user, role, optional language scope).
A user with **no row is a learner** — the default for every sign-up; learners
never need a grant.

| Role | Scope | Can do |
|---|---|---|
| *(learner)* | — | study: reviews, learn, notes, tutor, feedback |
| `contributor` | one language or all (`language_id NULL`) | draft grammar explanations, create points, add/delete NLP-validated drills, see learner feedback. Drafts stay invisible to learners. |
| `reviewer` | one language or all | everything a contributor can, **plus approve** — the human sign-off that flips `reviewed = true` and exposes content to learners (`reviewed_by` records who) |
| `admin` | global | everything: approve anywhere, grant/revoke roles, set per-language review policy (`strict` / `ai_ok`), admin panels |

## Bootstrapping the first admin (you)

The first admin can't be granted from inside the app (no admin exists yet to
grant it). Once, from the repo root:

```bash
# 1. Sign up in the app with your email and confirm it.
# 2. Then:
./scripts/grant_admin.sh you@example.com
```

Every grant after that happens in the app: **Contribute page → Roles panel**
(visible to admins only) — grant `contributor` / `reviewer` / `admin` by
account email, scoped to a language or to all, and revoke from the same list.
The API equivalents are `GET /api/contribute/roles/all`,
`POST /api/contribute/roles`, `POST /api/contribute/roles/revoke`.

## How review works (content lifecycle)

1. **Draft** — a contributor saves an explanation / creates a point / adds
   drills. It's stored with `reviewed = false`: browsable by role-holders,
   invisible to learners. (Bulk-seeded content from `data/grammar/*.json`
   enters the same way — `reviewed` in the JSON is the source of truth.)
2. **AI check (optional)** — "Run AI check" stores a semantic verdict
   (`ai_check_status: pass/concerns` + notes) to help the human reviewer.
   Under the default `strict` policy this changes nothing for learners; a
   language set to `ai_ok` (admin toggle) surfaces AI-passed drafts.
3. **Flag an issue (optional)** — for problems a reviewer can't or
   shouldn't fix on the spot ("this is the Ibadan form", "tone marks look
   doubtful"), every point has a *Flag an issue* box. Open issues collect
   in the amber **Open issues** panel at the top of the Contribute page —
   visible to everyone with a role for the language, resolvable by its
   reviewers and admins once addressed.
4. **Approve** — a reviewer for that language (or an admin) clicks
   *Approve (linguist sign-off)*. `reviewed = true`, `reviewed_by` = them,
   and the point immediately joins the learnable path.

Learner **feedback** on cards flows to the same page (Feedback panel) for
contributors to triage and resolve.
