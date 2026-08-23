import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { applyUiSkin, currentUiSkin, DEFAULT_SKIN } from '../lib/uiSkin'
import UiSkinApplier from '../components/UiSkinApplier'
import ExperimentsPanel from '../features/contribute/ExperimentsPanel'
import AppearanceTrial from '../features/settings/AppearanceTrial'

vi.mock('../api/profile', async (orig) => ({
  ...(await orig<typeof import('../api/profile')>()),
  getProfile: vi.fn(),
  getMyExperiments: vi.fn(),
  chooseExperimentVariant: vi.fn(),
}))
vi.mock('../api/feedback', async (orig) => ({
  ...(await orig<typeof import('../api/feedback')>()),
  sendFeedback: vi.fn(),
}))
vi.mock('../api/contribute', async (orig) => ({
  ...(await orig<typeof import('../api/contribute')>()),
  getExperiments: vi.fn(),
  updateExperiment: vi.fn(),
  assignExperiment: vi.fn(),
}))

import {
  chooseExperimentVariant,
  getMyExperiments,
  getProfile,
} from '../api/profile'
import {
  assignExperiment,
  getExperiments,
  updateExperiment,
} from '../api/contribute'
import { sendFeedback } from '../api/feedback'

const mockProfile = getProfile as ReturnType<typeof vi.fn>
const mockMine = getMyExperiments as ReturnType<typeof vi.fn>
const mockChoose = chooseExperimentVariant as ReturnType<typeof vi.fn>
const mockList = getExperiments as ReturnType<typeof vi.fn>
const mockUpdate = updateExperiment as ReturnType<typeof vi.fn>
const mockAssign = assignExperiment as ReturnType<typeof vi.fn>

function renderWithQuery(ui: React.ReactNode) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

const EXPERIMENT = {
  key: 'ui_skin',
  name: 'Visual direction',
  description: 'Which look the app is wearing.',
  variants: [
    { key: 'classic', label: 'Classic' },
    { key: 'flat', label: 'Flat (ink borders)' },
  ],
  default_variant: 'classic',
  rollout: { flat: 25 },
  enabled: true,
  learner_choice: true,
  counts: [{ variant: 'flat', source: 'admin', count: 2 }],
  assigned: [
    {
      user_id: 'u1',
      email: 'kate@example.com',
      variant: 'flat',
      source: 'admin' as const,
      note: null,
      assigned_at: '2026-08-20T00:00:00Z',
    },
  ],
}

describe('the visual direction, applied', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    document.documentElement.removeAttribute('data-ui')
  })

  it('the default skin carries no attribute at all', () => {
    // Classic must be the absence of a marker, not a marker of its own —
    // that is what lets the whole skin be deleted in one commit.
    applyUiSkin('flat')
    expect(document.documentElement.getAttribute('data-ui')).toBe('flat')
    applyUiSkin(DEFAULT_SKIN)
    expect(document.documentElement.hasAttribute('data-ui')).toBe(false)
    expect(currentUiSkin()).toBe(DEFAULT_SKIN)
  })

  it('a null variant is the default, not a skin called "null"', () => {
    applyUiSkin('flat')
    applyUiSkin(null)
    expect(document.documentElement.hasAttribute('data-ui')).toBe(false)
  })

  it('puts the account on the skin the server assigned it', async () => {
    mockProfile.mockResolvedValue({ experiments: { ui_skin: 'flat' } })
    renderWithQuery(<UiSkinApplier />)
    await waitFor(() =>
      expect(document.documentElement.getAttribute('data-ui')).toBe('flat'),
    )
  })

  it('a server with no experiments puts everyone back on Classic', async () => {
    // The withdrawal path. If a missing key read as "leave what was there",
    // turning an experiment off would strand every browser that had already
    // cached a variant — the kill switch would work everywhere except on
    // the people who were actually in the experiment.
    applyUiSkin('flat')
    mockProfile.mockResolvedValue({ experiments: {} })
    renderWithQuery(<UiSkinApplier />)
    await waitFor(() =>
      expect(document.documentElement.hasAttribute('data-ui')).toBe(false),
    )
  })

  it('leaves the painted skin alone until the profile actually lands', async () => {
    // The inline script in index.html paints from the cached value. Clearing
    // it while the request is in flight is the flash the whole arrangement
    // exists to prevent.
    applyUiSkin('flat')
    mockProfile.mockReturnValue(new Promise(() => {}))
    renderWithQuery(<UiSkinApplier />)
    expect(document.documentElement.getAttribute('data-ui')).toBe('flat')
  })
})

