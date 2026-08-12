import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import VocabReviewPanel from '../features/contribute/VocabReviewPanel'

vi.mock('../api/contribute', async (orig) => ({
  ...(await orig<typeof import('../api/contribute')>()),
  getVocabForLanguage: vi.fn(),
  getMyRoles: vi.fn(() =>
    Promise.resolve({ roles: [{ role: 'reviewer', language_id: null }], is_admin: false }),
  ),
  createChangeRequest: vi.fn(() => Promise.resolve({ id: 'cr-1' })),
}))

import { getVocabForLanguage, createChangeRequest } from '../api/contribute'
const mockVocab = getVocabForLanguage as ReturnType<typeof vi.fn>
const mockCreate = createChangeRequest as ReturnType<typeof vi.fn>

function renderPanel() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={qc}>
      <VocabReviewPanel languageId="lang-es" languageCode="es" />
    </QueryClientProvider>,
  )
}

const items = [
  { id: 'v1', word: 'hola', reading: null, part_of_speech: 'interj', level: 'A1', frequency_rank: 3, definition: 'hello', example_count: 2 },
  { id: 'v2', word: 'adiós', reading: null, part_of_speech: 'interj', level: 'A2', frequency_rank: 40, definition: null, example_count: 0 },
]

describe('VocabReviewPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockVocab.mockResolvedValue({ items, is_admin: false, can_review: true, can_contribute: true })
  })

  it('lists vocab and flags thin entries (no definition / no examples)', async () => {
    renderPanel()
    expect(await screen.findByText('hola')).toBeDefined()
    expect(screen.getByText('adiós')).toBeDefined()
    expect(screen.getByText('no definition')).toBeDefined()
    // The entry missing both definition and examples is marked "thin".
    expect(screen.getByText('thin')).toBeDefined()
  })

  it('filters by search', async () => {
    renderPanel()
    await screen.findByText('hola')
    fireEvent.change(screen.getByLabelText('Search vocab'), { target: { value: 'adi' } })
    expect(screen.queryByText('hola')).toBeNull()
    expect(screen.getByText('adiós')).toBeDefined()
  })

  it('lets a reviewer raise a votable change request on a word', async () => {
    renderPanel()
    fireEvent.click(await screen.findByText('hola'))
    fireEvent.click(await screen.findByRole('button', { name: /suggest a change/i }))
    fireEvent.change(await screen.findByPlaceholderText("What's wrong?"), {
      target: { value: 'Definition should be "hi/hello"' },
    })
    fireEvent.click(screen.getByRole('button', { name: /send to review board/i }))
    await waitFor(() =>
      expect(mockCreate).toHaveBeenCalledWith(
        expect.objectContaining({ target_type: 'vocabulary', target_id: 'v1' }),
      ),
    )
  })
})

/* Gap G6: "Flagged examples 3 · Translation fixes 4" counted language-wide,
 * but nothing said WHICH of two thousand words carried them, so the only
 * way to find one was to expand words at random. */
describe('VocabReviewPanel — needs attention', () => {
  const marked = [
    { ...items[0], flagged_count: 1, suggestion_count: 0 },
    { ...items[1], flagged_count: 0, suggestion_count: 2 },
    { id: 'v3', word: 'gato', reading: null, part_of_speech: 'n', level: 'A1',
      frequency_rank: 9, definition: 'cat', example_count: 3,
      flagged_count: 0, suggestion_count: 0 },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    mockVocab.mockResolvedValue({
      items: marked, is_admin: false, can_review: true, can_contribute: true,
    })
  })

  it('marks the words carrying flagged examples and translation fixes', async () => {
    renderPanel()
    expect(await screen.findByText('1 flagged')).toBeDefined()
    expect(screen.getByText('2 fixes')).toBeDefined()
  })

  it('filters the list down to those words on one click', async () => {
    renderPanel()
    const chip = await screen.findByTestId('needs-attention-chip')
    expect(chip.textContent).toContain('Needs attention (2)')
    fireEvent.click(chip)
    expect(screen.getByText('hola')).toBeDefined()
    expect(screen.getByText('adiós')).toBeDefined()
    // The clean word drops out.
    expect(screen.queryByText('gato')).toBeNull()
  })

  it('offers no chip when nothing needs attention', async () => {
    mockVocab.mockResolvedValue({
      items, is_admin: false, can_review: true, can_contribute: true,
    })
    renderPanel()
    await screen.findByText('hola')
    expect(screen.queryByTestId('needs-attention-chip')).toBeNull()
  })
})
