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
    expect(out.map((r) => r.role)).toEqual(['contributor'])
    const flags = downgradeFlags(fullFlags, 'contributor')
    expect(flags.can_contribute).toBe(true)
    expect(flags.can_review).toBe(false)
  })

  it('lets the reviewer view keep publish rights and the weaker roles', () => {
    const out = downgradeRoles(adminRoles, 'reviewer')
    expect(out.map((r) => r.role).sort()).toEqual([
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
