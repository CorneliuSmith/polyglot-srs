import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  clearSnapshot,
  readSnapshot,
  saveSnapshot,
  snapshotKey,
} from '../features/review/sessionSnapshot'
import type { DueCard } from '../api/types'

const card = (id: string): DueCard => ({
  id, card_type: 'grammar', card_id: 'p1', sentence: `S ${id} {{answer}}.`,
  correct_answer: 'x', morphology: null, alternatives: null, language_code: 'es',
  ease_factor: 2.5, interval: 0, repetitions: 0, streak: 0, lapses: 0,
  next_review: 'now',
})

describe('sessionSnapshot', () => {
  beforeEach(() => sessionStorage.clear())

  it('keys by the exact session URL (path + query)', () => {
    expect(snapshotKey('/cram', '?points=a,b&count=10')).toBe(
      'review-session:/cram?points=a,b&count=10',
    )
  })

  it('round-trips a parked session', () => {
    const key = snapshotKey('/cram', '?points=a')
    saveSnapshot(key, {
      cards: [card('c1'), card('c2')],
      index: 1,
      results: [{ cardId: 'c1', answerResult: 'correct', timeTakenMs: 900 }],
      requeued: [],
    })
    const snap = readSnapshot(key)
    expect(snap?.cards.map((c) => c.id)).toEqual(['c1', 'c2'])
    expect(snap?.index).toBe(1)
    expect(snap?.results[0].answerResult).toBe('correct')
  })

  it('rejects a stale snapshot (older than the parking window)', () => {
    const key = snapshotKey('/review', '')
    saveSnapshot(key, { cards: [card('c1')], index: 0, results: [], requeued: [] })
    const seven_hours = 7 * 60 * 60 * 1000
    vi.spyOn(Date, 'now').mockReturnValue(Date.now() + seven_hours)
    expect(readSnapshot(key)).toBeNull()
    expect(sessionStorage.getItem(key)).toBeNull() // cleaned up
    vi.restoreAllMocks()
  })

  it('rejects a snapshot parked past its deck (nothing to resume)', () => {
    const key = snapshotKey('/review', '')
    saveSnapshot(key, { cards: [card('c1')], index: 1, results: [], requeued: [] })
    expect(readSnapshot(key)).toBeNull()
  })

  it('a requeued miss extends the resumable range', () => {
    const key = snapshotKey('/review', '')
    saveSnapshot(key, {
      cards: [card('c1')], index: 1, results: [], requeued: [card('c1')],
    })
    expect(readSnapshot(key)?.requeued).toHaveLength(1)
  })

  it('clearSnapshot removes the parking spot', () => {
    const key = snapshotKey('/review', '')
    saveSnapshot(key, { cards: [card('c1')], index: 0, results: [], requeued: [] })
    clearSnapshot(key)
    expect(readSnapshot(key)).toBeNull()
  })

  it('garbage in storage reads as no snapshot', () => {
    const key = snapshotKey('/review', '')
    sessionStorage.setItem(key, '{not json')
    expect(readSnapshot(key)).toBeNull()
  })
})
