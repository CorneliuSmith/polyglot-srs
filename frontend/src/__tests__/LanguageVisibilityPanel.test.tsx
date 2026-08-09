import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import LanguageVisibilityPanel from '../features/contribute/LanguageVisibilityPanel'

const { mockSetActive } = vi.hoisted(() => ({ mockSetActive: vi.fn() }))

vi.mock('../api/profile', () => ({ getLanguages: vi.fn() }))
vi.mock('../api/contribute', () => ({
  setLanguageVisibility: vi.fn(),
  setLanguageAutoTranslate: vi.fn(),
  setLanguagePolicy: vi.fn(),
  setLanguageTutorModel: vi.fn(),
  TUTOR_MODELS: ['claude-fable-5', 'claude-sonnet-5'],
  getLanguageReadiness: vi.fn(() => Promise.resolve([])),
  getTranslationStatus: vi.fn(() =>
    Promise.resolve({
      provider_ready: true,
      budget_per_cycle: 50,
      sweep_seconds: 900,
      loop_enabled: true,
      loop: {
        started: true,
        last_cycle_at: new Date().toISOString(),
        cycles: 3,
        last_error: null,
        last_stats: null,
      },
      migrations: {},
      switched_off: [],
      pairs: [],
    }),
  ),
}))
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn(
    (selector: (s: Record<string, unknown>) => unknown) =>
      selector({ setActiveLanguageId: mockSetActive }),
  ),
}))

import { getLanguages } from '../api/profile'
import {
  getLanguageReadiness,
  setLanguageAutoTranslate,
  setLanguagePolicy,
  setLanguageTutorModel,
  setLanguageVisibility,
} from '../api/contribute'

const mockGetLanguages = getLanguages as ReturnType<typeof vi.fn>
const mockSetVisibility = setLanguageVisibility as ReturnType<typeof vi.fn>
const mockSetAutoTranslate = setLanguageAutoTranslate as ReturnType<typeof vi.fn>
const mockReadiness = getLanguageReadiness as ReturnType<typeof vi.fn>
const mockSetPolicy = setLanguagePolicy as ReturnType<typeof vi.fn>
const mockSetTutorModel = setLanguageTutorModel as ReturnType<typeof vi.fn>

const readinessRow = (id: string, awaiting: number) => ({
  id,
  code: id.slice(-2),
  name: id,
  is_visible: false,
  review_policy: 'strict',
  tutor_model: null,
  draft_points: awaiting,
  pending_drills: 0,
  pending_examples: 0,
  awaiting_review: awaiting,
  open_reports: 0,
})

const LANGS = [
  { id: 'lang-es', code: 'es', name: 'Spanish', rtl: false, is_visible: true,
    auto_translate_enabled: false },
  { id: 'lang-he', code: 'he', name: 'Hebrew', rtl: true, is_visible: false,
    auto_translate_enabled: true },
]

function renderPanel() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <LanguageVisibilityPanel />
    </QueryClientProvider>,
  )
}

