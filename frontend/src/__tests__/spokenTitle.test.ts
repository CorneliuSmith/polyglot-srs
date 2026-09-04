import { describe, it, expect } from 'vitest'
import { spokenTitle } from '../lib/spokenTitle'

describe('spokenTitle', () => {
  it('speaks the target-language side of a glossed title, not the gloss', () => {
    // The reported case: "there is / there are" was read in a French accent.
    expect(spokenTitle('Il y a — there is / there are')).toBe('Il y a')
    expect(spokenTitle('Er — the five jobs of one little word')).toBe('Er')
  })

  it('prefers the forms in parentheses', () => {
    expect(spokenTitle('Zijn — present (ben, bent, is, zijn)')).toBe('ben, bent, is, zijn')
    expect(spokenTitle('Subject pronouns (je, tu, il…)')).toBe('je, tu, il')
    expect(spokenTitle('Potential -nga- (ndingakunceda — may I?)')).toBe('ndingakunceda')
  })

  it('speaks a listed form after a colon, but not an English clause', () => {
    expect(spokenTitle('Subject pronouns: ik, jij, u, hij, zij…')).toBe('ik, jij, u, hij, zij')
    expect(spokenTitle('Word order: the verb comes second')).toBeNull()
    expect(spokenTitle('Negation: nicht')).toBe('nicht')
  })

  it('has nothing to say for a plain English title', () => {
    expect(spokenTitle('Present tense of -er verbs')).toBeNull()
    expect(spokenTitle('')).toBeNull()
  })
})
