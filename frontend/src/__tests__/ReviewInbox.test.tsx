import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ReviewInbox from '../features/contribute/ReviewInbox'

vi.mock('../api/contribute', () => ({
  getReviewInbox: vi.fn(),
}))

import { getReviewInbox } from '../api/contribute'
const mockGet = getReviewInbox as ReturnType<typeof vi.fn>

const ZERO = {
  grammar_pending: 0, pending_drills: 0, pending_examples: 0,
  flagged_examples: 0, translation_suggestions: 0, ai_levels: 0,
  change_requests: 0, suggestions: 0, notes: 0, feedback: 0,
}

function renderInbox() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  render(
    <QueryClientProvider client={qc}>
      <ReviewInbox languageId="lang-1" />
    </QueryClientProvider>,
  )
}

describe('ReviewInbox', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows only the non-empty queues with their counts and a total', async () => {
    mockGet.mockResolvedValue({
      counts: { ...ZERO, flagged_examples: 3, change_requests: 2 },
      can_publish: true,
    })
    renderInbox()
    expect(await screen.findByTestId('review-inbox')).toBeDefined()
    expect(screen.getByText(/5 awaiting/)).toBeDefined()
    expect(screen.getByText('Flagged examples')).toBeDefined()
    expect(screen.getByText('Change requests')).toBeDefined()
    // Empty queues are not rendered.
    expect(screen.queryByText('Learner feedback')).toBeNull()
  })

  it('reads All clear when nothing is pending', async () => {
    mockGet.mockResolvedValue({ counts: ZERO, can_publish: false })
    renderInbox()
    expect(await screen.findByTestId('review-inbox')).toBeDefined()
    expect(screen.getByText(/All clear/)).toBeDefined()
  })
})
