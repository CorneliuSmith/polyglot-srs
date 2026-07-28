import type { ContributorRole } from '../api/contribute'

/** The access levels an admin can preview the app as, weakest first. `null`
 * means "my real access" — the toggle off-state. */
export const VIEW_AS_LEVELS = [
  'learner',
  'trial_reviewer',
  'contributor',
  'reviewer',
] as const

export type ViewAsLevel = (typeof VIEW_AS_LEVELS)[number]

export const VIEW_AS_LABEL: Record<ViewAsLevel, string> = {
  learner: 'Learner',
  trial_reviewer: 'Trial reviewer',
  contributor: 'Contributor',
  reviewer: 'Reviewer',
}

/** What each previewed level is allowed to keep. Ordered weakest → strongest;
 * a level keeps its own row's roles and nothing above it. 'admin' is never in
 * any row — previewing admin IS turning the preview off. */
const KEPT_ROLES: Record<ViewAsLevel, ReadonlySet<string>> = {
  learner: new Set(),
  trial_reviewer: new Set(['trial_reviewer']),
  contributor: new Set(['contributor']),
  // A reviewer in this app can do everything a contributor can, plus publish.
  reviewer: new Set(['contributor', 'trial_reviewer', 'reviewer']),
}

/**
 * Strip a real admin's roles down to what the previewed level would see.
 *
 * SECURITY: this is presentation only, and it only ever REMOVES roles — there
 * is no input that makes the returned list stronger than the one passed in.
 * Every privileged endpoint re-derives the caller's real roles server-side, so
 * a tampered store can hide buttons but can never grant access.
 */
export function downgradeRoles(
  roles: ContributorRole[],
  viewAs: ViewAsLevel | null,
): ContributorRole[] {
  if (!viewAs) return roles
  const kept = KEPT_ROLES[viewAs]
  return roles.filter((r) => kept.has(r.role))
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
