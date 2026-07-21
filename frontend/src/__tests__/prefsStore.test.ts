import { describe, it, expect } from 'vitest'
import { usePrefsStore } from '../stores/prefsStore'

describe('prefs defaults', () => {
  it('hints default to fully revealed (beta report: bare cloze is unanswerable)', () => {
    expect(usePrefsStore.getState().hintLevel).toBe(9)
  })

  it('listening mode and accents-optional stay opt-in', () => {
    const s = usePrefsStore.getState()
    expect(s.listeningMode).toBe(false)
    expect(s.accentsOptional).toBe(false)
  })
})
