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

/**
 * The preview level as a react-query cache-key segment.
 *
 * EVERY query whose response passes through downgradeRoles/downgradeFlags
 * must carry this, because the downgrade happens inside the queryFn: two
 * levels produce different data under one key, and react-query keeps serving
 * the OLD level's answer for the whole refetch. That is what made "view as
 * Contributor" show no Contribute tab while "view as Reviewer" showed all
 * three — the tab bar was rendering the level you looked at previously, not
 * the one you picked.
 *
 * Keying by level makes each preview its own cache entry: no stale window,
 * and switching back is instant instead of a refetch.
 */
export const useViewAsKey = (): string =>
  useViewAsStore((s) => s.viewAs) ?? 'real'
