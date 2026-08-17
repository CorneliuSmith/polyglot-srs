import { create } from 'zustand'
import type { Reading } from '../api/reader'

/**
 * The reading being written right now — owned by the STORE, not by the
 * page that started it.
 *
 * Generating a text got slower on purpose (#285: every text is graded
 * against its contract and regenerated once if it misses), so the learner
 * is invited to go play a word game or run their reviews while they wait.
 * That means leaving /read — and a `useMutation` owned by ReaderPage dies
 * with the component, dropping the finished text on the floor.
 *
 * Module state outlives route changes, so the promise lives here and the
 * page is a subscriber. If the learner closes the app entirely the text is
 * still not lost: /api/reader/generate saves it before it responds, so it
 * appears in "My readings" — only the notification goes missing.
 */

export interface PendingJob {
  topic: string
  languageId: string
  languageCode: string
  startedAt: number
}

export interface ReadyReading {
  id: string
  reading: Omit<Reading, 'id' | 'topic'>
  topic: string
  level: string
}

interface PendingReadingState {
  pending: PendingJob | null
  ready: ReadyReading | null
  error: boolean
  /** Track a generation already in flight. The promise is awaited HERE, so
   * unmounting the page that started it changes nothing. */
  start: (
    job: PendingJob,
    promise: Promise<{
      id: string
      reading: Omit<Reading, 'id' | 'topic'>
      level: string
    }>,
  ) => void
  /** Take the finished reading and clear the slot — whoever renders it
   * owns it from then on. */
  claim: () => ReadyReading | null
  /** Drop a finished-or-failed job without rendering it (banner dismiss). */
  clear: () => void
}

export const usePendingReadingStore = create<PendingReadingState>(
  (set, get) => ({
    pending: null,
    ready: null,
    error: false,

    start: (job, promise) => {
      set({ pending: job, ready: null, error: false })
      promise
        .then((res) => {
          // A newer job replaced this one while it was in flight: its
          // result is stale, and announcing it would open a text the
          // learner has already moved on from.
          if (get().pending !== job) return
          set({
            pending: null,
            ready: {
              id: res.id,
              reading: res.reading,
              topic: job.topic,
              level: res.level,
            },
          })
        })
        .catch(() => {
          if (get().pending !== job) return
          set({ pending: null, error: true })
        })
    },

    claim: () => {
      const ready = get().ready
      if (ready) set({ ready: null, error: false })
      return ready
    },

    clear: () => set({ ready: null, error: false }),
  }),
)
