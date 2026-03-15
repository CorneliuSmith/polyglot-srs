import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface PrefsState {
  activeLanguageId: string | null
  setActiveLanguageId: (id: string) => void
}

export const usePrefsStore = create<PrefsState>()(
  persist(
    (set) => ({
      activeLanguageId: null,
      setActiveLanguageId: (id) => set({ activeLanguageId: id }),
    }),
    {
      name: 'polyglot-prefs',
    },
  ),
)
