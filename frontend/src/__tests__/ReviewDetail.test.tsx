import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import ReviewDetail from '../features/review/ReviewDetail'

vi.mock('../api/review', () => ({
  getCardDetail: vi.fn(),
}))
vi.mock('../api/curriculum', () => ({
  setReferenceRead: vi.fn().mockResolvedValue({ ref_key: 'x', read: true }),
}))

import { getCardDetail } from '../api/review'
import { setReferenceRead } from '../api/curriculum'

const mockGetCardDetail = getCardDetail as ReturnType<typeof vi.fn>
const mockSetReferenceRead = setReferenceRead as ReturnType<typeof vi.fn>

function renderDetail(props: { cardType: 'grammar' | 'vocabulary' }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ReviewDetail cardId="card-1" cardType={props.cardType} languageCode="tr" />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ReviewDetail', () => {
  beforeEach(() => vi.clearAllMocks())

  it('is collapsed by default and does not fetch', () => {
    renderDetail({ cardType: 'grammar' })
    expect(screen.getByRole('button', { name: /show info/i })).toBeDefined()
    expect(mockGetCardDetail).not.toHaveBeenCalled()
  })

  it('labels the toggle "Show info" for vocab cards', () => {
    renderDetail({ cardType: 'vocabulary' })
    expect(screen.getByRole('button', { name: /show info/i })).toBeDefined()
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

    fireEvent.click(screen.getByRole('button', { name: /show info/i }))

    expect(await screen.findByText(/express location with -de\/-da/i)).toBeDefined()
    expect(screen.getByText(/everyday directions/i)).toBeDefined()
    expect(screen.getByText('Evde.')).toBeDefined()
    expect(mockGetCardDetail).toHaveBeenCalledWith('card-1')
  })

  it('shows the WP13 item page: stage, progress, related grid, split resources', async () => {
    mockGetCardDetail.mockResolvedValue({
      card_type: 'grammar',
      point_id: 'gp-1',
      title: 'Locative case',
      part_of_speech: null,
      definition: null,
      usage_note: null,
      morphology: null,
      explanation: 'Used to express location.',
      culture_note: null,
      examples: [{ sentence: 'Evde.', translation: 'At home.', hint: null }],
      references: [
        { title: 'Wikipedia: Locative', url: 'https://example.org/loc' },
        { title: 'Locative chapter', book: 'A Turkish Grammar', page: '42' },
      ],
      read_refs: [],
      related: [
        {
          id: 'gp-2',
          title: 'Accusative case',
          level: 'A1',
          function_note: null,
          contrast: 'Locative marks WHERE; accusative marks WHAT.',
          stage: 'adept',
        },
      ],
      progress: {
        stage: 'seasoned',
        first_studied: '2026-06-01T00:00:00Z',
        times_studied: 12,
        accuracy: 0.75,
        streak: 4,
        misses: 2,
        next_review: '2026-08-01T00:00:00Z',
      },
    })
    renderDetail({ cardType: 'grammar' })
    fireEvent.click(screen.getByRole('button', { name: /show info/i }))

    // stage badge + progress panel
    expect(await screen.findByText('Seasoned')).toBeDefined()
    expect(screen.getByText('75%')).toBeDefined()
    expect(screen.getByText('Times studied')).toBeDefined()

    // related grid with the neighbour's stage
    expect(screen.getByText('Accusative case')).toBeDefined()
    expect(screen.getByText(/marks WHAT/)).toBeDefined()
    expect(screen.getByText('Adept')).toBeDefined()

    // resources split online/offline
    expect(screen.getByText('Online')).toBeDefined()
    expect(screen.getByText('Offline')).toBeDefined()
    expect(screen.getByText(/A Turkish Grammar, p\. 42/)).toBeDefined()

    // read-tracking round-trips through the API
    fireEvent.click(screen.getAllByRole('button', { name: /mark read/i })[0])
    await waitFor(() =>
      expect(mockSetReferenceRead).toHaveBeenCalledWith(
        'gp-1',
        'https://example.org/loc',
        true,
      ),
    )
  })

  it('blurs example translations until toggled', async () => {
    mockGetCardDetail.mockResolvedValue({
      card_type: 'vocabulary',
      title: 'ev',
      part_of_speech: 'noun',
      definition: 'house',
      usage_note: null,
      morphology: null,
      explanation: null,
      culture_note: null,
      examples: [{ sentence: 'Evde kal.', translation: 'Stay at home.', hint: null }],
      your_sentences: [{ sentence: 'Benim evim küçük.', translation: 'My house is small.' }],
    })
    renderDetail({ cardType: 'vocabulary' })
    fireEvent.click(screen.getByRole('button', { name: /show info/i }))

    const translation = await screen.findByText('Stay at home.')
    const blurButton = translation.closest('button')!
    expect(blurButton.className).toContain('blur-sm')

    // per-item click reveals
    fireEvent.click(blurButton)
    expect(blurButton.className).not.toContain('blur-sm')

    // the learner's own sentences render under Examples
    expect(screen.getByText('Your sentences')).toBeDefined()
    expect(screen.getByText('Benim evim küçük.')).toBeDefined()

    // global toggle reveals the rest
    fireEvent.click(screen.getByRole('button', { name: /show translations/i }))
    const own = screen.getByText('My house is small.').closest('button')!
    expect(own.className).not.toContain('blur-sm')
  })
})
