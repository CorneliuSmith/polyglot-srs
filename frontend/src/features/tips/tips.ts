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
  title: string
  body: string
  /** Where this tip lands best. Used to gently prefer a fitting tip; a tip
   *  with no contexts can appear anywhere. */
  contexts?: TipContext[]
}

export const TIPS: Tip[] = [
  {
    id: 'read-aloud',
    title: 'Say it out loud',
    body:
      'If you can, whisper or speak each sentence as you answer. Producing a word aloud makes it far stickier than reading it silently — it’s one of the simplest wins in learning.',
    contexts: ['session'],
  },
  {
    id: 'retrieval',
    title: 'The struggle to recall is the point',
    body:
      'Pulling an answer from memory — even when you get it wrong — strengthens it more than re-reading ever could. That effort right before the reveal is where the learning happens.',
    contexts: ['session'],
  },
  {
    id: 'shadow',
    title: 'Shadow the audio',
    body:
      'Play a sentence and repeat it straight back, copying the rhythm and melody. It trains your ear and your mouth at the same time.',
    contexts: ['session'],
  },
  {
    id: 'generation',
    title: 'Type it, don’t just recognise it',
    body:
      'Producing the answer yourself beats picking it from a list — that’s why the drills ask you to write it. The little bit of extra effort pays off in recall.',
    contexts: ['session'],
  },
  {
    id: 'mistakes',
    title: 'Wrong answers are data, not failure',
    body:
      'Every miss tells the app exactly what to bring back sooner. Getting things wrong and correcting them is how the schedule tunes itself to you.',
    contexts: ['session'],
  },
  {
    id: 'spacing',
    title: 'Short and often beats marathons',
    body:
      'Ten focused minutes a day teaches you more than a two-hour weekend cram. Spacing your practice out is one of the most reliable findings in all of learning science.',
    contexts: ['dashboard'],
  },
  {
    id: 'trust-schedule',
    title: 'Trust the schedule',
    body:
      'Reviews come back just as you’re about to forget them. Returning right at that edge is what moves a word into long-term memory — so a quiet day of few reviews is the system working.',
    contexts: ['dashboard'],
  },
  {
    id: 'consistency',
    title: 'A streak beats a burst',
    body:
      'Showing up daily, even briefly, keeps everything warm. Missed a day? Just pick back up — one lapse doesn’t undo your progress.',
    contexts: ['dashboard'],
  },
  {
    id: 'sleep',
    title: 'Sleep on it',
    body:
      'Memory consolidates while you sleep. A short session in the evening, reviewed again the next morning, sticks better than the same minutes crammed back to back.',
    contexts: ['dashboard'],
  },
  {
    id: 'interleave',
    title: 'Mix it up',
    body:
      'Jumping between tenses and topics — the way the Gym does — feels harder than drilling one thing, but it builds more flexible, longer-lasting knowledge.',
  },
  {
    id: 'elaborate',
    title: 'Make it mean something',
    body:
      'Tie a new word to an image, a little story, or a word you already know. The more hooks you give a word, the easier it is to find later.',
  },
  {
    id: 'in-context',
    title: 'Learn words inside sentences',
    body:
      'A word met in a real sentence brings its grammar and its usual company along with it — far more useful than a bare translation on its own.',
  },
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
