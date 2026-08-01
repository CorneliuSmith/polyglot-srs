import { describe, it, expect } from 'vitest'
import {
  canContributeWith,
  canReviewWith,
  canTrialReviewWith,
} from '../lib/roleFlags'
import { downgradeRoles } from '../lib/viewAs'
import { accountTabsFor } from '../features/settings/SettingsPage'

const ES = 'lang-es'
const AR = 'lang-ar'

describe('role flags', () => {
  it('an admin can do everything, everywhere', () => {
    expect(canContributeWith([], true, ES)).toBe(true)
    expect(canReviewWith([], true, ES)).toBe(true)
    expect(canTrialReviewWith([], true, ES)).toBe(true)
  })

  it('a plain learner can do none of it', () => {
    expect(canContributeWith([], false, ES)).toBe(false)
    expect(canReviewWith([], false, ES)).toBe(false)
    expect(canTrialReviewWith([], false, ES)).toBe(false)
  })

  it('a reviewer can also contribute — approving implies drafting', () => {
    const roles = [{ language_id: ES, role: 'reviewer' }]
    expect(canContributeWith(roles, false, ES)).toBe(true)
    expect(canReviewWith(roles, false, ES)).toBe(true)
  })

  it('a contributor cannot approve', () => {
    const roles = [{ language_id: ES, role: 'contributor' }]
    expect(canContributeWith(roles, false, ES)).toBe(true)
    expect(canReviewWith(roles, false, ES)).toBe(false)
  })

  it('a role stays inside its language', () => {
    const roles = [{ language_id: ES, role: 'reviewer' }]
    expect(canReviewWith(roles, false, AR)).toBe(false)
  })

  it('a null scope means every language', () => {
    const roles = [{ language_id: null, role: 'reviewer' }]
    expect(canReviewWith(roles, false, AR)).toBe(true)
  })

  it('a trial reviewer can recommend but not publish', () => {
    const roles = [{ language_id: ES, role: 'trial_reviewer' }]
    expect(canTrialReviewWith(roles, false, ES)).toBe(true)
    expect(canReviewWith(roles, false, ES)).toBe(false)
    expect(canContributeWith(roles, false, ES)).toBe(false)
  })
})

describe('the Account tabs an admin sees while previewing', () => {
  // The bug: "view as Contributor" rendered a learner's page with no tab bar
  // at all, while "view as Reviewer" showed all three tabs.
  const adminRoles = [{ language_id: null, role: 'admin' }]

  const tabsFor = (
    level: 'learner' | 'contributor' | 'trial_reviewer' | 'reviewer' | null,
  ) => {
    const roles = downgradeRoles(adminRoles, level)
    const isAdmin = level === null
    return accountTabsFor({
      canContribute: canContributeWith(roles, isAdmin, ES),
      canReview: canReviewWith(roles, isAdmin, ES),
      canTrialReview: canTrialReviewWith(roles, isAdmin, ES),
      isAdmin,
    })
  }

  it('as themselves: everything', () => {
    expect(tabsFor(null)).toEqual(['learner', 'contribute', 'review', 'admin'])
  })

  it('as a contributor: Learner and Contribute — not nothing', () => {
    expect(tabsFor('contributor')).toEqual(['learner', 'contribute'])
  })

  it('as a reviewer: Learner, Contribute and Review', () => {
    expect(tabsFor('reviewer')).toEqual(['learner', 'contribute', 'review'])
  })

  it('as a learner: just Learner', () => {
    expect(tabsFor('learner')).toEqual(['learner'])
  })

  it('as a trial reviewer: Learner and Review — the queue they exist to work', () => {
    // Regression: accountTabsFor only asked canReview, so a trial reviewer got
    // nothing but Learner. The queue was unreachable and their guide panel
    // rendered inside a tab they could not open. Caught from a screenshot of
    // the live preview, not from a test.
    expect(tabsFor('trial_reviewer')).toEqual(['learner', 'review'])
  })

  it('a trial reviewer reaches Review WITHOUT Contribute', () => {
    // The disjointness, at the tab layer: queue access must not imply the
    // ability to draft content.
    const tabs = tabsFor('trial_reviewer')
    expect(tabs).toContain('review')
    expect(tabs).not.toContain('contribute')
  })

  it('a contributor reaches Contribute WITHOUT Review', () => {
    const tabs = tabsFor('contributor')
    expect(tabs).toContain('contribute')
    expect(tabs).not.toContain('review')
  })

  it('no preview ever reaches Admin', () => {
    for (const level of ['learner', 'contributor', 'trial_reviewer', 'reviewer'] as const) {
      expect(tabsFor(level)).not.toContain('admin')
    }
  })
})

