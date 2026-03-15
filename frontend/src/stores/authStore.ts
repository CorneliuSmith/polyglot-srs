import { create } from 'zustand'
import type { Session } from '@supabase/supabase-js'

interface AuthState {
  session: Session | null
  loading: boolean
  setSession: (session: Session | null) => void
  setLoading: (loading: boolean) => void
  isAuthenticated: () => boolean
}

export const useAuthStore = create<AuthState>((set, get) => ({
  session: null,
  loading: true,
  setSession: (session) => set({ session }),
  setLoading: (loading) => set({ loading }),
  isAuthenticated: () => get().session !== null,
}))
