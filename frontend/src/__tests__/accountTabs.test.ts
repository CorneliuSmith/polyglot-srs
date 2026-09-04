import { describe, it, expect } from 'vitest'
import { accountTabsFor, resolveTab } from '../features/settings/SettingsPage'

const LEARNER = { canContribute: false, canReview: false, isAdmin: false }
const CONTRIBUTOR = { canContribute: true, canReview: false, isAdmin: false }
const REVIEWER = { canContribute: true, canReview: true, isAdmin: false }
const TRIAL = { canContribute: false, canReview: false, canTrialReview: true, isAdmin: false }
const ADMIN = { canContribute: true, canReview: true, isAdmin: true }

describe('accountTabsFor', () => {
  // Since 4 Sep 2026 the Account page carries no staff panels: the staff
  // console is the Workspace alone, and the only staff thing here is the
  // door to it (docs/plans/staff-console-consolidation.md).
  it('a learner gets Learner only', () => {
    expect(accountTabsFor(LEARNER)).toEqual(['learner'])
  })

  it('every staff role gets the Workspace door — and nothing else here', () => {
    for (const flags of [CONTRIBUTOR, REVIEWER, TRIAL, ADMIN]) {
      expect(accountTabsFor(flags)).toEqual(['learner', 'workspace'])
    }
  })

  it('the door is one tab whatever the role: the Workspace sorts out its own', () => {
    // A trial reviewer and an admin land on different Workspace tabs, but
    // from here the route is the same. Two doors would be the old drift.
    expect(accountTabsFor(TRIAL)).toEqual(accountTabsFor(ADMIN))
  })
})

describe('resolveTab', () => {
  it('keeps a selection that is still available', () => {
    expect(resolveTab('invite', ['learner', 'invite'])).toBe('invite')
  })

  it('falls back to Learner when the selection disappears', () => {
    // The old bug, still worth pinning: a "view as" preview shrinks the
    // set, and a selection pointing at a vanished tab rendered nothing.
    expect(resolveTab('invite', accountTabsFor(REVIEWER))).toBe('learner')
  })

  it('never returns a tab the account cannot reach', () => {
    const all = ['learner', 'invite', 'workspace'] as const
    for (const flags of [LEARNER, CONTRIBUTOR, REVIEWER, TRIAL, ADMIN]) {
      const tabs = accountTabsFor(flags)
      for (const sel of all) {
        expect(tabs).toContain(resolveTab(sel, tabs))
      }
    }
  })
})
