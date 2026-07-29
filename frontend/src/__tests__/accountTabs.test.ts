import { describe, it, expect } from 'vitest'
import { accountTabsFor, resolveTab } from '../features/settings/SettingsPage'

const LEARNER = { canContribute: false, canReview: false, isAdmin: false }
const CONTRIBUTOR = { canContribute: true, canReview: false, isAdmin: false }
const REVIEWER = { canContribute: true, canReview: true, isAdmin: false }
const ADMIN = { canContribute: true, canReview: true, isAdmin: true }

describe('accountTabsFor', () => {
  it('a learner gets Learner only', () => {
    expect(accountTabsFor(LEARNER)).toEqual(['learner'])
  })

  it('a CONTRIBUTOR can reach Contribute', () => {
    // The bar was gated on `canReview || isAdmin`, so a plain contributor saw
    // no tabs at all and had no route to their own panel (owner report:
    // "view as Contributor" rendered an empty page).
    expect(accountTabsFor(CONTRIBUTOR)).toEqual(['learner', 'contribute'])
  })

  it('a reviewer adds Review on top of Contribute', () => {
    expect(accountTabsFor(REVIEWER)).toEqual(['learner', 'contribute', 'review'])
  })

  it('an admin gets everything', () => {
    expect(accountTabsFor(ADMIN)).toEqual([
      'learner', 'contribute', 'review', 'admin',
    ])
  })

  it('each level is a superset of the one below it', () => {
    const [l, c, r, a] = [LEARNER, CONTRIBUTOR, REVIEWER, ADMIN].map(accountTabsFor)
    expect(c).toEqual(expect.arrayContaining(l))
    expect(r).toEqual(expect.arrayContaining(c))
    expect(a).toEqual(expect.arrayContaining(r))
  })
})

describe('resolveTab', () => {
  it('keeps a selection that is still available', () => {
    expect(resolveTab('review', accountTabsFor(REVIEWER))).toBe('review')
  })

  it('falls back to Learner when the selection disappears', () => {
    // Exactly the reported bug: sitting on Admin, then previewing as
    // Reviewer. Every panel is gated on an exact match, so the page rendered
    // a tab bar with nothing underneath.
    expect(resolveTab('admin', accountTabsFor(REVIEWER))).toBe('learner')
  })

  it('a contributor preview drops both Review and Admin', () => {
    const tabs = accountTabsFor(CONTRIBUTOR)
    expect(resolveTab('admin', tabs)).toBe('learner')
    expect(resolveTab('review', tabs)).toBe('learner')
    expect(resolveTab('contribute', tabs)).toBe('contribute')
  })

  it('never returns a tab the account cannot reach', () => {
    const all = ['learner', 'contribute', 'review', 'admin'] as const
    for (const flags of [LEARNER, CONTRIBUTOR, REVIEWER, ADMIN]) {
      const tabs = accountTabsFor(flags)
      for (const sel of all) {
        expect(tabs).toContain(resolveTab(sel, tabs))
      }
    }
  })
})
