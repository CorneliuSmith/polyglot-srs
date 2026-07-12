# Deploying PolyglotSRS for testers

This guide gets the app onto the public internet so friends can sign up and
study. Primary path: **DigitalOcean App Platform** (~$5–12/month). An
equivalent Render mapping is at the end; a raw Droplet/VPS is *not*
recommended for a test deployment (you'd be maintaining nginx, TLS,
systemd, and OS updates for no benefit).

## The one-paragraph architecture

Half the app is **already deployed**: the Postgres database, all seeded
content, and authentication live in your Supabase cloud project. You only
deploy two things — the **FastAPI backend** (one small always-on service)
and the **React frontend** (a static site, free). Both auto-deploy from
GitHub on push to `main`. Your friends' accounts, cards, and reviews land
in the same Supabase database you use today.

```
friends' browsers ──▶ static frontend (free)  ──▶ backend API ($5–12/mo)
                            │                          │
                            └────────▶ Supabase ◀──────┘
                                 (auth + Postgres — already live)
```

---

## 0. Pre-flight (15 minutes, do these first)

1. **Rotate the Supabase secrets.** The service-role key and DB password
   were pasted into chats during development — treat them as leaked before
   anything is public. Supabase dashboard → Settings → API → *Reset
   service_role key*; Settings → Database → *Reset database password*.
   Update your local `.env` with the new values (the deploy uses them too).
   - *New API-key model (optional):* Supabase is replacing the legacy
     `anon`/`service_role` keys with **publishable** (`sb_publishable_…`) and
     **secret** (`sb_secret_…`) keys; both coexist until you disable the old
     ones. This backend uses **neither** — it connects to Postgres directly
     and verifies tokens via the JWT secret / JWKS — so `SUPABASE_ANON_KEY`
     and `SUPABASE_SERVICE_ROLE_KEY` are optional and may be left blank. The
     only place a key matters is the **frontend** `VITE_SUPABASE_ANON_KEY`,
     where the publishable key is a drop-in for the anon key.
