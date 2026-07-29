import { describe, it, expect } from 'vitest'
import {
  VIEW_AS_LEVELS,
  downgradeFlags,
  downgradeRoles,
  type ViewAsLevel,
} from '../lib/viewAs'
import type { ContributorRole } from '../api/contribute'

const LANG = 'lang-1'
const adminRoles: ContributorRole[] = [
  { language_id: null, role: 'admin' },
  { language_id: LANG, role: 'reviewer' },
  { language_id: LANG, role: 'contributor' },
  { language_id: LANG, role: 'trial_reviewer' },
]

const fullFlags = {
  is_admin: true,
  can_review: true,
  can_trial_review: true,
  can_contribute: true,
}

describe('view-as downgrade', () => {
  it('is a no-op without a preview', () => {
    expect(downgradeRoles(adminRoles, null)).toEqual(adminRoles)
    expect(downgradeFlags(fullFlags, null)).toEqual(fullFlags)
  })

  it('never lets a preview keep the admin role', () => {
    for (const level of VIEW_AS_LEVELS) {
      const out = downgradeRoles(adminRoles, level)
      expect(out.some((r) => r.role === 'admin'), level).toBe(false)
      expect(downgradeFlags(fullFlags, level).is_admin, level).toBe(false)
    }
  })

  it('strips everything for the learner view', () => {
    expect(downgradeRoles(adminRoles, 'learner')).toEqual([])
    expect(downgradeFlags(fullFlags, 'learner')).toEqual({
      is_admin: false,
      can_review: false,
      can_trial_review: false,
      can_contribute: false,
    })
  })

  it('keeps only the contributor role for the contributor view', () => {
    const out = downgradeRoles(adminRoles, 'contributor')
    expect([...new Set(out.map((r) => r.role))]).toEqual(['contributor'])
    const flags = downgradeFlags(fullFlags, 'contributor')
    expect(flags.can_contribute).toBe(true)
    expect(flags.can_review).toBe(false)
  })

  it('lets the reviewer view keep publish rights and the weaker roles', () => {
    const out = downgradeRoles(adminRoles, 'reviewer')
    expect([...new Set(out.map((r) => r.role))].sort()).toEqual([
      'contributor', 'reviewer', 'trial_reviewer',
    ])
    const flags = downgradeFlags(fullFlags, 'reviewer')
    expect(flags.can_review).toBe(true)
    expect(flags.can_contribute).toBe(true)
    expect(flags.is_admin).toBe(false)
  })

  it('gives the trial reviewer advisory rights only', () => {
    const flags = downgradeFlags(fullFlags, 'trial_reviewer')
    expect(flags.can_trial_review).toBe(true)
    expect(flags.can_review).toBe(false)
    expect(flags.can_contribute).toBe(false)
  })

  it('can only ever REMOVE capability, never add it', () => {
    // The security property: whatever the real flags are, no preview level
    // turns a false into a true.
    const weak = {
      is_admin: false,
      can_review: false,
      can_trial_review: false,
      can_contribute: false,
    }
    for (const level of VIEW_AS_LEVELS as readonly ViewAsLevel[]) {
      expect(downgradeFlags(weak, level), level).toEqual(weak)
      expect(downgradeRoles([], level), level).toEqual([])
    }
  })
})

describe('view-as for a PLAIN admin (the shape a real admin account has)', () => {
  // The original fixture handed the admin explicit reviewer/contributor rows
  // as well, which hid the bug this covers: a real admin holds ONE row,
  // {language_id: null, role: 'admin'}. Filtering for the previewed role
  // found nothing in it, so every level collapsed to Learner and "view as
  // contributor" silently showed the learner's app.
  const plainAdmin: ContributorRole[] = [{ language_id: null, role: 'admin' }]

  it('actually produces the previewed role', () => {
    for (const level of ['trial_reviewer', 'contributor', 'reviewer'] as ViewAsLevel[]) {
      const out = downgradeRoles(plainAdmin, level)
      expect(out.length, level).toBeGreaterThan(0)
      expect(out.some((r) => r.role === level), level).toBe(true)
    }
  })

  it('inherits the admin scope, so the preview covers the same languages', () => {
    const out = downgradeRoles(plainAdmin, 'contributor')
    expect(out).toEqual([{ language_id: null, role: 'contributor' }])
  })

  it('a language-scoped admin previews only that language', () => {
    const scoped: ContributorRole[] = [{ language_id: LANG, role: 'admin' }]
    expect(downgradeRoles(scoped, 'contributor')).toEqual([
      { language_id: LANG, role: 'contributor' },
    ])
  })

  it('still strips everything for the learner view', () => {
    expect(downgradeRoles(plainAdmin, 'learner')).toEqual([])
  })

  it('never keeps or synthesizes admin', () => {
    for (const level of VIEW_AS_LEVELS) {
      expect(downgradeRoles(plainAdmin, level).some((r) => r.role === 'admin'))
        .toBe(false)
    }
  })

  it('NEVER widens a non-admin: synthesis is admin-only', () => {
    // The security property. A contributor previewing "reviewer" must not
    // gain a reviewer row — only a real admin, who already outranks every
    // previewable level, reaches the synthesis branch.
    const contributor: ContributorRole[] = [
      { language_id: LANG, role: 'contributor' },
    ]
    for (const level of VIEW_AS_LEVELS) {
      const out = downgradeRoles(contributor, level)
      expect(out.some((r) => r.role === 'reviewer'), level).toBe(false)
      expect(out.some((r) => r.role === 'admin'), level).toBe(false)
      expect(out.length, level).toBeLessThanOrEqual(contributor.length)
    }
  })

  it('does not duplicate a role the admin already holds explicitly', () => {
    const both: ContributorRole[] = [
      { language_id: null, role: 'admin' },
      { language_id: null, role: 'contributor' },
    ]
    expect(downgradeRoles(both, 'contributor')).toEqual([
      { language_id: null, role: 'contributor' },
    ])
  })
})
