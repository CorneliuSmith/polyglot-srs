import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import ContributorPage from '../features/contribute/ContributorPage'

vi.mock('../api/profile', () => ({ getLanguages: vi.fn() }))
vi.mock('../api/contribute', () => ({
  getGrammarForLanguage: vi.fn(),
  saveGrammarExplanation: vi.fn(),
  approveGrammar: vi.fn(),
}))
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn(() => 'lang-tr'),
}))

import { getLanguages } from '../api/profile'
import { getGrammarForLanguage, saveGrammarExplanation } from '../api/contribute'

const mockGetLanguages = getLanguages as ReturnType<typeof vi.fn>
const mockGetGrammar = getGrammarForLanguage as ReturnType<typeof vi.fn>
const mockSave = saveGrammarExplanation as ReturnType<typeof vi.fn>

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ContributorPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ContributorPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetLanguages.mockResolvedValue([{ id: 'lang-tr', code: 'tr', name: 'Turkish', rtl: false }])
  })

  it('lists editable grammar points and saves an edit', async () => {
    mockGetGrammar.mockResolvedValue({
      is_admin: false,
      points: [{
        id: 'p1', title: 'Locative case', level: 'A1',
        explanation: 'Old explanation', culture_note: null,
        explanation_source: 'ai', reviewed: false,
        references: [{ title: 'Wiktionary', url: 'https://en.wiktionary.org/wiki/-de' }],
      }],
    })
    mockSave.mockResolvedValue(undefined)
    renderPage()

    expect(await screen.findByText('Locative case')).toBeDefined()
    expect(screen.getByText(/pending · ai/i)).toBeDefined()

    const textarea = screen.getByDisplayValue('Old explanation')
    fireEvent.change(textarea, { target: { value: 'Better explanation' } })
    fireEvent.click(screen.getByRole('button', { name: /save \(pending review\)/i }))

    await waitFor(() => {
      expect(mockSave).toHaveBeenCalledWith('p1', 'Better explanation', '', [
        { title: 'Wiktionary', url: 'https://en.wiktionary.org/wiki/-de' },
      ])
    })
  })

  it('shows a forbidden message when the user lacks a role (403)', async () => {
    mockGetGrammar.mockRejectedValue({ response: { status: 403 } })
    renderPage()
    expect(await screen.findByText(/don’t have a contributor role/i)).toBeDefined()
  })

  it('shows an Approve button only for admins', async () => {
    mockGetGrammar.mockResolvedValue({
      is_admin: true,
      points: [{
        id: 'p1', title: 'Locative', level: 'A1',
        explanation: 'Has content', culture_note: null,
        explanation_source: 'contributor', reviewed: false,
      }],
    })
    renderPage()
    expect(await screen.findByRole('button', { name: /approve/i })).toBeDefined()
  })
})
