# One staff console (4 Sep 2026)

**Symptom.** The owner: "Is there a reason why workspace is different so
much from the account panels?" The Workspace (`/contribute`) and the
Account page's Workshop / Review / Admin tabs looked like two apps: one
narrow and English-only with the newest queues, one wide and translated
with an older panel set, each scoped to a different language.

**Cause.** Two staff consoles, built at different times, both left live.
Role tabs were bolted onto the Account page first; the Workspace was built
later as a per-language console; every new staff feature landed only in
the Workspace, and nothing removed the Account copies.

**Decision.** The Workspace is the only staff console. The Account page
keeps Learner and (for ambassadors) Invite, and shows a Workspace tab that
navigates there. Everything only the Account page had moves: the role
guides to the top of each Workspace tab, the deployment panel to Admin →
Rollouts, plan limits to Admin → Costs, the overlaps queue to the Review
tab (with a working inbox tile), and the app-feedback queue's read access
for every staff role. The Workspace takes the shared width ramp and a
translated frame. The standalone `/feedback` page becomes a redirect to
the queue; `ReviewQueue` and the Account page's grammar-payload fetch go.

**Alternatives that lost.** Folding the Workspace into the Account page
(would drag a per-language console into a per-person page and lose the
scope picker); styling the two to match (keeps the drift's cause); a
shared "StaffTabs" component rendered on both (still two maps).

**Cost.** One less door for ambassadors and admins who had learned the
Account route; the `settings.tabs.review/admin` catalog keys go; the
Workspace panels stay English (DEBT.md).

**Pattern.** Single source of truth for a surface: one page owns a
concern; other pages link to it rather than mount copies of it.
