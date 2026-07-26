import type { DueCard } from '../../api/types'
import type { SessionResult } from './useReviewSession'

/**
 * Mid-session survival for the review/Gym session (the "change a setting and
 * come back" flow). Session state lives in unmount-fragile component state and
 * cram decks use gcTime 0, so navigating to Settings used to throw the whole
 * session away — including background-generated Gym drills that exist nowhere
 * else. A snapshot in sessionStorage, keyed by the session URL, lets the page
 * rebuild exactly where the learner left off.
 *
 * sessionStorage on purpose: per-tab, gone when the tab closes — this is a
 * parking spot, not persistence.
 */

export interface SessionSnapshot {
  cards: DueCard[]
  index: number
  results: SessionResult[]
  requeued: DueCard[]
  savedAt: number
}

/** A parked session older than this is stale — start fresh instead. */
const MAX_AGE_MS = 6 * 60 * 60 * 1000

export function snapshotKey(pathname: string, search: string): string {
  return `review-session:${pathname}${search}`
}

export function saveSnapshot(
  key: string,
  snap: Omit<SessionSnapshot, 'savedAt'>,
): void {
  try {
    sessionStorage.setItem(key, JSON.stringify({ ...snap, savedAt: Date.now() }))
  } catch {
    // Quota/serialization problems just mean no resume — never break the session.
  }
}

export function readSnapshot(key: string): SessionSnapshot | null {
  try {
    const raw = sessionStorage.getItem(key)
    if (!raw) return null
    const snap = JSON.parse(raw) as SessionSnapshot
    if (
      !Array.isArray(snap.cards) ||
      snap.cards.length === 0 ||
      typeof snap.index !== 'number' ||
      Date.now() - (snap.savedAt ?? 0) > MAX_AGE_MS
    ) {
      sessionStorage.removeItem(key)
      return null
    }
    // A snapshot parked past its deck has nothing to resume.
    if (snap.index >= snap.cards.length + (snap.requeued?.length ?? 0)) {
      sessionStorage.removeItem(key)
      return null
    }
    return { ...snap, results: snap.results ?? [], requeued: snap.requeued ?? [] }
  } catch {
    return null
  }
}

export function clearSnapshot(key: string): void {
  try {
    sessionStorage.removeItem(key)
  } catch {
    // ignore
  }
}
