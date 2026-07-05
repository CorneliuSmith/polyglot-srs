import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import SettingsPage from '../features/settings/SettingsPage'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (orig) => ({
  ...(await orig<typeof import('react-router-dom')>()),
  useNavigate: () => mockNavigate,
}))
vi.mock('../api/profile', () => ({
  getProfile: vi.fn(),
  updateProfile: vi.fn(),
  getLanguages: vi.fn(() => Promise.resolve([])),
}))
vi.mock('../api/dashboard', () => ({ getDashboardStats: vi.fn() }))
vi.mock('../stores/prefsStore', () => ({ usePrefsStore: vi.fn(() => 'lang-es') }))
const { signOut } = vi.hoisted(() => ({
  signOut: vi.fn(() => Promise.resolve({ error: null })),
}))
vi.mock('../lib/supabase', () => ({ supabase: { auth: { signOut } } }))

import { getProfile, updateProfile } from '../api/profile'
import { getDashboardStats } from '../api/dashboard'

const mockGetProfile = getProfile as ReturnType<typeof vi.fn>
const mockUpdate = updateProfile as ReturnType<typeof vi.fn>
const mockStats = getDashboardStats as ReturnType<typeof vi.fn>

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetProfile.mockResolvedValue({
      id: 'u1', batch_size: 5, ui_language: 'en', active_language_id: 'lang-es',
      created_at: '', updated_at: '',
    })
    mockStats.mockResolvedValue({
      due_count: 4, streak_days: 3, cefr_progress: { A1: { learned: 12, total: 30 } },
    })
    mockUpdate.mockResolvedValue({})
  })

  it('shows progress from the analysis stats', async () => {
    renderPage()
    expect(await screen.findByText('12')).toBeDefined()  // cards learned (A1 learned)
    expect(screen.getByText('4')).toBeDefined()          // due now
    expect(screen.getByText('day streak')).toBeDefined()
  })

  it('changes the new-cards-per-session batch size', async () => {
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: '10' }))
    await waitFor(() => expect(mockUpdate).toHaveBeenCalledWith({ batch_size: 10 }))
  })

  it('signs out', async () => {
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: /sign out/i }))
    await waitFor(() => {
      expect(signOut).toHaveBeenCalled()
      expect(mockNavigate).toHaveBeenCalledWith('/login', { replace: true })
    })
  })
})
