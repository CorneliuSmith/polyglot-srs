import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import QualitySettingsPanel from '../features/contribute/QualitySettingsPanel'

vi.mock('../api/profile', () => ({ getLanguages: vi.fn() }))
vi.mock('../api/contribute', async (orig) => ({
  ...(await orig<typeof import('../api/contribute')>()),
  getQualitySettings: vi.fn(),
  updateQualitySettings: vi.fn(),
  updateQualityTarget: vi.fn(),
}))

import { getLanguages } from '../api/profile'
import {
  getQualitySettings,
  updateQualitySettings,
  updateQualityTarget,
  type QualitySettingsResponse,
} from '../api/contribute'
const mockLanguages = getLanguages as ReturnType<typeof vi.fn>
const mockGet = getQualitySettings as ReturnType<typeof vi.fn>
const mockUpdate = updateQualitySettings as ReturnType<typeof vi.fn>
const mockTarget = updateQualityTarget as ReturnType<typeof vi.fn>

const SETTINGS: QualitySettingsResponse = {
  available: true,
  settings: {
    judge_enabled: false, judge_rows_per_cycle: 200, judge_daily_token_cap: 1_500_000,
    judge_model: null,
  },
  spent_today: 12_345,
  targets: {
    ar: { judge_enabled: false, max_bad_card_pct: 15, max_judge_flag_pct: 5 },
    ko: { judge_enabled: true, max_bad_card_pct: 20, max_judge_flag_pct: 5 },
  },
}

function renderPanel() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <QualitySettingsPanel />
    </QueryClientProvider>,
  )
}