describe('contributor and trial_reviewer are siblings, not ranked', () => {
  // The view-as list reads like a ladder, which invites "simplifying"
  // KEPT_ROLES into a cumulative one. That would hand contributors review-queue
  // access and trial reviewers the ability to edit content — neither of which
  // the backend permits. These pin the disjointness.
  const contributor = [{ language_id: ES, role: 'contributor' }]
  const trialReviewer = [{ language_id: ES, role: 'trial_reviewer' }]

  it('a contributor can write content but cannot open the review queue', () => {
    expect(canContributeWith(contributor, false, ES)).toBe(true)
    expect(canTrialReviewWith(contributor, false, ES)).toBe(false)
  })

  it('a trial reviewer can open the queue but cannot write content', () => {
    expect(canTrialReviewWith(trialReviewer, false, ES)).toBe(true)
    expect(canContributeWith(trialReviewer, false, ES)).toBe(false)
  })

  it('neither outranks the other — each can do something the other cannot', () => {
    const contributorOnly =
      canContributeWith(contributor, false, ES) &&
      !canContributeWith(trialReviewer, false, ES)
    const trialOnly =
      canTrialReviewWith(trialReviewer, false, ES) &&
      !canTrialReviewWith(contributor, false, ES)
    expect(contributorOnly && trialOnly).toBe(true)
  })

  it('only reviewer subsumes both', () => {
    const reviewer = [{ language_id: ES, role: 'reviewer' }]
    expect(canContributeWith(reviewer, false, ES)).toBe(true)
    expect(canTrialReviewWith(reviewer, false, ES)).toBe(true)
    expect(canReviewWith(reviewer, false, ES)).toBe(true)
  })

  it('previewing as contributor does not smuggle in trial-reviewer powers', () => {
    // The bug a cumulative ladder would introduce, guarded at the seam an
    // admin actually exercises.
    const roles = downgradeRoles([{ language_id: null, role: 'admin' }], 'contributor')
    expect(canContributeWith(roles, false, ES)).toBe(true)
    expect(canTrialReviewWith(roles, false, ES)).toBe(false)
  })

  it('previewing as trial reviewer does not smuggle in contributor powers', () => {
    const roles = downgradeRoles([{ language_id: null, role: 'admin' }], 'trial_reviewer')
    expect(canTrialReviewWith(roles, false, ES)).toBe(true)
    expect(canContributeWith(roles, false, ES)).toBe(false)
  })
})

describe('the ambassador', () => {
  // A third disjoint sibling: recruit, not write or check. Its whole value
  // is the boundary, so these pin what it does NOT reach.
  const ambassador = [{ language_id: null, role: 'ambassador' }]

  it('gets an Invite tab and nothing else', () => {
    expect(
      accountTabsFor({
        canContribute: false,
        canReview: false,
        canTrialReview: false,
        canAddAccounts: true,
        isAdmin: false,
      }),
    ).toEqual(['learner', 'invite'])
  })

  it('cannot edit content or open the review queue', () => {
    expect(canContributeWith(ambassador, false, ES)).toBe(false)
    expect(canReviewWith(ambassador, false, ES)).toBe(false)
    expect(canTrialReviewWith(ambassador, false, ES)).toBe(false)
  })

  it('an admin keeps the full Admin tab instead of a second Invite one', () => {
    // Admins already reach account creation through Admin; two doors to the
    // same room is just clutter.
    const tabs = accountTabsFor({
      canContribute: true,
      canReview: true,
      canTrialReview: true,
      canAddAccounts: true,
      isAdmin: true,
    })
    expect(tabs).toContain('admin')
    expect(tabs).not.toContain('invite')
  })

  it('a content role never gets the Invite tab', () => {
    for (const flags of [
      { canContribute: true, canReview: false, canTrialReview: false },
      { canContribute: false, canReview: true, canTrialReview: true },
    ]) {
      expect(
        accountTabsFor({ ...flags, canAddAccounts: false, isAdmin: false }),
      ).not.toContain('invite')
    }
  })

  it('previewing as ambassador does not smuggle in content powers', () => {
    const roles = downgradeRoles(
      [{ language_id: null, role: 'admin' }],
      'ambassador',
    )
    expect(canContributeWith(roles, false, ES)).toBe(false)
    expect(canTrialReviewWith(roles, false, ES)).toBe(false)
    expect(canReviewWith(roles, false, ES)).toBe(false)
  })

  it('previewing as reviewer does not smuggle in account creation', () => {
    // Reviewer subsumes the two CONTENT roles. It must not quietly pick up
    // a third that has nothing to do with content.
    const roles = downgradeRoles(
      [{ language_id: null, role: 'admin' }],
      'reviewer',
    )
    expect(roles.some((r) => r.role === 'ambassador')).toBe(false)
  })
})
