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
vi.mock('../api/billing', async (orig) => ({
  ...(await orig<typeof import('../api/billing')>()),
  getPlanPrices: vi.fn(() => Promise.resolve({ single: null, all: null })),
}))
vi.mock('../api/onboarding', () => ({
  getOnboardingStatus: vi.fn(),
  placementNext: vi.fn(),
  completeOnboarding: vi.fn(),
}))
const mockSetActive = vi.fn()
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn(() => mockSetActive),
}))

import { getLanguages } from '../api/profile'
import {
  getOnboardingStatus,
  placementNext,
  completeOnboarding,
} from '../api/onboarding'

const mockGetLanguages = getLanguages as ReturnType<typeof vi.fn>
const mockStatus = getOnboardingStatus as ReturnType<typeof vi.fn>
const mockNext = placementNext as ReturnType<typeof vi.fn>
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
    fireEvent.click(await screen.findByRole('button', { name: /brand new/i }))
    fireEvent.click(await screen.findByRole('button', { name: /continue/i }))
    fireEvent.click(await screen.findByRole('button', { name: /start learning/i }))

    await waitFor(() => {
      expect(mockComplete).toHaveBeenCalledWith({
        languageId: 'lang-es', level: 'A1', planScope: 'single',
      })
    })
    expect(mockSetActive).toHaveBeenCalledWith('lang-es')
    expect(mockNavigate).toHaveBeenCalledWith('/welcome', { replace: true })
  })

  it('adaptive placement: one item at a time, estimate flows into completion', async () => {
    const item1 = { id: 'i1', kind: 'grammar', level: 'A2',
                    prompt: 'la ____ roja', translation: 'the red house' }
    const item2 = { id: 'i2', kind: 'vocabulary', level: 'B1',
                    prompt: 'hello', translation: null }
    mockNext
      .mockResolvedValueOnce({ available: true, done: false, item: item1,
                               asked: 0, max_items: 12 })
      .mockResolvedValueOnce({ available: true, done: false, item: item2,
                               asked: 1, max_items: 12 })
      .mockResolvedValueOnce({ available: true, done: true,
                               estimated_level: 'B1', per_level: {}, asked: 2 })

    renderPage()

    fireEvent.click(await screen.findByRole('button', { name: 'Spanish' }))
    fireEvent.click(await screen.findByRole('button', { name: /test my level/i }))

    // First item appears alone; answering it fetches the next.
    const first = await screen.findByLabelText('la ____ roja')
    fireEvent.change(first, { target: { value: 'casa' } })
    fireEvent.click(screen.getByRole('button', { name: /^next$/i }))

    // Second item; "I don't know" submits it blank (counts as wrong server-side).
    await screen.findByLabelText('hello')
    fireEvent.click(screen.getByRole('button', { name: /i don't know/i }))

    // Server says done — the estimate is preselected on the confirm step.
    const select = (await screen.findByLabelText('Starting level')) as HTMLSelectElement
    await waitFor(() => expect(select.value).toBe('B1'))
    expect(mockNext).toHaveBeenLastCalledWith('lang-es', [
      { id: 'i1', input: 'casa' },
      { id: 'i2', input: '' },
    ])

    fireEvent.click(screen.getByRole('button', { name: /continue/i }))
    fireEvent.click(await screen.findByRole('button', { name: /all languages/i }))
    fireEvent.click(screen.getByRole('button', { name: /start learning/i }))
    await waitFor(() => {
      expect(mockComplete).toHaveBeenCalledWith({
        languageId: 'lang-es', level: 'B1', planScope: 'all',
      })
    })
  })

  it('falls back to self-report when placement is unavailable', async () => {
    mockNext.mockResolvedValue({ available: false, done: true,
                                 estimated_level: null, per_level: {}, asked: 0 })
    renderPage()

    fireEvent.click(await screen.findByRole('button', { name: 'Spanish' }))
    fireEvent.click(await screen.findByRole('button', { name: /test my level/i }))

    const select = (await screen.findByLabelText('Starting level')) as HTMLSelectElement
    expect(select.value).toBe('A1')
  })

  it('self-pick path: "I know some" goes straight to the level chooser, no test', async () => {
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: 'Spanish' }))
    fireEvent.click(await screen.findByRole('button', { name: /i know some/i }))
    // Lands on the level chooser without ever calling the placement endpoint.
    expect(await screen.findByLabelText('Starting level')).toBeDefined()
    expect(mockNext).not.toHaveBeenCalled()
  })

  it('placement is escapable: "Skip the test" drops to the level chooser', async () => {
    mockNext.mockResolvedValueOnce({
      available: true, done: false,
      item: { id: 'i1', kind: 'vocabulary', level: 'A1', prompt: 'hola', translation: null },
      asked: 0, max_items: 12,
    })
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: 'Spanish' }))
    fireEvent.click(await screen.findByRole('button', { name: /test my level/i }))
    await screen.findByLabelText('hola')
    fireEvent.click(screen.getByRole('button', { name: /skip the test/i }))
    expect(await screen.findByLabelText('Starting level')).toBeDefined()
  })

  it('the back button returns to the previous step', async () => {
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: 'Spanish' }))
    // On the method step now; go back to language selection.
    await screen.findByRole('button', { name: /brand new/i })
    fireEvent.click(screen.getByRole('button', { name: /^back$/i }))
    expect(await screen.findByText(/which language do you want to learn/i)).toBeDefined()
  })

  it('redirects away if already onboarded', async () => {
    mockStatus.mockResolvedValue({ onboarded: true, active_language_id: 'lang-es', has_subscriptions: true })
    renderPage()
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true })
    })
  })
})
