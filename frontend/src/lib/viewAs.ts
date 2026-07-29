import type { ContributorRole } from '../api/contribute'

/**
 * The access levels an admin can preview the app as. `null` means "my real
 * access" — the toggle off-state.
 *
 * This is DISPLAY order, not a ranking, because the roles do not form a
 * chain. `contributor` and `trial_reviewer` are SIBLINGS with disjoint
 * powers, and it is genuinely not the case that either outranks the other:
 *
 *              write content   see review queue   publish
 *   learner          –                 –             –
 *   contributor      yes               –             –
 *   trial_reviewer   –                yes            –
 *   reviewer         yes              yes           yes
 *   admin            yes              yes           yes    + accounts/roles
 *
 * So the real shape is a tree, not a ladder:
 *
 *   admin
 *     └── reviewer            (contributor + trial_reviewer + publish)
 *           ├── contributor       drafts content, cannot open the queue
 *           └── trial_reviewer    recommends on the queue, cannot draft
 *
 * Getting this wrong is tempting because the list looks sequential — but
 * "collapse KEPT_ROLES into a cumulative ladder" would hand contributors
 * queue access and trial reviewers the ability to edit content. Mirrors
 * can_contribute / can_trial_review in backend/repositories/contributor.py.
 */
export const VIEW_AS_LEVELS = [
  'learner',
  'contributor',
  'trial_reviewer',
  'reviewer',
] as const

export type ViewAsLevel = (typeof VIEW_AS_LEVELS)[number]

/**
 * What each level is CALLED in the UI. Note `trial_reviewer` displays as
 * "Tester": the owner renamed the role, and the stored value stays
 * `trial_reviewer` because it sits in a CHECK constraint
 * (20260709000000_reviewer_role.sql) that every existing grant depends on.
 * Renaming the value would be a migration with real rows behind it, for zero
 * user-visible gain — so label and value diverge here on purpose. If you are
 * grepping for the role in code, it is `trial_reviewer`; if you are looking
 * for it on screen, it is "Tester".
 */
export const VIEW_AS_LABEL: Record<ViewAsLevel, string> = {
  learner: 'Learner',
  trial_reviewer: 'Tester',
  contributor: 'Contributor',
  reviewer: 'Reviewer',
}

/** What each previewed level is allowed to keep — each level's OWN roles, not
 * an accumulation of the ones listed before it (see the tree above). 'admin'
 * is never in any row: previewing admin IS turning the preview off. */
const KEPT_ROLES: Record<ViewAsLevel, ReadonlySet<string>> = {
  learner: new Set(),
  // Deliberately NOT each other's supersets: a contributor drafting content
  // has no queue access, and a trial reviewer recommending on the queue
  // cannot draft.
  contributor: new Set(['contributor']),
  trial_reviewer: new Set(['trial_reviewer']),
  // Reviewer is the only level that subsumes both, plus publishing.
  reviewer: new Set(['contributor', 'trial_reviewer', 'reviewer']),
}

/**
 * Recast a real admin's roles as what the previewed level would see.
 *
 * Filtering alone does not work, and quietly produced the wrong answer for
 * every level: an admin holds a single `admin` row and no `contributor` or
 * `reviewer` rows, so `roles.filter(kept.has)` returned [] and EVERY preview
 * collapsed to Learner. "View as contributor" showed the learner's app.
 *
 * So the previewed roles are synthesized over the scope the admin's authority
 * already covers (per-language for a scoped admin, global for a global one).
 *
 * SECURITY: still cannot widen access. The synthesis branch is reachable only
 * when the caller is REALLY an admin — someone who already outranks every
 * level in VIEW_AS_LEVELS — so the result is always weaker than what they
 * hold. A non-admin gets the plain filter, which can only remove. And every
 * privileged endpoint re-derives the caller's real roles server-side, so a
 * tampered store can hide buttons but can never grant access.
 */
export function downgradeRoles(
  roles: ContributorRole[],
  viewAs: ViewAsLevel | null,
): ContributorRole[] {
  if (!viewAs) return roles
  const kept = KEPT_ROLES[viewAs]
  const real = roles.filter((r) => kept.has(r.role))

  const adminScopes = roles
    .filter((r) => r.role === 'admin')
    .map((r) => r.language_id)
  if (adminScopes.length === 0) return real

  const seen = new Set(real.map((r) => `${r.language_id}:${r.role}`))
  const out = [...real]
  for (const language_id of adminScopes) {
    for (const role of kept) {
      const key = `${language_id}:${role}`
      if (seen.has(key)) continue
      seen.add(key)
      out.push({ language_id, role })
    }
  }
  return out
}

/** The capability flags the contributor workspace hands the UI. Same rule:
 * a preview can only turn a flag off. */
export interface WorkspaceFlags {
  is_admin: boolean
  can_review: boolean
  can_trial_review?: boolean
  can_contribute: boolean
}

export function downgradeFlags<T extends WorkspaceFlags>(
  flags: T,
  viewAs: ViewAsLevel | null,
): T {
  if (!viewAs) return flags
  const kept = KEPT_ROLES[viewAs]
  return {
    ...flags,
    is_admin: false,
    can_review: flags.can_review && kept.has('reviewer'),
    can_trial_review:
      (flags.can_trial_review ?? false) &&
      (kept.has('trial_reviewer') || kept.has('reviewer')),
    can_contribute: flags.can_contribute && kept.has('contributor'),
  }
}
