import { describe, it, expect } from 'vitest'
import { safePrompt } from '../features/review/hintLayers'

describe('safePrompt — the Gym prompt must never give the answer', () => {
  it('strips a spelled-out recipe clause', () => {
    expect(safePrompt('to watch — add -es', 'watches')).toBe('to watch')
    expect(safePrompt('to study — y changes to -ies', 'studies')).toBe('to study')
    expect(safePrompt('to fly — y becomes -ies', 'flies')).toBe('to fly')
  })

  it('blanks the prompt when the base form IS the answer', () => {
    expect(safePrompt('to speak', 'speak')).toBe('')
    expect(safePrompt('speak', 'speak')).toBe('')
  })

  it('keeps legitimate cues that do not reveal the answer', () => {
    expect(safePrompt('preparar, tú', 'preparas')).toBe('preparar, tú')
    expect(safePrompt('go — past', 'went')).toBe('go — past')
    expect(safePrompt('the indefinite article', 'a')).toBe('the indefinite article')
  })

  it('matches the answer only as a whole word', () => {
    // "comer" contains "come" as a substring but not a whole word.
    expect(safePrompt('comer, tú', 'come')).toBe('comer, tú')
    // A stripped lemma that still equals the answer is blanked.
    expect(safePrompt('to run — no change', 'run')).toBe('')
  })

  it('handles empty / missing input', () => {
    expect(safePrompt('', 'x')).toBe('')
    expect(safePrompt('to watch', null)).toBe('to watch')
    expect(safePrompt('to watch', undefined)).toBe('to watch')
  })
})
