import { describe, it, expect } from 'vitest'
import { pickTip, TIPS, TIP_THROTTLE_MS, allTipsSeen } from '../features/tips/tips'

const base = {
  enabled: true,
  seenTipIds: [] as string[],
  lastTipShownAt: 0,
  now: TIP_THROTTLE_MS + 1, // past the throttle window
  rand: () => 0, // deterministic: first of the pool
}

describe('pickTip', () => {
  it('returns nothing when tips are disabled', () => {
    expect(pickTip({ ...base, enabled: false })).toBeNull()
  })

  it('respects the throttle window', () => {
    // Shown just now → nothing until the window passes.
    expect(pickTip({ ...base, now: 1000, lastTipShownAt: 900 })).toBeNull()
  })

  it('shows a tip once the window has passed', () => {
    const tip = pickTip(base)
    expect(tip).not.toBeNull()
  })

  it('never repeats a tip the learner has already seen (until all are seen)', () => {
    const seenTipIds = TIPS.slice(0, TIPS.length - 1).map((t) => t.id)
    const tip = pickTip({ ...base, seenTipIds })
    expect(tip?.id).toBe(TIPS[TIPS.length - 1].id) // the only unseen one
  })

  it('prefers a tip fitting the current context', () => {
    const tip = pickTip({ ...base, context: 'session' })
    expect(tip?.contexts).toContain('session')
  })

  it('still cycles once every tip has been seen', () => {
    const seenTipIds = TIPS.map((t) => t.id)
    expect(allTipsSeen(seenTipIds)).toBe(true)
    // Fresh cycle: it returns something rather than going silent forever.
    expect(pickTip({ ...base, seenTipIds })).not.toBeNull()
  })
})
