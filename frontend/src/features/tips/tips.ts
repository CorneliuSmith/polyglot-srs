/**
 * Learning tips: short, evidence-based study nudges surfaced now and then —
 * before a session or on the dashboard. They're deliberately infrequent
 * (throttled to about once a day), never repeat until the learner has seen the
 * whole set, and lightly prefer whichever tip fits where they are. Default on;
 * a single toggle in Settings turns them off.
 */

export type TipContext = 'dashboard' | 'session'

export interface Tip {
  id: string
  /** Where this tip lands best. Used to gently prefer a fitting tip; a tip
   *  with no contexts can appear anywhere. */
  contexts?: TipContext[]
}

/** Tip copy lives in the i18n catalogs under `tips.items.<id>.{title,body}`,
 * resolved at render time by LearningTip so it follows the site language —
 * this module only carries ids and placement metadata. */
export const TIPS: Tip[] = [
  { id: 'read-aloud', contexts: ['session'] },
  { id: 'retrieval', contexts: ['session'] },
  { id: 'shadow', contexts: ['session'] },
  { id: 'generation', contexts: ['session'] },
  { id: 'mistakes', contexts: ['session'] },
  { id: 'spacing', contexts: ['dashboard'] },
  { id: 'trust-schedule', contexts: ['dashboard'] },
  { id: 'consistency', contexts: ['dashboard'] },
  { id: 'sleep', contexts: ['dashboard'] },
  { id: 'interleave' },
  { id: 'elaborate' },
  { id: 'in-context' },
]

const TIP_BY_ID = new Set(TIPS.map((t) => t.id))
export const TIP_COUNT = TIPS.length

/** Have all tips been seen? (Then the seen-list can reset and cycle again.) */
export function allTipsSeen(seenTipIds: string[]): boolean {
  const seen = new Set(seenTipIds.filter((id) => TIP_BY_ID.has(id)))
  return seen.size >= TIPS.length
}

// About once a day: a learner who opens the app several times gets at most one
// tip, and a daily user sees a steady, unhurried drip.
export const TIP_THROTTLE_MS = 20 * 60 * 60 * 1000

export interface PickTipState {
  enabled: boolean
  seenTipIds: string[]
  lastTipShownAt: number
  now: number
  context?: TipContext
  /** Injectable for tests; defaults to Math.random. */
  rand?: () => number
}

/**
 * Choose a tip to show, or null. Null when tips are off, when one was shown too
 * recently (throttle), or — rarely — when nothing fits. Prefers unseen tips,
 * then tips that fit the current context; falls back to the full set once the
 * learner has seen them all.
 */
export function pickTip(s: PickTipState): Tip | null {
  if (!s.enabled) return null
  if (s.now - s.lastTipShownAt < TIP_THROTTLE_MS) return null

  const seen = new Set(s.seenTipIds)
  let pool = TIPS.filter((t) => !seen.has(t.id))
  if (pool.length === 0) pool = TIPS // all seen — allow a fresh cycle

  if (s.context) {
    const fitting = pool.filter((t) => t.contexts?.includes(s.context!))
    if (fitting.length) pool = fitting
  }
  if (pool.length === 0) return null

  const r = s.rand ? s.rand() : Math.random()
  return pool[Math.min(pool.length - 1, Math.floor(r * pool.length))]
}
