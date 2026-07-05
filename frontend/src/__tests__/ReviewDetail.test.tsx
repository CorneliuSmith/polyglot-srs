import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ReviewDetail from '../features/review/ReviewDetail'

vi.mock('../api/review', () => ({
  getCardDetail: vi.fn(),
}))

import { getCardDetail } from '../api/review'

const mockGetCardDetail = getCardDetail as ReturnType<typeof vi.fn>

function renderDetail(props: { cardType: 'grammar' | 'vocabulary' }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <ReviewDetail cardId="card-1" cardType={props.cardType} languageCode="tr" />
    </QueryClientProvider>,
  )
}

describe('ReviewDetail', () => {
  beforeEach(() => vi.clearAllMocks())

  it('is collapsed by default and does not fetch', () => {
    renderDetail({ cardType: 'grammar' })
    expect(screen.getByRole('button', { name: /show grammar/i })).toBeDefined()
    expect(mockGetCardDetail).not.toHaveBeenCalled()
  })

  it('labels the toggle "Show examples" for vocab cards', () => {
    renderDetail({ cardType: 'vocabulary' })
    expect(screen.getByRole('button', { name: /show examples/i })).toBeDefined()
  })

  it('lazy-loads and shows grammar explanation + culture note on expand', async () => {
    mockGetCardDetail.mockResolvedValue({
      card_type: 'grammar',
      title: 'Locative case',
      part_of_speech: null,
      definition: null,
      usage_note: null,
      morphology: null,
      explanation: 'Used to express location with -de/-da.',
      culture_note: 'Very common in everyday directions.',
      examples: [{ sentence: 'Evde.', translation: 'At home.', hint: null }],
    })
    renderDetail({ cardType: 'grammar' })

    fireEvent.click(screen.getByRole('button', { name: /show grammar/i }))

    expect(await screen.findByText(/express location with -de\/-da/i)).toBeDefined()
    expect(screen.getByText(/everyday directions/i)).toBeDefined()
    expect(screen.getByText('Evde.')).toBeDefined()
    expect(mockGetCardDetail).toHaveBeenCalledWith('card-1')
  })
})