2. **Get the pooler connection string.** Supabase dashboard → Connect →
   **Session pooler** URI (looks like
   `postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres`).
   Use THIS as the deployed `DATABASE_URL`, not the direct URL — Supabase
   direct connections are IPv6-only and most PaaS hosts can't reach them.
   (Session mode, port 5432 — not the 6543 transaction pooler, which
   breaks asyncpg's prepared statements.)
3. **Decide the tutor mode** for the test:
   - **Recommended:** set a real `ANTHROPIC_API_KEY` and
     `TUTOR_FREE_ACCESS=false`. Friends get the free tier (20 tutor
     messages/month each) — real product behavior, and the allowance caps
     your API bill. Add `STRIPE_DEV_MOCK=true` if you want them to be able
     to "subscribe" to Plus for free while testing.
   - **Free:** leave `ANTHROPIC_API_KEY` empty — the tutor shows as
     unavailable; everything else works.
4. **Make sign-up painless.** Supabase dashboard → Authentication →
   Sign In / Up → email provider → turn **off** "Confirm email" for the
   test phase. Supabase's built-in mailer is rate-limited to a few emails
   per hour — with confirmation on, your third friend's signup email
   silently never arrives. (Re-enable with custom SMTP before a real
   launch.)

---

## 1. Backend on DigitalOcean App Platform

DigitalOcean → Create → **App Platform** → connect the GitHub repo,
branch `main`, autodeploy on.

**Component 1 — Web Service, built from the repo's `Dockerfile`.**
App Platform detects the Dockerfile automatically ("no components
detected" means it isn't on the selected branch yet — the buildpack
does NOT recognize a pyproject-only Python repo, which is exactly why
the Dockerfile exists). Everything heavy (spaCy model, WordNet,
camel-tools data) is baked into the image.

| Setting | Value |
|---|---|
| Source directory | `/` (repo root) |
| Build command | *(leave empty — the Dockerfile does it)* |
| Run command | *(leave empty — the image CMD runs uvicorn)* |
| HTTP port | `8080` |
| Health check | HTTP path `/api/health` |
| Instance size | **1 GB RAM** ($12/mo). You can try the $5 512 MB tier, but the NLP stack (spaCy + camel-tools + pymorphy3) will likely OOM under it — if the service restarts under load, this is why. |

**Backend environment variables** (App → Settings → Environment
Variables; mark the secrets as *encrypted*):

| Variable | Value |
|---|---|
| `DATABASE_URL` | the **session-pooler** URI from pre-flight step 2 |
| `SUPABASE_URL` | `https://<your-ref>.supabase.co` |
| `SUPABASE_ANON_KEY` | optional — unused by the backend; leave blank |
| `SUPABASE_SERVICE_ROLE_KEY` | optional — unused by the backend; leave blank |
| `SUPABASE_JWT_SECRET` | Settings → API → JWT keys (the HS256 secret) |
| `ENVIRONMENT` | `production` |
| `CORS_ORIGINS` | `["https://<your-frontend-url>"]` — JSON array, exact origin, no trailing slash. You'll fill the real value in after step 2 creates the frontend. |
| `TUTOR_FREE_ACCESS` | `false` (see pre-flight step 3) |
| `TUTOR_DEV_MOCK` | `false` |
| `ANTHROPIC_API_KEY` | your key, or empty to disable the tutor |
| `STRIPE_DEV_MOCK` | `true` for the test phase (fake "subscribe" grants Plus) |
| `APP_BASE_URL` | the frontend URL (used for post-checkout redirects) |

First build takes ~5–10 minutes (the NLP wheels are heavy). When it's up,
`https://<backend-url>/api/health` should return OK.

## 2. Frontend as a Static Site

Same app → Create Component → **Static Site**, same repo:

| Setting | Value |
|---|---|
| Source directory | `frontend` |
| Build command | `npm ci && npm run build` |
| Output directory | `dist` |
| Catchall document | `index.html` ← **required** — client-side routing 404s without it |

**Frontend environment variables** (these are baked in at *build* time —
change one and you must trigger a rebuild):

| Variable | Value |
|---|---|
| `VITE_SUPABASE_URL` | `https://<your-ref>.supabase.co` |
| `VITE_SUPABASE_ANON_KEY` | the anon key **or** the new publishable key (`sb_publishable_…`) — public by design, safe in a static build |
| `VITE_API_BASE_URL` | the backend URL from step 1, e.g. `https://polyglot-api-xxxxx.ondigitalocean.app` — no trailing slash |

Static sites are free on App Platform (up to 3). When it deploys, copy its
URL back into the backend's `CORS_ORIGINS` and `APP_BASE_URL` and redeploy
the backend component.

## 3. Point Supabase Auth at the deployed frontend

Supabase dashboard → Authentication → **URL Configuration**:

- **Site URL**: the frontend URL.
- **Redirect URLs**: add the frontend URL, plus
  `https://<frontend-url>/reset-password` (password-reset emails land
  there), and keep `http://localhost:5173` + `http://localhost:5173/reset-password`
  so local dev still works.

If you want Google sign-in for the testers, follow the provider setup in
[accounts-and-roles.md](accounts-and-roles.md) and add the deployed origin
to the Google OAuth client's authorized origins.

## 4. Smoke test (5 minutes, in an incognito window)

1. Open the frontend URL → sign up with a throwaway email → you land in
   onboarding (no email confirmation if you did pre-flight 4).
2. Pick Turkish → take the placement check → a few adaptive questions →
   level confirm → dashboard shows due counts.
3. Learn a batch, run a review, answer one right and one wrong.
4. Switch to Russian → start a review → the QWERTY pill appears under the
   blank; typing `privet` yields `привет`.
5. Open the tutor → free-tier meter shows "20 messages this month" (or
   "unavailable" if you skipped the API key).
6. Sign in as **ss2smith@gmail.com** → Contribute page shows the admin
   panels (Roles, Open issues, review policy).

If step 1 works but steps 2+ hang or error, it's almost always CORS or
`VITE_API_BASE_URL` — see troubleshooting.

## 5. Invite friends

Send them the frontend URL — that's it, sign-up is self-serve. Optional:

- Make a linguist friend a **reviewer**: Contribute → Roles → their email,
  role `reviewer`, their language. They can then work through the African
  draft points and file issues.
- Watch feedback: learner card-feedback and reviewer issues both surface
  on your Contribute page per language.

---

## Costs

| Piece | Cost |
|---|---|
| Frontend (static) | $0 |
| Backend (1 GB) | $12/mo ($5 if 512 MB survives your usage) |
| Supabase | current plan (free tier is fine for a friends test) |
| Anthropic API | usage — capped by the tutor allowances (20/mo free tier, 100/day Plus) |
| **Total** | **~$12/mo** |

## Alternative: Render (equally good)

Same shape, near-identical settings: a **Web Service** (Docker runtime
from the same Dockerfile, health check `/api/health`; Starter $7/mo is 512 MB — watch for
OOM; the free tier spins down and cold-starts ~1 min, fine for very casual
testing) plus a **Static Site** (free; add a rewrite rule `/*` →
`/index.html` for SPA routing). Env vars identical. Pick whichever
dashboard you prefer — the app doesn't care.

## When the test becomes real (WP10)

Before opening beyond friends: custom domain, re-enable email confirmation
with custom SMTP, real Stripe keys + webhook (`STRIPE_DEV_MOCK=false`),
Sentry error tracking, Supabase backups (paid plan), a nightly
`fit_fsrs_weights` cron, and `TUTOR_*` limits tuned to real usage. That
list lives in ROADMAP WP10.

## Troubleshooting

- **Frontend loads, every API call fails / CORS errors in the console** —
  `CORS_ORIGINS` must be a JSON array containing the exact frontend origin
  (scheme + host, no trailing slash, no path). Redeploy the backend after
  changing it.
- **API calls 404 or hit the wrong host** — `VITE_API_BASE_URL` was empty
  or wrong at build time. Fix the variable and *rebuild* the static site
  (env is baked in at build).
- **Backend can't connect to the database** (`Network is unreachable` /
  timeouts) — you used the direct Supabase URL, which is IPv6-only. Switch
  `DATABASE_URL` to the session-pooler URI (pre-flight 2).
