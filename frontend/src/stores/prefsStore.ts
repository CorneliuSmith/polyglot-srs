import { create } from 'zustand'
import { persist } from 'zustand/middleware'

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
  // the next session, instead of resetting to hidden every card.
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
      hintLevel: 0,
      setHintLevel: (level) => set({ hintLevel: level }),
      qwertyTranslit: {},
      setQwertyTranslit: (code, on) =>
        set((s) => ({ qwertyTranslit: { ...s.qwertyTranslit, [code]: on } })),
      listeningMode: false,
      setListeningMode: (on) => set({ listeningMode: on }),
      accentsOptional: false,
      setAccentsOptional: (on) => set({ accentsOptional: on }),
    }),
    {
      name: 'polyglot-prefs',
    },
  ),
)
