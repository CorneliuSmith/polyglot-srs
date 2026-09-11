import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import HandwritingPanel from '../features/settings/HandwritingPanel'

vi.mock('react-router-dom', async (orig) => ({
  ...(await orig<typeof import('react-router-dom')>()),
  useNavigate: () => vi.fn(),
}))
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn(
    (sel: (s: Record<string, unknown>) => unknown) => sel({ activeLanguageId: 'lang-ar' }),
  ),
}))
vi.mock('../api/profile', () => ({
  getLanguages: vi.fn().mockResolvedValue([
    { id: 'lang-ar', code: 'ar', name: 'Arabic', rtl: true, is_visible: true },
  ]),
}))
vi.mock('../api/write', () => ({
  getHandProfile: vi.fn(),
  setHandAdapt: vi.fn().mockResolvedValue(undefined),
  resetHand: vi.fn().mockResolvedValue(undefined),
}))
import { getHandProfile, resetHand, setHandAdapt } from '../api/write'
const mockProfile = getHandProfile as ReturnType<typeof vi.fn>
const EMPTY = { right: 0, wrong: 0, total: 0, letters_to_watch: [], legibility_mean: null, history: [] }

function renderPanel() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <HandwritingPanel />
    </QueryClientProvider>,
  )
}

describe('HandwritingPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
  })

  it('hides itself until the migration is there', async () => {
    mockProfile.mockResolvedValue({ available: false, adapt: false, habits: [], stats: {}, samples: 0, confirmed: 0, readout: EMPTY })
    renderPanel()
    await waitFor(() => expect(mockProfile).toHaveBeenCalled())
    expect(screen.queryByTestId('hand-panel')).not.toBeInTheDocument()
  })

  it('shows what is kept, and turning it off asks first then deletes', async () => {
    mockProfile.mockResolvedValue({ available: true, adapt: true, habits: [], stats: {}, samples: 4, confirmed: 1, readout: { right: 5, wrong: 2, total: 7, letters_to_watch: [{ letter: 'أ', count: 2 }], legibility_mean: 3.5, history: [3, 4] } })
    renderPanel()
    expect(await screen.findByTestId('hand-toggle')).toHaveAttribute('aria-checked', 'true')
    await waitFor(() => expect(screen.getByTestId('hand-kept')).toHaveTextContent(/4 samples kept for Arabic/))
    expect(screen.getByTestId('hand-accuracy')).toHaveTextContent(/5 of 7/)
    expect(screen.getByTestId('hand-accuracy')).toHaveTextContent('أ')
    fireEvent.click(screen.getByTestId('hand-toggle'))
    expect(window.confirm).toHaveBeenCalled()
    await waitFor(() => expect(setHandAdapt).toHaveBeenCalledWith(false))
  })

  it('does not ask before turning it on, and resets one language or all', async () => {
    mockProfile.mockResolvedValue({ available: true, adapt: false, habits: [], stats: {}, samples: 0, confirmed: 0, readout: EMPTY })
    renderPanel()
    fireEvent.click(await screen.findByTestId('hand-toggle'))
    expect(window.confirm).not.toHaveBeenCalled()
    await waitFor(() => expect(setHandAdapt).toHaveBeenCalledWith(true))

    mockProfile.mockResolvedValue({ available: true, adapt: true, habits: [], stats: {}, samples: 2, confirmed: 2, readout: EMPTY })
    renderPanel()
    const resets = await screen.findAllByTestId('hand-reset')
    fireEvent.click(resets[resets.length - 1])
    await waitFor(() => expect(resetHand).toHaveBeenCalledWith('lang-ar'))
    const alls = screen.getAllByTestId('hand-reset-all')
    fireEvent.click(alls[alls.length - 1])
    await waitFor(() => expect(resetHand).toHaveBeenCalledWith(undefined))
  })
})