describe('LanguageVisibilityPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetLanguages.mockResolvedValue(LANGS)
    mockSetVisibility.mockResolvedValue(undefined)
    mockReadiness.mockResolvedValue([])
  })

  it('shows every language with its current visibility state', async () => {
    renderPanel()
    expect(await screen.findByText('Spanish')).toBeDefined()
    expect(screen.getByText('Hebrew')).toBeDefined()
    const es = screen.getByLabelText(
      /spanish visible to learners/i,
    ) as HTMLInputElement
    const he = screen.getByLabelText(
      /hebrew visible to learners/i,
    ) as HTMLInputElement
    expect(es.checked).toBe(true)
    expect(he.checked).toBe(false)
  })

  it('toggling a checkbox calls setLanguageVisibility', async () => {
    renderPanel()
    await screen.findByText('Hebrew')
    const heCheckbox = screen.getByLabelText(/hebrew visible to learners/i)
    fireEvent.click(heCheckbox)
    await waitFor(() =>
      expect(mockSetVisibility).toHaveBeenCalledWith('lang-he', true),
    )
  })

  it('shows the auto-translate switch state and toggles it', async () => {
    mockSetAutoTranslate.mockResolvedValue(undefined)
    renderPanel()
    await screen.findByText('Spanish')
    const es = screen.getByLabelText(
      /spanish automatic translation/i,
    ) as HTMLInputElement
    const he = screen.getByLabelText(
      /hebrew automatic translation/i,
    ) as HTMLInputElement
    expect(es.checked).toBe(false)
    expect(he.checked).toBe(true)

    fireEvent.click(es)
    await waitFor(() =>
      expect(mockSetAutoTranslate).toHaveBeenCalledWith('lang-es', true),
    )
    // The visibility endpoint is never touched by this switch.
    expect(mockSetVisibility).not.toHaveBeenCalled()
  })

  it('surfaces the missing-migration 503 detail on the auto-translate switch', async () => {
    mockSetAutoTranslate.mockRejectedValue({
      response: {
        data: {
          detail:
            'Automatic translation needs migration 20260913 applied — ' +
            'run `supabase db push` (check /api/health/schema)',
        },
      },
    })
    renderPanel()
    await screen.findByText('Spanish')
    fireEvent.click(screen.getByLabelText(/spanish automatic translation/i))
    expect(
      await screen.findByText(/needs migration 20260913 applied/i),
    ).toBeDefined()
  })

  it('clicking a language name switches the active language (the way in for admins)', async () => {
    renderPanel()
    fireEvent.click(await screen.findByText('Hebrew'))
    expect(mockSetActive).toHaveBeenCalledWith('lang-he')
  })

  describe('release gate (owner: "released after review")', () => {
    it('badges the outstanding review backlog per language', async () => {
      mockReadiness.mockResolvedValue([
        readinessRow('lang-he', 12),
        { ...readinessRow('lang-es', 0), is_visible: true },
      ])
      renderPanel()
      expect(await screen.findByText('12 to review')).toBeDefined()
      expect(screen.getByText('Reviewed')).toBeDefined()
    })

    it('asks before releasing a language that still has unreviewed content', async () => {
      mockReadiness.mockResolvedValue([readinessRow('lang-he', 12)])
      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)
      renderPanel()
      await screen.findByText('12 to review')

      fireEvent.click(screen.getByLabelText(/hebrew visible to learners/i))
      expect(confirmSpy).toHaveBeenCalled()
      expect(confirmSpy.mock.calls[0][0]).toMatch(/12 items awaiting review/i)
      // Declined — the language stays hidden.
      expect(mockSetVisibility).not.toHaveBeenCalled()

      confirmSpy.mockRestore()
    })

    it('releases without asking once nothing is awaiting review', async () => {
      mockReadiness.mockResolvedValue([readinessRow('lang-he', 0)])
      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
      renderPanel()
      await screen.findByText('Reviewed')

      fireEvent.click(screen.getByLabelText(/hebrew visible to learners/i))
      expect(confirmSpy).not.toHaveBeenCalled()
      await waitFor(() =>
        expect(mockSetVisibility).toHaveBeenCalledWith('lang-he', true),
      )
      confirmSpy.mockRestore()
    })

    it('never blocks UN-releasing a language', async () => {
      // Pulling something back is always safe — only going live asks.
      mockReadiness.mockResolvedValue([
        { ...readinessRow('lang-es', 99), is_visible: true },
      ])
      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
      renderPanel()
      await screen.findByText('99 to review')

      fireEvent.click(screen.getByLabelText(/spanish visible to learners/i))
      expect(confirmSpy).not.toHaveBeenCalled()
      await waitFor(() =>
        expect(mockSetVisibility).toHaveBeenCalledWith('lang-es', false),
      )
      confirmSpy.mockRestore()
    })
  })

  describe('the per-row settings drawer (one window for every language)', () => {
    /* Review policy and tutor model used to be editable only for the
     * admin's own ACTIVE language, so cycling through the courses meant
     * changing your own study language once per row. Every dial now opens
     * from the row itself. */
    it('opens a row\u2019s drawer with its policy and tutor model', async () => {
      mockReadiness.mockResolvedValue([readinessRow('lang-es', 0)])
      renderPanel()
      await screen.findByText('Spanish')
      fireEvent.click(await screen.findByLabelText(/spanish settings/i))
      const policy = (await screen.findByLabelText(
        /spanish publish policy/i,
      )) as HTMLSelectElement
      // The stored legacy 'strict' reads back as human_only, not as a
      // mystery value the <select> can't display.
      expect(policy.value).toBe('human_only')
      const model = screen.getByLabelText(/spanish tutor model/i) as HTMLSelectElement
      expect(model.value).toBe('')
    })

    it('changing the policy calls the API for THAT language', async () => {
      mockReadiness.mockResolvedValue([readinessRow('lang-es', 0)])
      mockSetPolicy.mockResolvedValue(undefined)
      renderPanel()
      await screen.findByText('Spanish')
      fireEvent.click(await screen.findByLabelText(/spanish settings/i))
      fireEvent.change(await screen.findByLabelText(/spanish publish policy/i), {
        target: { value: 'ai_ok' },
      })
      await waitFor(() =>
        expect(mockSetPolicy).toHaveBeenCalledWith('lang-es', 'ai_ok'))
    })

    it('changing the tutor model calls the API; empty means the default', async () => {
      mockReadiness.mockResolvedValue([readinessRow('lang-es', 0)])
      mockSetTutorModel.mockResolvedValue(undefined)
      renderPanel()
      await screen.findByText('Spanish')
      fireEvent.click(await screen.findByLabelText(/spanish settings/i))
      fireEvent.change(await screen.findByLabelText(/spanish tutor model/i), {
        target: { value: 'claude-sonnet-5' },
      })
      await waitFor(() =>
        expect(mockSetTutorModel).toHaveBeenCalledWith('lang-es', 'claude-sonnet-5'))
    })

    it('opening another row closes the first \u2014 cycling, not stacking', async () => {
      mockReadiness.mockResolvedValue([
        readinessRow('lang-es', 0), readinessRow('lang-he', 0)])
      renderPanel()
      await screen.findByText('Spanish')
      fireEvent.click(await screen.findByLabelText(/spanish settings/i))
      expect(await screen.findByTestId('language-settings-es')).toBeDefined()
      fireEvent.click(screen.getByLabelText(/hebrew settings/i))
      expect(await screen.findByTestId('language-settings-he')).toBeDefined()
      expect(screen.queryByTestId('language-settings-es')).toBeNull()
    })
  })
})
