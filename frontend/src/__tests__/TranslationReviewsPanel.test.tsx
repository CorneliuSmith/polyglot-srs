import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import TranslationReviewsPanel from '../features/contribute/TranslationReviewsPanel'

vi.mock('../api/contribute', () => ({
  getTranslationReviews: vi.fn(),
  approveTranslationReview: vi.fn(),
  rejectTranslationReview: vi.fn(),
  approveTranslationReviewItem: vi.fn(),
  rejectTranslationReviewItem: vi.fn(),
  // The rows carry their card now, and the card can be corrected here.
  editReviewedCard: vi.fn(),
}))
import {
  approveTranslationReview,
  approveTranslationReviewItem,
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
    mockGet.mockResolvedValue({ reviews: [
      { id: 'r1', locale: 'nl', word: 'cat', proposed: 'kat',
        reason: 'checker unsure', current_definition: 'small feline',
        created_at: null },
    ], items: [] })
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
    mockGet.mockResolvedValue({ reviews: [
      { id: 'r1', locale: 'ar', word: 'crees', proposed: null,
        reason: 'mismatch in sense', current_definition: 'subjunctive of crear',
        created_at: null },
    ], items: [] })
    renderPanel('lang-es')
    await waitFor(() =>
      expect(screen.getByTestId('translation-reviews')).toBeDefined())
    expect(mockGet).toHaveBeenCalledWith('lang-es')
    expect(screen.getByText('AI generated · awaiting review')).toBeDefined()
  })

  it('renders nothing when the queue is empty', async () => {
    mockGet.mockResolvedValue({ reviews: [], items: [] })
    const { container } = renderPanel()
    await waitFor(() => expect(mockGet).toHaveBeenCalled())
    expect(container.querySelector('[data-testid="translation-reviews"]')).toBeNull()
  })
})

describe('TranslationReviewsPanel — reviewability', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows current and proposed as a pair, so the choice is legible', async () => {
    mockGet.mockResolvedValue({ reviews: [
      { id: 'r1', locale: 'ar', word: 'crees', proposed: 'تظن',
        reason: 'sense mismatch',
        current_definition: 'second-person singular present subjunctive of crear',
        created_at: null },
    ], items: [] })
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
    mockGet.mockResolvedValue({ reviews: [
      { id: 'r2', locale: 'ar', word: 'mis', proposed: '',
        reason: 'no accurate single-word gloss',
        current_definition: 'plural of mi', created_at: null },
    ], items: [] })
    const { rejectTranslationReview } = await import('../api/contribute')
    const mockReject = rejectTranslationReview as ReturnType<typeof vi.fn>
    mockReject.mockResolvedValue(undefined)
    renderPanel()
    const row = await screen.findByTestId('translation-reviews')
    // And it says WHY it has one: the owner read the missing button as a
    // bug ("on some i only get the option to dismiss and not understand
    // why"), because the old copy described the cause and left the
    // consequence to be inferred.
    expect(row.textContent).toMatch(/nothing to approve/i)
    expect(screen.getByTestId('no-proposal-r2').textContent).toMatch(
      /dismiss is the only action/i,
    )
    expect(screen.queryByRole('button', { name: 'Approve' })).toBeNull()
    const dismiss = screen.getByRole('button', { name: 'Dismiss' })
    fireEvent.click(dismiss)
    await waitFor(() => expect(mockReject.mock.calls[0]?.[0]).toBe('r2'))
  })
  it('carries the word itself, so a dead-end row has a way out', async () => {
    // A row with nothing to approve hands the reviewer a problem and, until
    // now, no means to fix it: the checker's objection is usually to the
    // ENGLISH definition, which every locale is translated from.
    mockGet.mockResolvedValue({ reviews: [
      { id: 'r3', locale: 'ar', word: 'nuestras', proposed: null,
        reason: 'no accurate single-word Arabic gloss',
        current_definition: 'feminine plural of nuestro', created_at: null,
        target_type: 'vocabulary', target_id: 'v9',
        card: { sentence: 'nuestras', answer: null, hint: null,
                translation: 'feminine plural of nuestro',
                context: 'det', level: 'A1' } },
    ], items: [] })
    renderPanel()
    await screen.findByTestId('translation-reviews')
    expect(screen.getByTestId('translation-card-r3')).toBeDefined()
    fireEvent.click(screen.getByTestId('translation-card-r3-edit'))
    expect(screen.getByLabelText('Definition (English)')).toBeDefined()
  })
})

