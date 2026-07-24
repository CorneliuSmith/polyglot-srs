import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { allTipsSeen } from '../features/tips/tips'

export type Theme = 'system' | 'light' | 'dark'

interface PrefsState {
  activeLanguageId: string | null
  setActiveLanguageId: (id: string) => void
  // Theme switcher (WP13h): 'system' follows the OS. Applied by ThemeApplier
  // (and pre-applied by the inline script in index.html to avoid a flash).
  theme: Theme
  setTheme: (theme: Theme) => void
  // How many cards a review session pulls (the server clamps to 1–100).
  sessionSize: number
  setSessionSize: (n: number) => void
  // Hint disclosure level during reviews (0 = nothing revealed). Persisted:
  // the level the learner chose last time carries over to the next card and
  // the next session. Defaults to ALL layers revealed (beta report: a bare
  // "Tengo tres ___." is unanswerable — nobody found the hint dots); the
  // dots cycle back to fewer for learners who want the harder mode.
  hintLevel: number
  setHintLevel: (level: number) => void
  // QWERTY transliteration input per language code (ru/ar/el). Absent =
  // enabled — typing Latin and getting the target script is the baseline;
  // learners with a real native keyboard opt out.
  qwertyTranslit: Record<string, boolean>
  setQwertyTranslit: (code: string, on: boolean) => void
  // Listening mode (WP19a): cloze drills play the audio and hide the
  // sentence — the learner types the missing word by ear. Persisted like
  // hintLevel: the chosen mode carries across cards and sessions.
  listeningMode: boolean
  setListeningMode: (on: boolean) => void
  // Accents optional (beta request): when on, a diacritic-only miss
  // ("quien" for "quién") counts as fully correct instead of "Almost —
  // check the accents". Applied client-side by remapping correct_sloppy →
  // correct before it drives feedback and the SRS grade.
  accentsOptional: boolean
  setAccentsOptional: (on: boolean) => void
  // First-run feature tour. Undefined until the learner finishes or dismisses
  // it with "don't show again"; the dashboard auto-opens it once while unset.
  walkthroughDone: boolean
  setWalkthroughDone: (done: boolean) => void
  // "Install the app" banner (PWA): once dismissed, stays gone.
  installPromptDismissed: boolean
  setInstallPromptDismissed: (done: boolean) => void
  // Daily learn goal (beta request): the Learn tile shows progress toward a
  // small daily target instead of the whole queue count ("538 queued" was
  // overwhelming). 0 = no goal, show the full queue.
  dailyLearnGoal: number
  setDailyLearnGoal: (n: number) => void
  // What's-new entry ids the learner has already opened the panel over.
  // Drives the unseen-count badge on the dashboard.
  whatsNewSeen: string[]
  markWhatsNewSeen: (ids: string[]) => void
  // Learning tips (evidence-based study nudges). Default ON. seenTipIds avoids
  // repeats until the whole set has been seen (then it resets and cycles);
  // lastTipShownAt throttles them to ~once a day regardless of how often the
  // learner opens the app.
  learningTipsEnabled: boolean
  setLearningTipsEnabled: (on: boolean) => void
  seenTipIds: string[]
  lastTipShownAt: number
  recordTipShown: (id: string) => void
}

export const usePrefsStore = create<PrefsState>()(
  persist(
    (set) => ({
      activeLanguageId: null,
      setActiveLanguageId: (id) => set({ activeLanguageId: id }),
      theme: 'system' as Theme,
      setTheme: (theme) => set({ theme }),
      sessionSize: 20,
      setSessionSize: (n) => set({ sessionSize: n }),
      // 9 = "everything this card has" (clamped to the card's layer count).
      hintLevel: 9,
      setHintLevel: (level) => set({ hintLevel: level }),
      qwertyTranslit: {},
      setQwertyTranslit: (code, on) =>
        set((s) => ({ qwertyTranslit: { ...s.qwertyTranslit, [code]: on } })),
      listeningMode: false,
      setListeningMode: (on) => set({ listeningMode: on }),
      accentsOptional: false,
      setAccentsOptional: (on) => set({ accentsOptional: on }),
      walkthroughDone: false,
      setWalkthroughDone: (done) => set({ walkthroughDone: done }),
      installPromptDismissed: false,
      setInstallPromptDismissed: (done) => set({ installPromptDismissed: done }),
      dailyLearnGoal: 20,
      setDailyLearnGoal: (n) => set({ dailyLearnGoal: n }),
      whatsNewSeen: [],
      markWhatsNewSeen: (ids) =>
        set((s) => ({
          whatsNewSeen: Array.from(new Set([...s.whatsNewSeen, ...ids])),
        })),
      learningTipsEnabled: true,
      setLearningTipsEnabled: (on) => set({ learningTipsEnabled: on }),
      seenTipIds: [],
      lastTipShownAt: 0,
      recordTipShown: (id) =>
        set((s) => {
          const seen = s.seenTipIds.includes(id)
            ? s.seenTipIds
            : [...s.seenTipIds, id]
          // Once every tip has been seen, clear the list so the rotation starts
          // fresh instead of repeating at random forever.
          return {
            seenTipIds: allTipsSeen(seen) ? [] : seen,
            lastTipShownAt: Date.now(),
          }
        }),
    }),
    {
      name: 'polyglot-prefs',
      // v1: hints default ON. One-time bump for existing accounts whose
      // persisted level is the old hidden default — learners who prefer
      // the hard mode cycle the dots back to 0 once.
      version: 1,
      migrate: (persisted, version) => {
        const state = persisted as Partial<PrefsState>
        if (version < 1 && (state.hintLevel ?? 0) === 0) {
          state.hintLevel = 9
        }
        return state as PrefsState
      },
    },
  ),
)
