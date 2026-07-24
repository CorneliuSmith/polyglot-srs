import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import ReviewQueue from '../features/contribute/ReviewQueue'

vi.mock('../api/contribute', () => ({
  getSuggestions: vi.fn(),
  getReviewNotes: vi.fn(),
  getFeedback: vi.fn(),
  // Referenced by the child panels' imports.
  approveSuggestion: vi.fn(),
  rejectSuggestion: vi.fn(),
  resolveReviewNote: vi.fn(),
  resolveFeedback: vi.fn(),
}))

import { getSuggestions, getReviewNotes, getFeedback } from '../api/contribute'
const mockSuggestions = getSuggestions as ReturnType<typeof vi.fn>
const mockNotes = getReviewNotes as ReturnType<typeof vi.fn>
const mockFeedback = getFeedback as ReturnType<typeof vi.fn>

function renderQueue(canReview = true) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ReviewQueue languageId="lang-1" canReview={canReview} />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ReviewQueue', () => {
  beforeEach(() => vi.clearAllMocks())

  it('tells the reviewer the queue is empty when nothing is pending', async () => {
    mockSuggestions.mockResolvedValue([])
    mockNotes.mockResolvedValue([])
    mockFeedback.mockResolvedValue([])
    renderQueue()
    expect(await screen.findByTestId('review-queue-empty')).toBeDefined()
    expect(screen.getByText(/no reviews in the queue/i)).toBeDefined()
  })

  it('does NOT show the empty state when something is pending', async () => {
    mockSuggestions.mockResolvedValue([])
    mockNotes.mockResolvedValue([
      { id: 'n1', note: 'Typo here', card_label: 'x', created_at: '2026-01-01' },
    ])
    mockFeedback.mockResolvedValue([])
    renderQueue()
    // Give the queries a tick to settle, then assert the empty state stays away.
    await waitFor(() => expect(mockNotes).toHaveBeenCalled())
    await new Promise((r) => setTimeout(r, 0))
    expect(screen.queryByTestId('review-queue-empty')).toBeNull()
  })
})