describe('TranslationReviewsPanel — the other layers', () => {
  beforeEach(() => vi.clearAllMocks())

  it('lists non-vocabulary rejects grouped by kind and approves through the item endpoint', async () => {
    // Until 3 Sep 2026 only glosses had a queue: a rejected drill line,
    // explanation, grammar title or example meaning was simply not
    // written and waited for the retry backoff where nobody could see it.
    mockGet.mockResolvedValue({
      reviews: [
        { id: 'r1', locale: 'fr', word: 'cat', proposed: 'chat',
          reason: 'unsure', current_definition: 'small feline', created_at: null },
      ],
      items: [
        { id: 'i1', kind: 'drill', field: 'hint', locale: 'fr',
          label: 'Yo {{answer}} un libro.', source_text: 'a verb',
          proposed: 'un verbe', reason: 'gate: answer leak', created_at: null,
          target_type: 'drill', target_id: 'd1' },
        { id: 'i2', kind: 'grammar_meta', field: 'title', locale: 'fr',
          label: 'Present tense', source_text: 'Present tense',
          proposed: null, reason: 'no verdict', created_at: null,
          target_type: 'grammar_point', target_id: 'g1' },
      ],
    })
    const mockApproveItem = approveTranslationReviewItem as ReturnType<typeof vi.fn>
    mockApproveItem.mockResolvedValue(undefined)
    renderPanel('lang-es')
    await screen.findByTestId('translation-reviews')
    // One section per layer, in a fixed order, each counting its rows.
    const sections = screen.getAllByTestId(/^translation-kind-/)
    expect(sections.map((s) => s.getAttribute('data-testid'))).toEqual([
      'translation-kind-vocabulary', 'translation-kind-drill',
      'translation-kind-grammar_meta',
    ])
    const drills = screen.getByTestId('translation-kind-drill')
    expect(drills.textContent).toContain('Drill lines and hints')
    expect(drills.textContent).toContain('Yo {{answer}} un libro.')
    // The English being rendered sits next to the proposal, with the field
    // named — a drill has two texts and the reviewer must know which.
    expect(drills.textContent).toContain('English:')
    expect(drills.textContent).toContain('a verb')
    expect(drills.textContent).toContain('un verbe')
    expect(drills.textContent).toMatch(/hint/i)
    // A row with nothing to approve says so, same as a gloss would.
    expect(screen.getByTestId('no-proposal-i2').textContent).toMatch(
      /dismiss is the only action/i,
    )
    // Approving an item hits the item endpoint, not the gloss one.
    const [approveDrill] = within(drills).getAllByRole('button', { name: 'Approve' })
    fireEvent.click(approveDrill)
    await waitFor(() => expect(mockApproveItem.mock.calls[0]?.[0]).toBe('i1'))
    expect(mockApprove).not.toHaveBeenCalled()
  })

  it('reads a server without the item queue as an empty item list', async () => {
    // The API helper fills `items` in; the panel must not care whether the
    // owner has applied the migration yet.
    mockGet.mockResolvedValue({
      reviews: [
        { id: 'r1', locale: 'nl', word: 'cat', proposed: 'kat',
          reason: 'unsure', current_definition: 'small feline', created_at: null },
      ],
      items: [],
    })
    renderPanel()
    await screen.findByTestId('translation-reviews')
    expect(screen.queryByTestId(/^translation-kind-(drill|explanation)/)).toBeNull()
  })
})
