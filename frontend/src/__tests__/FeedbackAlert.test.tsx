import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import FeedbackAlert from '../features/feedback/FeedbackAlert'
import { usePrefsStore } from '../stores/prefsStore'

vi.mock('../api/feedback', () => ({ getFeedbackSummary: vi.fn() }))

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => ({
  ...(await vi.importActual<typeof import('react-router-dom')>('react-router-dom')),
  useNavigate: () => mockNavigate,
}))

import { getFeedbackSummary } from '../api/feedback'
const mockSummary = getFeedbackSummary as ReturnType<typeof vi.fn>

function renderAlert(canSeeQueue = true) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <FeedbackAlert canSeeQueue={canSeeQueue} />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('the staff nudge when feedback arrives', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    usePrefsStore.setState({ feedbackSeenAt: null })
  })

  it('says how much is waiting', async () => {
    mockSummary.mockResolvedValue({
      open_count: 3,
      latest_at: '2026-08-01T10:00:00Z',
    })
    renderAlert()
    expect(await screen.findByTestId('feedback-alert')).toBeDefined()
    expect(screen.getByText(/3 pieces of feedback waiting/i)).toBeDefined()
  })

  it('takes you to the queue, and remembers you looked', async () => {
    // The whole point: the triage screen was three taps down inside
    // Settings → Admin, with nothing anywhere saying there was something in
    // it. A send button whose replies nobody reads is no send button.
    mockSummary.mockResolvedValue({
      open_count: 1,
      latest_at: '2026-08-01T10:00:00Z',
    })
    renderAlert()
    fireEvent.click(await screen.findByRole('button', { name: /read it/i }))

    expect(mockNavigate).toHaveBeenCalledWith('/feedback')
    expect(usePrefsStore.getState().feedbackSeenAt).toBe('2026-08-01T10:00:00Z')
  })

  it('stays quiet about a batch already dismissed', async () => {
    // An open-count alone would nag forever about items read and decided
    // against — the fastest way to teach someone to ignore the banner.
    usePrefsStore.setState({ feedbackSeenAt: '2026-08-01T10:00:00Z' })
    mockSummary.mockResolvedValue({
      open_count: 3,
      latest_at: '2026-08-01T10:00:00Z',
    })
    renderAlert()
    await waitFor(() => expect(mockSummary).toHaveBeenCalled())
    expect(screen.queryByTestId('feedback-alert')).toBeNull()
  })

  it('speaks up again when something NEWER lands', async () => {
    usePrefsStore.setState({ feedbackSeenAt: '2026-08-01T10:00:00Z' })
    mockSummary.mockResolvedValue({
      open_count: 4,
      latest_at: '2026-08-02T09:00:00Z',
    })
    renderAlert()
    expect(await screen.findByTestId('feedback-alert')).toBeDefined()
  })

  it('dismissing silences it without navigating', async () => {
    mockSummary.mockResolvedValue({
      open_count: 2,
      latest_at: '2026-08-01T10:00:00Z',
    })
    renderAlert()
    fireEvent.click(await screen.findByRole('button', { name: /dismiss/i }))

    expect(mockNavigate).not.toHaveBeenCalled()
    await waitFor(() =>
      expect(screen.queryByTestId('feedback-alert')).toBeNull(),
    )
  })

  it('shows nothing when the queue is empty', async () => {
    mockSummary.mockResolvedValue({ open_count: 0, latest_at: null })
    renderAlert()
    await waitFor(() => expect(mockSummary).toHaveBeenCalled())
    expect(screen.queryByTestId('feedback-alert')).toBeNull()
  })

  it('never asks a learner — the endpoint is staff-only', async () => {
    renderAlert(false)
    await waitFor(() => expect(mockSummary).not.toHaveBeenCalled())
    expect(screen.queryByTestId('feedback-alert')).toBeNull()
  })
})
