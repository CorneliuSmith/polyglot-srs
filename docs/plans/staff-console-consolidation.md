# One staff console — 4 Sep 2026

**Question (owner):** "Is there a reason why workspace is different so much
from the account panels?"

**Answer:** history. Staff features were first bolted onto the Account
page as role tabs (Workshop / Review / Admin), then the Workspace
(`/contribute`) was built as a per-language console and every new staff
feature landed only there. Both stayed live, so an admin learned two maps
that drifted: different widths, different panel sets, different scoping,
one translated and one not.

**Decision:** the Workspace is the only staff console. The Account page
keeps what belongs to the person — Learner settings and, for ambassadors,
Invite — plus a Workspace tab that is a door. Nothing an account could do
on the Account page's staff tabs is lost; everything below names where it
went.

## What moves, and where (function parity)

| Was on the Account page | Now in the Workspace |
| --- | --- |
| Role guide ("How the Workshop / Review / Admin works") | top of the matching Workspace tab, same collapsible component |
| Deployment panel (build stamp, missing migrations) | Admin → Rollouts, first |
| Plan limits (per-tier allotments, monetization switch) | Admin → Costs & plans |
| Overlapping grammar points queue | Review tab, as a queue with its own inbox tile — the inbox's overlaps tile finally points somewhere |
| App-feedback queue readable by any staff role, triage admin-only | Review tab, same rule (it was admin-only in the Workspace; widened back) |
| Review queue's explicit "nothing waiting" | the Review Inbox's "All clear" |
| Invite panel (ambassador) | **stays on the Account page** — the ambassador is a learner with one power, not staff, and must never see the account roster |

Everything the Account page's Admin tab had that the Workspace already
had (analytics, engagement, visibility, generation, accounts, roles,
review policy, tutor model, costs) is simply no longer duplicated.

## Other consolidation found on the way

- `/feedback` was a third door to the same app-feedback queue. It is now
  a redirect into the Workspace's Review tab with that queue focused; the
  home-page alert and the admin digest link there directly. (The digest's
  "Open the feedback queue" link pointed at the Admin tab, which never
  held it.)
- `ReviewQueue` (Account-only wrapper around four panels, with four extra
  queries just to count for its empty state) is deleted.
- The Account page no longer fetches the grammar workspace payload on
  every visit — it only fed two admin controls that lived there.
- The Workspace takes the shared page-width ramp (`PAGE_WIDE`) and pairs
  independent admin cards into columns on wide screens; the review queues
  and the Workshop editor stay single-column (they are lists and a form).
- The Workspace chrome — heading, tab labels, admin section labels,
  content switch, loading and no-role copy — is translated in the six UI
  locales. The 42 staff panels stay English (DEBT.md).

## Deep links

The Account page never read a tab from the URL, so no `/settings?tab=`
link exists anywhere to break. Workspace links (`?tab=`, `?section=`,
`?queue=`, `?point=`) are unchanged; `/feedback` redirects.

## Out of scope

Translating the panels themselves (a multi-day pass), and merging the
bell and the inbox (they render the same taxonomy on purpose).
