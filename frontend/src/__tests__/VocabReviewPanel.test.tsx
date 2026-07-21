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
