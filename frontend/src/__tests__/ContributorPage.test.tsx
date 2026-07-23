import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import ContributorPage from '../features/contribute/ContributorPage'

vi.mock('../api/profile', () => ({ getLanguages: vi.fn() }))
vi.mock('../api/contribute', () => ({
  getAnalyticsTimeseries: vi.fn(() => Promise.resolve([])),
  getAnalyticsCohorts: vi.fn(() => Promise.resolve([])),
  listAccounts: vi.fn(() => Promise.resolve([])),
  deleteAccount: vi.fn(),
  overridePlan: vi.fn(),
  getTranslationReviews: vi.fn(() => Promise.resolve([])),
  approveTranslationReview: vi.fn(),
  rejectTranslationReview: vi.fn(),
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
  setTutorAccess: vi.fn(() => Promise.resolve()),
  flagPointIssue: vi.fn(() => Promise.resolve()),
  getReviewNotes: vi.fn(() => Promise.resolve([])),
  resolveReviewNote: vi.fn(() => Promise.resolve()),
  setLanguageTutorModel: vi.fn(() => Promise.resolve()),
  getGenerationCoverage: vi.fn(() =>
    Promise.resolve({
      available: false, coverage: [], recommended_next: [],
      limits: { max_items: 100, max_per_item: 10 },
    }),
  ),
  runGeneration: vi.fn(),
  getPendingExamples: vi.fn(() => Promise.resolve([])),
  reviewExample: vi.fn(),
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

async function openTab(name: 'Contribute' | 'Review' | 'Admin') {
  fireEvent.click(await screen.findByRole('tab', { name }))
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
    await openTab('Review')
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
    await openTab('Admin')

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
    await openTab('Admin')

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

  it('admin edits roles inline from the accounts table', async () => {
    const { listAccounts, listAllRoles, grantRole, revokeRole } =
      await import('../api/contribute')
    const mockAccounts = listAccounts as ReturnType<typeof vi.fn>
    const mockAllRoles = listAllRoles as ReturnType<typeof vi.fn>
    const mockGrant = grantRole as ReturnType<typeof vi.fn>
    const mockRevoke = revokeRole as ReturnType<typeof vi.fn>

    mockGetGrammar.mockResolvedValue({
      is_admin: true, points: [], review_policy: 'strict', tutor_model: null,
    })
    mockAccounts.mockResolvedValue([{
      id: 'u-2', email: 'friend@x.com', created_at: '2026-07-01T00:00:00Z',
      last_sign_in_at: null, plan_scope: 'all', plan_language: null,
      tutor_access: 'default', tutor_daily_cap: null,
      roles: ['reviewer'], cards: 10, languages_studied: 1,
    }])
    mockAllRoles.mockResolvedValue([{
      user_id: 'u-2', email: 'friend@x.com', language_id: 'lang-tr',
      language_code: 'tr', role: 'reviewer', created_at: null,
    }])
    mockGrant.mockResolvedValue(undefined)
    mockRevoke.mockResolvedValue(undefined)
    renderPage()
    await openTab('Admin')

    fireEvent.click(await screen.findByRole('button', { name: /manage accounts/i }))
    const table = await screen.findByTestId('accounts-table')
    expect(table.textContent).toContain('friend@x.com')
    // (chip text is lowercase; the capital R comes from CSS `capitalize`)
    expect(table.textContent).toContain('reviewer')
    expect(table.textContent).toContain('Turkish')

    // Revoke the existing grant from its chip.
    fireEvent.click(
      screen.getByRole('button', {
        name: /revoke reviewer \(turkish\) for friend@x\.com/i,
      }),
    )
    await waitFor(() =>
      expect(mockRevoke).toHaveBeenCalledWith({
        user_id: 'u-2', role: 'reviewer', language_id: 'lang-tr',
      }),
    )

    // Grant a new role inline (defaults: reviewer scope All languages).
    // Scope to the table — the Roles panel below has its own Grant button.
    fireEvent.click(
      screen.getByRole('button', { name: /add role for friend@x\.com/i }),
    )
    fireEvent.change(screen.getByLabelText(/new role for friend@x\.com/i), {
      target: { value: 'admin' },
    })
    fireEvent.click(within(table).getByRole('button', { name: /^grant$/i }))
    await waitFor(() =>
      expect(mockGrant).toHaveBeenCalledWith({
        email: 'friend@x.com', role: 'admin', language_id: null,
      }),
    )
  })

  it('admin enables the tutor for an account with a daily cap', async () => {
    const { listAccounts, listAllRoles, setTutorAccess } =
      await import('../api/contribute')
    const mockSetTutor = setTutorAccess as ReturnType<typeof vi.fn>
    ;(listAllRoles as ReturnType<typeof vi.fn>).mockResolvedValue([])
    ;(listAccounts as ReturnType<typeof vi.fn>).mockResolvedValue([{
      id: 'u-2', email: 'friend@x.com', created_at: null, last_sign_in_at: null,
      plan_scope: 'all', plan_language: null,
      tutor_access: 'enabled', tutor_daily_cap: 10,
      roles: [], cards: 0, languages_studied: 0,
    }])
    mockGetGrammar.mockResolvedValue({
      is_admin: true, points: [], review_policy: 'strict', tutor_model: null,
    })
    renderPage()
    await openTab('Admin')

    fireEvent.click(await screen.findByRole('button', { name: /manage accounts/i }))
    // Current state renders: enabled + its cap.
    const select = (await screen.findByLabelText(
      /tutor access for friend@x\.com/i,
    )) as HTMLSelectElement
    expect(select.value).toBe('enabled')
    const cap = screen.getByLabelText(
      /tutor daily message cap for friend@x\.com/i,
    ) as HTMLInputElement
    expect(cap.value).toBe('10')

    // Tighten the cap: type + blur persists it.
    fireEvent.change(cap, { target: { value: '5' } })
    fireEvent.blur(cap)
    await waitFor(() =>
      expect(mockSetTutor).toHaveBeenCalledWith('u-2', 'enabled', 5),
    )

    // Block the account outright.
    fireEvent.change(select, { target: { value: 'blocked' } })
    await waitFor(() =>
      expect(mockSetTutor).toHaveBeenCalledWith('u-2', 'blocked', 5),
    )
  })

  it("admin can't revoke their own admin role from the accounts table", async () => {
    const { listAccounts, listAllRoles } = await import('../api/contribute')
    const { useAuthStore } = await import('../stores/authStore')
    ;(listAccounts as ReturnType<typeof vi.fn>).mockResolvedValue([{
      id: 'u-self', email: 'me@x.com', created_at: null, last_sign_in_at: null,
      plan_scope: 'all', plan_language: null, roles: ['admin'],
      tutor_access: 'default', tutor_daily_cap: null,
      cards: 0, languages_studied: 0,
    }])
    ;(listAllRoles as ReturnType<typeof vi.fn>).mockResolvedValue([{
      user_id: 'u-self', email: 'me@x.com', language_id: null,
      language_code: null, role: 'admin', created_at: null,
    }])
    mockGetGrammar.mockResolvedValue({
      is_admin: true, points: [], review_policy: 'strict', tutor_model: null,
    })
    useAuthStore.setState({
      session: { user: { id: 'u-self' } } as never,
    })
    try {
      renderPage()
    await openTab('Admin')
      fireEvent.click(
        await screen.findByRole('button', { name: /manage accounts/i }),
      )
      const revoke = await screen.findByRole('button', {
        name: /revoke admin \(all languages\) for me@x\.com/i,
      })
      expect((revoke as HTMLButtonElement).disabled).toBe(true)
    } finally {
      useAuthStore.setState({ session: null })
    }
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
    await openTab('Review')

    const panel = await screen.findByTestId('issues-panel')
    expect(panel.textContent).toContain('tone marks look off')
    expect(panel.textContent).toContain('linguist@x.com')

    fireEvent.click(screen.getByRole('button', { name: /resolve/i }))
    await waitFor(() => expect(mockResolveNote).toHaveBeenCalledWith('n1'))
  })
})
