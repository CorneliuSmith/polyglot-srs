import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { ViewAsLevel } from '../lib/viewAs'

interface ViewAsState {
  /** null = my real access. Only meaningful for accounts that ARE admins;
   * the bar that sets it renders for nobody else, and the value is
   * presentation-only either way (see lib/viewAs.ts). */
  viewAs: ViewAsLevel | null
  setViewAs: (level: ViewAsLevel | null) => void
}

export const useViewAsStore = create<ViewAsState>()(
  persist(
    (set) => ({
      viewAs: null,
      setViewAs: (viewAs) => set({ viewAs }),
    }),
    { name: 'polyglot-view-as' },
  ),
)
