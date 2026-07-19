import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import TranslationReviewsPanel from '../features/contribute/TranslationReviewsPanel'

vi.mock('../api/contribute', () => ({
  getTranslationReviews: vi.fn(),
  approveTranslationReview: vi.fn(),
  rejectTranslationReview: vi.fn(),
}))
import {
  approveTranslationReview,
  getTranslationReviews,
} from '../api/contribute'
const mockGet = getTranslationReviews as ReturnType<typeof vi.fn>
const mockApprove = approveTranslationReview as ReturnType<typeof vi.fn>

function renderPanel() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <TranslationReviewsPanel />
    </QueryClientProvider>,
  )
}

describe('TranslationReviewsPanel', () => {
  beforeEach(() => vi.clearAllMocks())

  it('lists queued items and approves one', async () => {
    mockGet.mockResolvedValue([
      { id: 'r1', locale: 'nl', word: 'cat', proposed: 'kat',
        reason: 'checker unsure', current_definition: 'small feline',
        created_at: null },
    ])
    mockApprove.mockResolvedValue(undefined)
    renderPanel()
    await waitFor(() => expect(screen.getByTestId('translation-reviews')).toBeDefined())
    expect(screen.getByText('cat')).toBeDefined()
    expect(screen.getByText('kat')).toBeDefined()
    expect(screen.getByText('checker unsure')).toBeDefined()
    fireEvent.click(screen.getByText('Approve'))
    await waitFor(() => expect(mockApprove.mock.calls[0]?.[0]).toBe('r1'))
  })

  it('renders nothing when the queue is empty', async () => {
    mockGet.mockResolvedValue([])
    const { container } = renderPanel()
    await waitFor(() => expect(mockGet).toHaveBeenCalled())
    expect(container.querySelector('[data-testid="translation-reviews"]')).toBeNull()
  })
})