describe('the admin rollout panel', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows a rollout with its share and who is pinned to it', async () => {
    mockList.mockResolvedValue([EXPERIMENT])
    renderWithQuery(<ExperimentsPanel />)
    expect(await screen.findByText('Visual direction')).toBeInTheDocument()
    expect(
      (screen.getByTestId('experiment-rollout-ui_skin-flat') as HTMLInputElement)
        .value,
    ).toBe('25')
    expect(screen.getByText(/kate@example.com/)).toBeInTheDocument()
  })

  it('turning a rollout off sends only that field', async () => {
    // Not cosmetic: a patch that also re-sent the rollout would let an
    // "off" click quietly overwrite a percentage someone else had just
    // changed in another tab.
    mockList.mockResolvedValue([EXPERIMENT])
    mockUpdate.mockResolvedValue({ ...EXPERIMENT, enabled: false })
    renderWithQuery(<ExperimentsPanel />)
    fireEvent.click(await screen.findByTestId('experiment-enabled-ui_skin'))
    // First argument only: react-query hands the mutation function a second
    // context argument of its own.
    await waitFor(() =>
      expect(mockUpdate.mock.calls[0]?.[0]).toEqual({
        key: 'ui_skin',
        enabled: false,
      }),
    )
  })

  it('assigns a named person by email', async () => {
    mockList.mockResolvedValue([EXPERIMENT])
    mockAssign.mockResolvedValue({ user_id: 'u2', variant: 'flat' })
    renderWithQuery(<ExperimentsPanel />)
    fireEvent.change(await screen.findByTestId('experiment-email-ui_skin'), {
      target: { value: 'sam@example.com' },
    })
    fireEvent.click(screen.getByTestId('experiment-assign-ui_skin'))
    await waitFor(() =>
      expect(mockAssign.mock.calls[0]?.[0]).toEqual({
        key: 'ui_skin',
        email: 'sam@example.com',
        variant: 'flat',
      }),
    )
  })

  it('says what the server said when the migration is missing', async () => {
    mockList.mockRejectedValue({
      response: { data: { detail: 'Experiments need migration 20260930 applied' } },
    })
    renderWithQuery(<ExperimentsPanel />)
    expect(await screen.findByTestId('experiments-error')).toHaveTextContent(
      '20260930',
    )
  })

  it('a share cannot be pushed past 100 from the input itself', async () => {
    mockList.mockResolvedValue([EXPERIMENT])
    mockUpdate.mockResolvedValue(EXPERIMENT)
    renderWithQuery(<ExperimentsPanel />)
    fireEvent.change(
      await screen.findByTestId('experiment-rollout-ui_skin-flat'),
      { target: { value: '400' } },
    )
    await waitFor(() =>
      expect(mockUpdate.mock.calls[0]?.[0]).toEqual({
        key: 'ui_skin',
        rollout: { flat: 100 },
      }),
    )
  })
})

describe('the learner’s own switch', () => {
  beforeEach(() => vi.clearAllMocks())

  it('is invisible on an account that is not in a rollout', async () => {
    mockMine.mockResolvedValue([])
    renderWithQuery(<AppearanceTrial />)
    await waitFor(() => expect(mockMine).toHaveBeenCalled())
    expect(screen.queryByTestId('appearance-trial')).not.toBeInTheDocument()
  })

  it('lets someone switch back, which is the point of offering it', async () => {
    mockMine.mockResolvedValue([
      { ...EXPERIMENT, current: 'flat' },
    ])
    mockChoose.mockResolvedValue({ key: 'ui_skin', variant: 'classic' })
    renderWithQuery(<AppearanceTrial />)
    fireEvent.click(await screen.findByTestId('trial-ui_skin-classic'))
    await waitFor(() =>
      expect(mockChoose).toHaveBeenCalledWith('ui_skin', 'classic'),
    )
  })

  it('marks which one they are on', async () => {
    mockMine.mockResolvedValue([{ ...EXPERIMENT, current: 'flat' }])
    renderWithQuery(<AppearanceTrial />)
    const flat = await screen.findByTestId('trial-ui_skin-flat')
    expect(flat).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByTestId('trial-ui_skin-classic')).toHaveAttribute(
      'aria-pressed',
      'false',
    )
  })
})


