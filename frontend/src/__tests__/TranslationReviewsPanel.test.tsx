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

function renderPanel(languageId?: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <TranslationReviewsPanel languageId={languageId} />
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

  it('is scoped to the working language and badged with the review type', async () => {
    /* Owner: these belong in the Review section, marked as AI generated —
     * so the panel fetches ONE language's queue and names its type. */
    mockGet.mockResolvedValue([
      { id: 'r1', locale: 'ar', word: 'crees', proposed: null,
        reason: 'mismatch in sense', current_definition: 'subjunctive of crear',
        created_at: null },
    ])
    renderPanel('lang-es')
    await waitFor(() =>
      expect(screen.getByTestId('translation-reviews')).toBeDefined())
    expect(mockGet).toHaveBeenCalledWith('lang-es')
    expect(screen.getByText('AI generated · awaiting review')).toBeDefined()
  })

  it('renders nothing when the queue is empty', async () => {
    mockGet.mockResolvedValue([])
    const { container } = renderPanel()
    await waitFor(() => expect(mockGet).toHaveBeenCalled())
    expect(container.querySelector('[data-testid="translation-reviews"]')).toBeNull()
  })
})

describe('TranslationReviewsPanel — reviewability', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows current and proposed as a pair, so the choice is legible', async () => {
    mockGet.mockResolvedValue([
      { id: 'r1', locale: 'ar', word: 'crees', proposed: 'تظن',
        reason: 'sense mismatch',
        current_definition: 'second-person singular present subjunctive of crear',
        created_at: null },
    ])
    renderPanel()
    const row = await screen.findByTestId('translation-reviews')
    expect(row.textContent).toContain('now:')
    expect(row.textContent).toContain('proposed:')
    expect(row.textContent).toContain('تظن')
    // Approve is live when there IS something to apply.
    expect(screen.getByRole('button', { name: 'Approve' })).not.toBeDisabled()
  })

  it('a row with no proposal offers exactly one action: Dismiss', async () => {
    // A disabled Approve next to Reject read as "the only thing I can do is
    // reject", with no hint what rejecting did (owner: "What will happen
    // when I reject… which I only have the option to reject"). There IS one
    // action on such a row — clear it, card untouched — so show one button
    // named for what it does.
    mockGet.mockResolvedValue([
      { id: 'r2', locale: 'ar', word: 'mis', proposed: '',
        reason: 'no accurate single-word gloss',
        current_definition: 'plural of mi', created_at: null },
    ])
    const { rejectTranslationReview } = await import('../api/contribute')
    const mockReject = rejectTranslationReview as ReturnType<typeof vi.fn>
    mockReject.mockResolvedValue(undefined)
    renderPanel()
    const row = await screen.findByTestId('translation-reviews')
    expect(row.textContent).toMatch(/no replacement proposed/i)
    expect(screen.queryByRole('button', { name: 'Approve' })).toBeNull()
    const dismiss = screen.getByRole('button', { name: 'Dismiss' })
    fireEvent.click(dismiss)
    await waitFor(() => expect(mockReject.mock.calls[0]?.[0]).toBe('r2'))
  })
})
