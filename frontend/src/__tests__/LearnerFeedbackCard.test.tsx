import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import FeedbackPanel from '../features/contribute/FeedbackPanel'

vi.mock('../api/contribute', () => ({
  getFeedback: vi.fn(),
  resolveFeedback: vi.fn(),
  editReviewedCard: vi.fn(),
}))
import { getFeedback, editReviewedCard } from '../api/contribute'
const mockFeedback = getFeedback as ReturnType<typeof vi.fn>
const mockEdit = editReviewedCard as ReturnType<typeof vi.fn>

function renderPanel() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <FeedbackPanel languageId="lang-1" />
    </QueryClientProvider>,
  )
}

const REPORT = {
  id: 'f1',
  card_type: 'vocabulary',
  content_id: 'v1',
  card_title: 'pequeña',
  message: 'Too much info',
  status: 'open',
  created_at: null,
  target_type: 'vocabulary',
  target_id: 'v1',
  card: {
    sentence: 'pequeña',
    answer: null,
    hint: 'peh-KEH-nya',
    translation: 'small; little; of a young person, short',
    context: 'adj',
    level: 'A1',
  },
}

describe('Learner feedback queue', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows the card the report is about, not just the word', async () => {
    // "Too much info" is a judgement about text that was nowhere on this
    // screen: the queue gave the reviewer a word and a complaint, and
    // deciding between them meant going to look the card up elsewhere.
    mockFeedback.mockResolvedValue([REPORT])
    renderPanel()
    await screen.findByText('Too much info')
    expect(screen.getByTestId('feedback-card-f1').textContent).toContain(
      'small; little; of a young person, short',
    )
  })

  it('corrects the card without leaving the queue', async () => {
    mockFeedback.mockResolvedValue([REPORT])
    mockEdit.mockResolvedValue(undefined)
    renderPanel()

    fireEvent.click(await screen.findByTestId('feedback-card-f1-edit'))
    fireEvent.change(screen.getByLabelText('Definition (English)'), {
      target: { value: 'small' },
    })
    fireEvent.click(screen.getByTestId('feedback-card-f1-save'))

    await waitFor(() => expect(mockEdit).toHaveBeenCalled())
    expect(mockEdit.mock.calls[0][2].translation).toBe('small')
  })

  it('says the card is gone rather than showing a complaint about nothing', async () => {
    // A report outlives the card it names, exactly as a change request does.
    mockFeedback.mockResolvedValue([{ ...REPORT, card: null }])
    renderPanel()
    expect(await screen.findByTestId('feedback-card-gone')).toBeDefined()
  })
})
