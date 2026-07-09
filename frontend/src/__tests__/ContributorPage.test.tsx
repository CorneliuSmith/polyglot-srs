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
  getFeedback: vi.fn(() => Promise.resolve([])),
  resolveFeedback: vi.fn(),
  setLanguagePolicy: vi.fn(),
  listAllRoles: vi.fn(() => Promise.resolve([])),
  grantRole: vi.fn(),
  revokeRole: vi.fn(),
  flagPointIssue: vi.fn(() => Promise.resolve()),
  getReviewNotes: vi.fn(() => Promise.resolve([])),
  resolveReviewNote: vi.fn(() => Promise.resolve()),
  setLanguageTutorModel: vi.fn(() => Promise.resolve()),
  TUTOR_MODELS: ['claude-opus-4-8', 'claude-sonnet-5'],
  getTutorUsage: vi.fn(() =>
    Promise.resolve({ days: 30, rows: [], total_messages: 0, total_est_cost_usd: 0 }),
  ),
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
  flagPointIssue,
  getReviewNotes,
  resolveReviewNote,
} from '../api/contribute'

const mockGetLanguages = getLanguages as ReturnType<typeof vi.fn>
const mockGetGrammar = getGrammarForLanguage as ReturnType<typeof vi.fn>
const mockSave = saveGrammarExplanation as ReturnType<typeof vi.fn>
const mockAiCheck = runAiCheck as ReturnType<typeof vi.fn>
const mockFlag = flagPointIssue as ReturnType<typeof vi.fn>
const mockGetNotes = getReviewNotes as ReturnType<typeof vi.fn>
const mockResolveNote = resolveReviewNote as ReturnType<typeof vi.fn>

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
    mockGetGrammar.mockResolvedValue({ is_admin: false, points: [basePoint], review_policy: "strict" })
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
    mockGetGrammar.mockResolvedValue({ is_admin: true, points: [basePoint], review_policy: "strict" })
    mockAiCheck.mockResolvedValue({ status: 'concerns', notes: 'Drill 2 answer is wrong.' })
    renderPage()

    // The human linguist review is flagged as required and not yet done.
    expect(await screen.findByText(/required — not yet reviewed/i)).toBeDefined()

    fireEvent.click(screen.getByRole('button', { name: /run ai check/i }))
    await waitFor(() => {
      expect(mockAiCheck).toHaveBeenCalledWith('p1')
    })
  })

  it('files a reviewer issue against a point', async () => {
    mockGetGrammar.mockResolvedValue({ is_admin: false, points: [basePoint], review_policy: 'strict' })
    mockFlag.mockResolvedValue(undefined)
    renderPage()

    fireEvent.click(await screen.findByRole('button', { name: /flag an issue/i }))
    fireEvent.change(screen.getByLabelText(/issue description/i), {
      target: { value: 'Drill 3 uses the Ibadan form' },
    })
    fireEvent.click(screen.getByRole('button', { name: /file issue/i }))

    await waitFor(() => {
      expect(mockFlag).toHaveBeenCalledWith('p1', 'Drill 3 uses the Ibadan form')
    })
  })

  it('admin sets a per-language tutor model', async () => {
    const { setLanguageTutorModel } = await import('../api/contribute')
    const mockSetModel = setLanguageTutorModel as ReturnType<typeof vi.fn>
    mockGetGrammar.mockResolvedValue({
      is_admin: true, points: [], review_policy: 'strict', tutor_model: null,
    })
    renderPage()

    const select = (await screen.findByLabelText('Tutor model')) as HTMLSelectElement
    expect(select.value).toBe('') // default (server setting)
    fireEvent.change(select, { target: { value: 'claude-sonnet-5' } })
    await waitFor(() => {
      expect(mockSetModel).toHaveBeenCalledWith('lang-tr', 'claude-sonnet-5')
    })
  })

  it('admin sees the tutor cost monitor with priced rows', async () => {
    const { getTutorUsage } = await import('../api/contribute')
    const mockUsage = getTutorUsage as ReturnType<typeof vi.fn>
    mockUsage.mockResolvedValue({
      days: 30,
      rows: [{
        language_id: 'lang-tr', language_name: 'Turkish',
        model: 'claude-sonnet-5', kind: 'chat', messages: 42,
        input_tokens: 120_000, output_tokens: 30_000,
        cache_write_tokens: 4_000, cache_read_tokens: 2_000_000,
        est_cost_usd: 1.42,
      }],
      total_messages: 42,
      total_est_cost_usd: 1.42,
    })
    mockGetGrammar.mockResolvedValue({
      is_admin: true, points: [], review_policy: 'strict', tutor_model: null,
    })
    renderPage()

    const panel = await screen.findByTestId('tutor-costs')
    expect(panel.textContent).toContain('Turkish')
    expect(panel.textContent).toContain('claude-sonnet-5')
    expect(panel.textContent).toContain('42 messages')
    expect(panel.textContent).toContain('$1.42')
    expect(panel.textContent).toContain('2.1M / 30,000') // cache reads included in "in"
  })

  it('non-admins never see the cost monitor', async () => {
    mockGetGrammar.mockResolvedValue({
      is_admin: false, points: [basePoint], review_policy: 'strict',
    })
    renderPage()
    await screen.findByText('Locative case')
    expect(screen.queryByTestId('tutor-costs')).toBeNull()
  })

  it('shows open issues and lets a reviewer resolve them', async () => {
    mockGetGrammar.mockResolvedValue({
      is_admin: false, can_review: true, points: [basePoint], review_policy: 'strict',
    })
    mockGetNotes.mockResolvedValue([{
      id: 'n1', grammar_point_id: 'p1', point_title: 'Locative case',
      level: 'A1', note: 'tone marks look off', status: 'open',
      author_email: 'linguist@x.com', created_at: null,
    }])
    mockResolveNote.mockResolvedValue(undefined)
    renderPage()

    const panel = await screen.findByTestId('issues-panel')
    expect(panel.textContent).toContain('tone marks look off')
    expect(panel.textContent).toContain('linguist@x.com')

    fireEvent.click(screen.getByRole('button', { name: /resolve/i }))
    await waitFor(() => expect(mockResolveNote).toHaveBeenCalledWith('n1'))
  })
})