- **"No components detected" when adding the repo** — the deploy branch
  doesn't have the `Dockerfile` yet (buildpacks don't recognize a
  pyproject-only repo). Merge/push it to `main` and re-run detection.
- **Build fails on `camel-tools`** — the Dockerfile already installs
  cmake/build-essential so source builds succeed; if it still fails,
  remove `camel-tools` from `pyproject.toml` for the deploy — Arabic
  answers then grade via the diacritic-folding fallback, acceptable for
  a friends test.
- **Service restarts / OOM under review load** — bump to the 1 GB
  instance; the NLP models are the memory hog.
- **Refreshing any page but `/` gives 404** — the static site is missing
  the catchall/rewrite to `index.html`.
- **Friends' signup emails never arrive** — Supabase's built-in mailer is
  rate-limited; disable "Confirm email" for the test (pre-flight 4).
- **Reset-password emails link somewhere broken** — the frontend URL (and
  `/reset-password`) must be in Supabase's redirect allow-list (step 3).

## Invite-only beta (friends-and-family)

Locking signup to admin-created accounts takes BOTH halves:

1. **Supabase (the enforcement)** — dashboard → Authentication →
   Sign In / Up: turn OFF "Allow new users to sign up"; under Providers,
   disable Google (and any other OAuth). Existing sessions keep working.
2. **Frontend (the honest UI)** — set `VITE_INVITE_ONLY=true` in the
   frontend build env. The login page then hides the Sign Up tab and the
   Google button and shows a "private beta" note.

Create accounts from Contribute → Accounts → "Manage accounts": enter an
email, Generate a password, Create — then hand the password to your
friend (they can change it via "Forgot password?"). The same panel edits
plans and deletes accounts.
