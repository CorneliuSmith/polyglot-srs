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
}

export const usePrefsStore = create<PrefsState>()(
  persist(
    (set) => ({
      activeLanguageId: null,
      setActiveLanguageId: (id) => set({ activeLanguageId: id }),
      hintLevel: 0,
      setHintLevel: (level) => set({ hintLevel: level }),
    }),
    {
      name: 'polyglot-prefs',
    },
  ),
)
