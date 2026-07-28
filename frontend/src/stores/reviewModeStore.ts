import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface ReviewModeState {
  /**
   * Staff "Review Mode": while on, selecting text anywhere in the app offers
   * to flag it. Persisted because a reviewer works in sessions — they turn it
   * on, go through thirty cards, and should not have to re-arm it on every
   * navigation or reload.
   *
   * Purely a UI affordance. It reveals no content and grants no permission:
   * the flag endpoint re-checks the caller's role for the language server-side,
   * so a non-staff account flipping this in devtools gains nothing.
   */
  reviewMode: boolean
  setReviewMode: (on: boolean) => void
}

export const useReviewModeStore = create<ReviewModeState>()(
  persist(
    (set) => ({
      reviewMode: false,
      setReviewMode: (on) => set({ reviewMode: on }),
    }),
    { name: 'polyglot-review-mode' },
  ),
)
