import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

const { mockDismiss, prefsState } = vi.hoisted(() => ({
  mockDismiss: vi.fn(),
  prefsState: { dismissed: [] as string[] },
}))

vi.mock('../api/profile', () => ({ getLanguages: vi.fn() }))
vi.mock('../api/onboarding', () => ({
  getPlacementHistory: vi.fn(),
  placementNext: vi.fn(),
  setLearnerLevel: vi.fn(),
}))
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn(
    (selector: (s: Record<string, unknown>) => unknown) =>
      selector({
        placementOfferDismissed: prefsState.dismissed,
        dismissPlacementOffer: mockDismiss,
        qwertyTranslit: {},
      }),
  ),
}))

import PlacementOffer from '../features/onboarding/PlacementOffer'
import { getLanguages } from '../api/profile'
import { getPlacementHistory, placementNext } from '../api/onboarding'

const mockLanguages = getLanguages as ReturnType<typeof vi.fn>
const mockHistory = getPlacementHistory as ReturnType<typeof vi.fn>
const mockNext = placementNext as ReturnType<typeof vi.fn>

const LANGS = [
  { id: 'lang-he', code: 'he', name: 'Hebrew', rtl: true, is_visible: true },
]

const NEVER_PLACED = {
  attempts: 0, has_placed: false, last_level: null,
  last_taken_at: null, history: [],
}

function renderOffer(languageId: string | null = 'lang-he') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <PlacementOffer languageId={languageId} />
    </QueryClientProvider>,
  )
}

describe('PlacementOffer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    prefsState.dismissed = []
    mockLanguages.mockResolvedValue(LANGS)
    mockHistory.mockResolvedValue(NEVER_PLACED)
  })

  it('offers the test the first time in a language', async () => {
    renderOffer()
    expect(await screen.findByTestId('placement-offer')).toBeDefined()
    expect(screen.getByText(/Want to find your starting level/i)).toBeDefined()
  })

  it('says out loud that it can be retaken any time (owner ask)', async () => {
    renderOffer()
    await screen.findByTestId('placement-offer')
    expect(screen.getByText(/any time/i)).toBeDefined()
    expect(screen.getByText(/Settings/i)).toBeDefined()
  })

  it('stays out of the way once the learner has placed in this language', async () => {
    mockHistory.mockResolvedValue({
      ...NEVER_PLACED, attempts: 1, has_placed: true, last_level: 'B1',
    })
    renderOffer()
    await waitFor(() => expect(mockHistory).toHaveBeenCalled())
    expect(screen.queryByTestId('placement-offer')).toBeNull()
  })

  it('"Not now" remembers the answer instead of asking again', async () => {
    renderOffer()
    fireEvent.click(await screen.findByRole('button', { name: /not now/i }))
    expect(mockDismiss).toHaveBeenCalledWith('lang-he')
  })

  it('does not even ask the server once the offer was declined', async () => {
    prefsState.dismissed = ['lang-he']
    renderOffer()
    await waitFor(() => expect(screen.queryByTestId('placement-offer')).toBeNull())
    expect(mockHistory).not.toHaveBeenCalled()
  })

  it('renders nothing with no active language', async () => {
    renderOffer(null)
    expect(screen.queryByTestId('placement-offer')).toBeNull()
  })

  it('taking the test starts the adaptive run', async () => {
    mockNext.mockResolvedValue({
      available: true, done: false, asked: 0, max_items: 12,
      item: { id: 'i1', kind: 'vocabulary', level: 'A2', prompt: 'water', translation: null },
    })
    renderOffer()
    fireEvent.click(await screen.findByRole('button', { name: /take the test/i }))
    expect(await screen.findByTestId('placement-test')).toBeDefined()
    await waitFor(() => expect(mockNext).toHaveBeenCalledWith('lang-he', []))
    expect(await screen.findByText('water')).toBeDefined()
  })
})