describe('QualitySettingsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGet.mockResolvedValue(SETTINGS)
    mockLanguages.mockResolvedValue([
      { id: 'l-ar', code: 'ar', name: 'Arabic', rtl: true, is_visible: true },
      { id: 'l-ko', code: 'ko', name: 'Korean', rtl: false, is_visible: true },
    ])
    mockUpdate.mockImplementation((partial: Record<string, unknown>) =>
      Promise.resolve({ ...SETTINGS, settings: { ...SETTINGS.settings, ...partial } }),
    )
    mockTarget.mockImplementation((code: string, partial: Record<string, unknown>) =>
      Promise.resolve({ code, targets: { ...SETTINGS.targets[code], ...partial } }),
    )
  })

  it('shows the stored values, the spend against the cap, and every course', async () => {
    renderPanel()
    const sw = await screen.findByRole('switch', { name: 'Judge master switch' })
    expect(sw.getAttribute('aria-checked')).toBe('false')
    expect((screen.getByLabelText('Judge rows per cycle') as HTMLInputElement).value).toBe('200')
    expect((screen.getByLabelText('Judge daily token cap') as HTMLInputElement).value).toBe('1500000')
    expect(screen.getByText(/1,500,000 · spent today 12,345 of cap/)).toBeDefined()
    expect((screen.getByLabelText('Judge model') as HTMLInputElement).value).toBe('')
    expect(screen.getByText(/spends the API key every night it is on/)).toBeDefined()
    const ko = await screen.findByTestId('quality-target-ko')
    expect(within(ko).getByText('Korean')).toBeDefined()
    expect(within(ko).getByRole('switch').getAttribute('aria-checked')).toBe('true')
    expect((within(ko).getByLabelText('Korean max bad-card %') as HTMLInputElement).value).toBe('20')
  })

  it('Save is disabled until the field differs from what is stored', async () => {
    renderPanel()
    const input = await screen.findByLabelText('Judge rows per cycle')
    const row = input.closest('div')!
    const save = within(row).getByRole('button', { name: 'Save' })
    expect(save).toBeDisabled()
    fireEvent.change(input, { target: { value: '300' } })
    expect(save).not.toBeDisabled()
    // Back to the stored value: nothing to save again.
    fireEvent.change(input, { target: { value: '200' } })
    expect(save).toBeDisabled()
    // Out of the CHECK constraint's range: the button, not the server, says no.
    fireEvent.change(input, { target: { value: '20000' } })
    expect(save).toBeDisabled()
  })

  it('saving sends only the changed field', async () => {
    renderPanel()
    const input = await screen.findByLabelText('Judge rows per cycle')
    fireEvent.change(input, { target: { value: '300' } })
    fireEvent.click(within(input.closest('div')!).getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(mockUpdate).toHaveBeenCalledTimes(1))
    expect(mockUpdate).toHaveBeenCalledWith({ judge_rows_per_cycle: 300 })
    // The response is now what is shown, so Save goes quiet again.
    await waitFor(() =>
      expect(within(input.closest('div')!).getByRole('button', { name: 'Save' })).toBeDisabled(),
    )
  })

  it('a blank model saves as null — the checker tier — not as an empty string', async () => {
    mockGet.mockResolvedValue({
      ...SETTINGS, settings: { ...SETTINGS.settings, judge_model: 'claude-sonnet-5' },
    })
    renderPanel()
    const input = await screen.findByLabelText('Judge model')
    expect((input as HTMLInputElement).value).toBe('claude-sonnet-5')
    fireEvent.change(input, { target: { value: '  ' } })
    fireEvent.click(within(input.closest('div')!).getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(mockUpdate).toHaveBeenCalledWith({ judge_model: null }))
  })

  it('the master switch flips judge_enabled and nothing else', async () => {
    renderPanel()
    fireEvent.click(await screen.findByRole('switch', { name: 'Judge master switch' }))
    await waitFor(() => expect(mockUpdate).toHaveBeenCalledWith({ judge_enabled: true }))
    await waitFor(() =>
      expect(
        screen.getByRole('switch', { name: 'Judge master switch' }).getAttribute('aria-checked'),
      ).toBe('true'),
    )
  })

  it('with the table absent every control is disabled and the migration is named', async () => {
    mockGet.mockResolvedValue({ ...SETTINGS, available: false })
    renderPanel()
    expect(await screen.findByText(/migration 20261029/)).toBeDefined()
    expect(screen.getByText(/Rollouts → Deployment/)).toBeDefined()
    expect(screen.getByRole('switch', { name: 'Judge master switch' })).toBeDisabled()
    expect(screen.getByLabelText('Judge rows per cycle')).toBeDisabled()
    expect(screen.getByLabelText('Judge daily token cap')).toBeDisabled()
    expect(screen.getByLabelText('Judge model')).toBeDisabled()
    for (const b of screen.getAllByRole('button', { name: 'Save' })) expect(b).toBeDisabled()
    for (const s of screen.getAllByRole('switch')) expect(s).toBeDisabled()
    expect(mockUpdate).not.toHaveBeenCalled()
  })

  it('a course toggle saves that course alone', async () => {
    renderPanel()
    const ar = await screen.findByTestId('quality-target-ar')
    fireEvent.click(within(ar).getByRole('switch', { name: 'Judge Arabic' }))
    await waitFor(() => expect(mockTarget).toHaveBeenCalledWith('ar', { judge_enabled: true }))
    await waitFor(() =>
      expect(within(ar).getByRole('switch').getAttribute('aria-checked')).toBe('true'),
    )
    expect(mockUpdate).not.toHaveBeenCalled()
  })

  it('a course threshold saves only the number that changed', async () => {
    renderPanel()
    const ar = await screen.findByTestId('quality-target-ar')
    const save = within(ar).getByRole('button', { name: 'Save' })
    expect(save).toBeDisabled()
    fireEvent.change(within(ar).getByLabelText('Arabic max judge-flag %'), {
      target: { value: '7.5' },
    })
    expect(save).not.toBeDisabled()
    fireEvent.click(save)
    await waitFor(() => expect(mockTarget).toHaveBeenCalledWith('ar', { max_judge_flag_pct: 7.5 }))
  })

  it("shows the server's 503 detail when a save is refused", async () => {
    mockUpdate.mockRejectedValue({
      response: {
        status: 503,
        data: { detail: 'Quality settings need migration 20261029 applied — check /api/health/schema' },
      },
    })
    renderPanel()
    fireEvent.click(await screen.findByRole('switch', { name: 'Judge master switch' }))
    expect((await screen.findByRole('alert')).textContent).toContain('check /api/health/schema')
  })
})
