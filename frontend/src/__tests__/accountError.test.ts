import { describe, it, expect } from 'vitest'
import { accountErrorMessage } from '../features/contribute/AccountsPanel'

describe('accountErrorMessage', () => {
  it('uses the server detail string when present', () => {
    expect(
      accountErrorMessage({ response: { data: { detail: 'An account with that email already exists.' } } }),
    ).toBe('An account with that email already exists.')
  })

  it('summarizes a 422 validation array', () => {
    expect(
      accountErrorMessage({ response: { data: { detail: [{ msg: 'password too short' }] } } }),
    ).toBe('password too short')
  })

  it('reports a network error when there is no response (the old blind spot)', () => {
    expect(accountErrorMessage({ message: 'Network Error' })).toMatch(/reach the server/i)
  })

  it('falls back for a response without a detail', () => {
    expect(accountErrorMessage({ response: { data: {} } })).toBe('Could not create the account.')
  })
})
