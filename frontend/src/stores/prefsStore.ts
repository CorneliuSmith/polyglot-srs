import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface PrefsState {
  activeLanguageId: string | null
  setActiveLanguageId: (id: string) => void
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
}

export const usePrefsStore = create<PrefsState>()(
  persist(
    (set) => ({
      activeLanguageId: null,
      setActiveLanguageId: (id) => set({ activeLanguageId: id }),
      hintLevel: 0,
      setHintLevel: (level) => set({ hintLevel: level }),
      qwertyTranslit: {},
      setQwertyTranslit: (code, on) =>
        set((s) => ({ qwertyTranslit: { ...s.qwertyTranslit, [code]: on } })),
    }),
    {
      name: 'polyglot-prefs',
    },
  ),
)
