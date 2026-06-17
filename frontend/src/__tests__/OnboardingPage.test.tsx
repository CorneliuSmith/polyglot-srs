import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import OnboardingPage from '../features/onboarding/OnboardingPage'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (orig) => ({
  ...(await orig<typeof import('react-router-dom')>()),
  useNavigate: () => mockNavigate,
}))
vi.mock('../api/profile', () => ({ getLanguages: vi.fn() }))
vi.mock('../api/onboarding', () => ({
  getOnboardingStatus: vi.fn(),
  getPlacement: vi.fn(),
  scorePlacement: vi.fn(),
  completeOnboarding: vi.fn(),
}))
const mockSetActive = vi.fn()
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn(() => mockSetActive),
}))

import { getLanguages } from '../api/profile'
import {
  getOnboardingStatus,
  getPlacement,
  scorePlacement,
  completeOnboarding,
} from '../api/onboarding'

const mockGetLanguages = getLanguages as ReturnType<typeof vi.fn>
const mockStatus = getOnboardingStatus as ReturnType<typeof vi.fn>
const mockGetPlacement = getPlacement as ReturnType<typeof vi.fn>
const mockScore = scorePlacement as ReturnType<typeof vi.fn>
const mockComplete = completeOnboarding as ReturnType<typeof vi.fn>

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <OnboardingPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('OnboardingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetLanguages.mockResolvedValue([{ id: 'lang-es', code: 'es', name: 'Spanish', rtl: false }])
    mockStatus.mockResolvedValue({ onboarded: false, active_language_id: null, has_subscriptions: false })
    mockComplete.mockResolvedValue({ subscribed: 4, active_language_id: 'lang-es', level: 'A1' })
  })

  it('beginner path: pick language → "I\'m new" → start learning at A1', async () => {
    renderPage()

    fireEvent.click(await screen.findByRole('button', { name: 'Spanish' }))
    fireEvent.click(await screen.findByRole('button', { name: /i'm new to it/i }))
    fireEvent.click(await screen.findByRole('button', { name: /start learning/i }))

    await waitFor(() => {
      expect(mockComplete).toHaveBeenCalledWith({ languageId: 'lang-es', level: 'A1' })
    })
    expect(mockSetActive).toHaveBeenCalledWith('lang-es')
    expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true })
  })

  it('placement path: estimated level flows into completion', async () => {
    mockGetPlacement.mockResolvedValue({
      available: true,
      items: [
        { id: 'i1', level: 'A1', prompt: 'hello' },
        { id: 'i2', level: 'B1', prompt: 'house' },
      ],
    })
    mockScore.mockResolvedValue({ estimated_level: 'B1', per_level: {} })

    renderPage()

    fireEvent.click(await screen.findByRole('button', { name: 'Spanish' }))
    fireEvent.click(await screen.findByRole('button', { name: /take a quick placement/i }))

    // Items render as labelled inputs; answer them.
    const helloInput = await screen.findByLabelText('hello')
    fireEvent.change(helloInput, { target: { value: 'hola' } })
    fireEvent.click(screen.getByRole('button', { name: /see my level/i }))

    // The estimated level is preselected on the confirm step.
    const select = (await screen.findByLabelText('Starting level')) as HTMLSelectElement
    await waitFor(() => expect(select.value).toBe('B1'))

    fireEvent.click(screen.getByRole('button', { name: /start learning/i }))
    await waitFor(() => {
      expect(mockComplete).toHaveBeenCalledWith({ languageId: 'lang-es', level: 'B1' })
    })
  })

  it('redirects away if already onboarded', async () => {
    mockStatus.mockResolvedValue({ onboarded: true, active_language_id: 'lang-es', has_subscriptions: true })
    renderPage()
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true })
    })
  })
})
