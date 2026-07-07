# Accounts & roles

## Creating accounts

Everyone self-serves through the login page:

- **Email + password** — Sign Up tab → confirmation email → confirmed account.
  This always works; it needs no configuration beyond the Supabase project
  itself.
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
3. **Approve** — a reviewer for that language (or an admin) clicks
   *Approve (linguist sign-off)*. `reviewed = true`, `reviewed_by` = them,
   and the point immediately joins the learnable path.

Learner **feedback** on cards flows to the same page (Feedback panel) for
contributors to triage and resolve.
