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

  const tabsFor = (level: 'learner' | 'contributor' | 'reviewer' | null) => {
    const roles = downgradeRoles(adminRoles, level)
    const isAdmin = level === null
    return accountTabsFor({
      canContribute: canContributeWith(roles, isAdmin, ES),
      canReview: canReviewWith(roles, isAdmin, ES),
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

  it('every preview is a strict subset of the one above it', () => {
    const learner = tabsFor('learner')
    const contributor = tabsFor('contributor')
    const reviewer = tabsFor('reviewer')
    expect(contributor).toEqual(expect.arrayContaining(learner))
    expect(reviewer).toEqual(expect.arrayContaining(contributor))
    // And no preview ever reaches Admin.
    for (const tabs of [learner, contributor, reviewer]) {
      expect(tabs).not.toContain('admin')
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
