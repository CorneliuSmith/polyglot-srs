import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ReviewedCardView from '../features/contribute/ReviewedCardView'

vi.mock('../api/contribute', () => ({ editReviewedCard: vi.fn() }))
import { editReviewedCard } from '../api/contribute'
const mockEdit = editReviewedCard as ReturnType<typeof vi.fn>

const DRILL = {
  sentence: 'Casi no {{answer}} vino.',
  answer: 'queda',
  hint: 'almost none is left',
  translation: 'There is almost no wine left.',
  context: 'Present tense',
  level: 'A2',
}

const WORD = {
  sentence: 'pequeña',
  answer: null,
  hint: 'peh-KEH-nya',
  translation: 'small; little; of a young person, short',
  context: 'adj',
  level: 'A1',
}

function renderCard(props: Record<string, unknown> = {}) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <ReviewedCardView card={DRILL} targetType="drill" targetId="d1" {...props} />
    </QueryClientProvider>,
  )
}

describe('ReviewedCardView', () => {
  beforeEach(() => vi.clearAllMocks())

  it('fills the blank in, so "gives the answer away" is decidable', () => {
    // The learner sees a gap; a reviewer reading the raw {{answer}} token
    // cannot tell whether the hint hands over what fills it.
    renderCard()
    expect(screen.getByTestId('reviewed-card').textContent).toContain(
      'Casi no 【queda】 vino.',
    )
  })

  it('offers no editor to someone who cannot edit', () => {
    renderCard()
    expect(screen.queryByTestId('reviewed-card-edit')).toBeNull()
  })

  it('edits the card where the complaint is read, and saves what was typed', async () => {
    // The owner's ask in one test: judging a report ends in "yes, and here
    // is the correction", and that used to mean leaving the queue for the
    // content editor and finding the same card again by search.
    mockEdit.mockResolvedValue(undefined)
    renderCard({ canEdit: true })

    fireEvent.click(screen.getByTestId('reviewed-card-edit'))
    fireEvent.change(screen.getByLabelText('Hint'), {
      target: { value: 'there is hardly any left' },
    })
    fireEvent.click(screen.getByTestId('reviewed-card-save'))

    await waitFor(() => expect(mockEdit).toHaveBeenCalled())
    const [type, id, fields] = mockEdit.mock.calls[0]
    expect(type).toBe('drill')
    expect(id).toBe('d1')
    expect(fields.hint).toBe('there is hardly any left')
    // Every other field goes back unchanged rather than blanked — a partial
    // payload from a four-box editor would wipe what it didn't show.
    expect(fields.sentence).toBe('Casi no {{answer}} vino.')
    expect(fields.answer).toBe('queda')
  })

  it('warns when an edit removes the blank from a drill', () => {
    // A drill with no {{answer}} renders with nothing to fill in, and the
    // damage is invisible until a learner meets the card.
    renderCard({ canEdit: true })
    fireEvent.click(screen.getByTestId('reviewed-card-edit'))
    fireEvent.change(screen.getByLabelText('Sentence'), {
      target: { value: 'Casi no queda vino.' },
    })
    expect(screen.getByTestId('drill-blank-warning')).toBeDefined()
  })

  it('never offers to rewrite a word itself, only what it means', () => {
    // The word IS the card's identity — user cards, audio and every example
    // point at that row, so a rename here would silently re-target all of
    // them. The editable pair is the reading and the English definition.
    render(
      <QueryClientProvider
        client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
      >
        <ReviewedCardView
          card={WORD}
          targetType="vocabulary"
          targetId="v1"
          canEdit
        />
      </QueryClientProvider>,
    )
    fireEvent.click(screen.getByTestId('reviewed-card-edit'))
    expect(screen.getByLabelText('Definition (English)')).toBeDefined()
    expect(screen.getByLabelText('Reading')).toBeDefined()
    expect(screen.queryByLabelText('Sentence')).toBeNull()
  })

  it('says so when the save is refused instead of looking like it worked', async () => {
    mockEdit.mockRejectedValue(new Error('403'))
    renderCard({ canEdit: true })
    fireEvent.click(screen.getByTestId('reviewed-card-edit'))
    fireEvent.click(screen.getByTestId('reviewed-card-save'))
    expect(await screen.findByText(/couldn’t save that/i)).toBeDefined()
    // And the editor stays open, holding what was typed.
    expect(screen.getByTestId('reviewed-card-editor')).toBeDefined()
  })
})
