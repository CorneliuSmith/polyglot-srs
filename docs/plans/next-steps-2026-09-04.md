# Next steps — 4 Sep 2026

The checklist that follows the 3 September brief
(`owner-notes-2026-09-03.md`). Everything the brief called worth building
has shipped (#385–#393); this is what is left, in the order that unblocks
the most. Tick items here as they land — the file is the record.

**Owner** items need a hand or a decision only the owner has. **Agent**
items are built on request, in a session.

## Unblock what already shipped

- [x] **1. Apply the pending migrations** — `supabase db push` (done 4 Sep
  2026: `20261014` translation review items, `20261015` Speak
  no-corrections flag). Settings → Admin → Deployment lists what the live
  database is missing. *Owner.*
- [ ] **2. Run the tutor skill digest, per language** —
  `scripts/tutor_skill_digest.py <code> [--db-url …]`, one summary-model
  call each. Fold the bullets you accept into that language's `ERRORS.md`
  together with the stamp line it prints, and remove the code from
  `NEVER_DIGESTED` in `backend/services/tutor_skill_digest.py`. From then
  on the test fails when `docs/quality/<code>.md` changes without a
  re-digest. Start with the languages testers are using. *Owner (spend),
  or agent with a key.*
- [ ] **3. Work the AI translations queue** — Settings → Review, admin
  only. It fills from the next 15-minute sweep with the drill lines,
  explanations, grammar titles and example meanings the checker rejected,
  grouped by kind, each with the English source, the proposal and the card
  editor. *Owner / admin.*

## Open brief items (agent, on request)

- [x] **4. 7c phase 2 — markdown cards** (done 4 Sep 2026). A block with
  markdown syntax — `**bold**`, lists, tables, `code`, links — renders
  through react-markdown + rehype-sanitize; plain blocks keep the
  typesetter, so no existing card moved (the 3,786 seed texts carry no
  markers, and a test now keeps it that way). The server strips raw HTML
  and unsafe links at every writer. The editor preview shows the result.
  Not in: colour classes (DEBT.md).
- [ ] **5. 7b — the popup.** Only if the stepper feels wrong on the phone;
  it would duplicate focus mode.
- [ ] **6. The cross-queue stream.** One "next item across every queue"
  mode on top of the stepper. Worth it once the queues are busy.

## The release gate (unchanged, owner decision of 26 Aug 2026)

- [ ] **7. The Gym level.**
- [ ] **8. A comprehensive grammar-concept review.** Both before the
  production seeder sequence runs
  (`docs/decisions/2026-08-26-owner-decisions.md`). The app itself
  auto-deploys from `main`, so everything above is already live.

## Before end of month

- [ ] **9. Walk the go-live checklist** for the four plan options
  (`docs/DEPLOY.md`, from #388): Stripe price IDs for all four,
  `app_flags.monetization` staying off, the cancel-on-upgrade path
  exercised in test mode. *Owner.*
- [ ] **10. Retest recommendations on a single-language account** now
  that entitlement follows the pool rather than the tier name (#387).
  *Owner / a reviewer.*