describe('the A/B/C/D lineup', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    document.documentElement.removeAttribute('data-ui')
    document.getElementById('ui-skin-editorial-font')?.remove()
  })

  it('the admin panel offers a rollout share for every non-default variant', async () => {
    // The panel is generic over the server's variant list — adding C and D
    // in the migration must surface controls with no frontend change.
    mockList.mockResolvedValue([{
      ...EXPERIMENT,
      variants: [
        { key: 'classic', label: 'Classic' },
        { key: 'editorial', label: 'A · Editorial (serif, paper)' },
        { key: 'flat', label: 'B · Ink Grid (square, no shadows)' },
        { key: 'ground', label: 'C · Language as Ground (flag-tinted page)' },
        { key: 'focus', label: 'D · One Thing at a Time (bigger drills)' },
      ],
      rollout: {},
    }])
    renderWithQuery(<ExperimentsPanel />)
    await screen.findByText('Visual direction')
    for (const key of ['editorial', 'flat', 'ground', 'focus']) {
      expect(
        screen.getByTestId(`experiment-rollout-ui_skin-${key}`),
      ).toBeInTheDocument()
    }
    // …and each is assignable to a named account by its letter.
    const assign = screen.getByTestId(
      'experiment-assign-variant-ui_skin',
    ) as HTMLSelectElement
    expect(
      Array.from(assign.options).map((o) => o.value),
    ).toEqual(['classic', 'editorial', 'flat', 'ground', 'focus'])
  })

  it('the editorial skin fetches its serif only when worn', () => {
    applyUiSkin('flat')
    expect(document.getElementById('ui-skin-editorial-font')).toBeNull()
    applyUiSkin('editorial')
    const link = document.getElementById('ui-skin-editorial-font')
    expect(link).not.toBeNull()
    expect(link?.getAttribute('href')).toContain('Literata')
    // Idempotent — reapplying must not stack a second stylesheet.
    applyUiSkin('editorial')
    expect(
      document.querySelectorAll('#ui-skin-editorial-font').length,
    ).toBe(1)
  })
})


describe('feedback from inside the trial', () => {
  const mockSend = sendFeedback as ReturnType<typeof vi.fn>

  beforeEach(() => vi.clearAllMocks())

  it('a sentence typed where they switched arrives with no course attached', async () => {
    // The server stamps which variant the sender was on; the client's job
    // is only to not mis-file it under a language.
    mockMine.mockResolvedValue([{ ...EXPERIMENT, current: 'ground' }])
    mockSend.mockResolvedValue({ id: 'f1' })
    renderWithQuery(<AppearanceTrial />)
    fireEvent.change(await screen.findByTestId('trial-feedback-note'), {
      target: { value: 'C makes Korean feel like Korean' },
    })
    fireEvent.click(screen.getByTestId('trial-feedback-send'))
    await waitFor(() =>
      expect(mockSend).toHaveBeenCalledWith({
        category: 'other',
        message: 'C makes Korean feel like Korean',
        languageId: null,
        page: 'appearance-trial',
      }),
    )
    expect(await screen.findByTestId('trial-feedback-sent')).toBeInTheDocument()
  })

  it('an empty note cannot be sent', async () => {
    mockMine.mockResolvedValue([{ ...EXPERIMENT, current: 'flat' }])
    renderWithQuery(<AppearanceTrial />)
    expect(await screen.findByTestId('trial-feedback-send')).toBeDisabled()
    expect(mockSend).not.toHaveBeenCalled()
  })
})
