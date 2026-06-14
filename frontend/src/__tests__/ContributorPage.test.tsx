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
  runAiCheck: vi.fn(),
  createGrammarPoint: vi.fn(),
}))
// DrillsEditor is its own tested unit; stub it here to keep this test focused.
vi.mock('../features/contribute/DrillsEditor', () => ({ default: () => null }))
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn(() => 'lang-tr'),
}))

import { getLanguages } from '../api/profile'
import {
  getGrammarForLanguage,
  saveGrammarExplanation,
  runAiCheck,
} from '../api/contribute'

const mockGetLanguages = getLanguages as ReturnType<typeof vi.fn>
const mockGetGrammar = getGrammarForLanguage as ReturnType<typeof vi.fn>
const mockSave = saveGrammarExplanation as ReturnType<typeof vi.fn>
const mockAiCheck = runAiCheck as ReturnType<typeof vi.fn>

const basePoint = {
  id: 'p1', title: 'Locative case', level: 'A1',
  explanation: 'Old explanation', culture_note: null,
  explanation_source: 'ai', reviewed: false,
  references: [{ title: 'Wiktionary', url: 'https://en.wiktionary.org/wiki/-de' }],
  ai_check_status: null, ai_check_notes: null, reviewed_by: null, reviewed_at: null,
}

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
    mockGetGrammar.mockResolvedValue({ is_admin: false, points: [basePoint] })
    mockSave.mockResolvedValue(undefined)
    renderPage()

    expect(await screen.findByText('Locative case')).toBeDefined()
    expect(screen.getByText(/pending review · ai/i)).toBeDefined()

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
      points: [{ ...basePoint, explanation: 'Has content', explanation_source: 'contributor' }],
    })
    renderPage()
    expect(await screen.findByRole('button', { name: /approve \(linguist/i })).toBeDefined()
  })

  it('shows the required human review status and runs the AI check', async () => {
    mockGetGrammar.mockResolvedValue({ is_admin: true, points: [basePoint] })
    mockAiCheck.mockResolvedValue({ status: 'concerns', notes: 'Drill 2 answer is wrong.' })
    renderPage()

    // The human linguist review is flagged as required and not yet done.
    expect(await screen.findByText(/required — not yet reviewed/i)).toBeDefined()

    fireEvent.click(screen.getByRole('button', { name: /run ai check/i }))
    await waitFor(() => {
      expect(mockAiCheck).toHaveBeenCalledWith('p1')
    })
  })
})
