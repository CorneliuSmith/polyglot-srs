import type { ContributorRole } from '../api/contribute'

/**
 * What a set of roles lets someone do — the client-side mirror of
 * backend/repositories/contributor.py's can_contribute / can_review /
 * can_trial_review.
 *
 * These exist so NAVIGATION can be decided from the roles payload, which is
 * tiny and shared by every page, instead of from the per-language contributor
 * workspace, which loads a language's whole grammar list. The Account tab bar
 * used to read the workspace: while that query was in flight — or if it
 * failed — `canContribute` was false, the bar rendered nothing, and a
 * contributor had no route to their own panel. A slow network is not a reason
 * to hide someone's role from them.
 *
 * Presentation only, exactly like the "view as" downgrade these run on top
 * of: every privileged endpoint re-derives the caller's real roles.
 */

/** A role row applies to a language if it is global (null) or names it. */
function scoped(role: ContributorRole, languageId: string | null): boolean {
  return role.language_id === null || role.language_id === languageId
}

export function canContributeWith(
  roles: ContributorRole[],
  isAdmin: boolean,
  languageId: string | null,
): boolean {
  if (isAdmin) return true
  // A reviewer can approve content, so they can obviously also draft fixes
  // to it — same rule the backend applies.
  return roles.some(
    (r) => (r.role === 'contributor' || r.role === 'reviewer') && scoped(r, languageId),
  )
}

export function canReviewWith(
  roles: ContributorRole[],
  isAdmin: boolean,
  languageId: string | null,
): boolean {
  if (isAdmin) return true
  return roles.some((r) => r.role === 'reviewer' && scoped(r, languageId))
}

export function canTrialReviewWith(
  roles: ContributorRole[],
  isAdmin: boolean,
  languageId: string | null,
): boolean {
  if (canReviewWith(roles, isAdmin, languageId)) return true
  return roles.some((r) => r.role === 'trial_reviewer' && scoped(r, languageId))
}
