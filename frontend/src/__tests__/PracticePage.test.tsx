import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import PracticePage from '../features/dashboard/PracticePage'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (orig) => ({
  ...(await orig<typeof import('react-router-dom')>()),
  useNavigate: () => mockNavigate,
}))
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn(
    (sel: (s: Record<string, unknown>) => unknown) =>
      sel({ activeLanguageId: 'lang-es' }),
  ),
}))
vi.mock('../api/gym', () => ({ getGymManifest: vi.fn() }))
// The page's other sections fetch on mount; they aren't what's under test.
vi.mock('../features/recommendations/NewPicksPrompt', () => ({
  default: () => null,
}))
vi.mock('../features/decks/PersonalDecksSection', () => ({
  default: () => null,
}))

import { getGymManifest } from '../api/gym'
const mockManifest = getGymManifest as ReturnType<typeof vi.fn>

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <PracticePage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('PracticePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockManifest.mockResolvedValue({ columns: [] })
  })

  it('leads with Speak, and it is the only accented thing on the screen', async () => {
    // One element carries the accent, everything else stays quiet — that is
    // the whole reason the eye lands anywhere. Speak arriving as the fourth
    // of four identical tiles is how a new feature goes unnoticed.
    renderPage()
    const speak = await screen.findByTestId('tile-speak')

    expect(speak.className).toContain('bg-lang')
    for (const other of ['tile-read', 'tile-tutor']) {
      expect(screen.getByTestId(other).className).not.toContain('bg-lang ')
    }
  })

  it('says what Speak actually does, not just its name', async () => {
    renderPage()
    await screen.findByTestId('tile-speak')
    expect(screen.getByText(/Have a conversation/i)).toBeInTheDocument()
    expect(screen.getByText('New')).toBeInTheDocument()
  })

  it('opens Speak', async () => {
    renderPage()
    fireEvent.click(await screen.findByTestId('tile-speak'))
    expect(mockNavigate).toHaveBeenCalledWith('/speak')
  })

  it('keeps the quiet row to the languages that have a Gym', async () => {
    mockManifest.mockResolvedValue({ columns: ['tense'] })
    renderPage()
    await waitFor(() =>
      expect(screen.queryByTestId('tile-gym')).toBeInTheDocument(),
    )
    // Gym, Read, Tutor — Speak has its own row above them.
    expect(screen.getByTestId('feature-tiles').className).toContain('grid-cols-3')
  })

  it('drops to two across for an uninflected language', async () => {
    renderPage()
    await screen.findByTestId('tile-read')
    expect(screen.queryByTestId('tile-gym')).not.toBeInTheDocument()
    expect(screen.getByTestId('feature-tiles').className).toContain('grid-cols-2')
  })

  it('disables the language-dependent entries with no course chosen', async () => {
    const { usePrefsStore } = await import('../stores/prefsStore')
    ;(usePrefsStore as unknown as ReturnType<typeof vi.fn>).mockImplementation(
      (sel: (s: Record<string, unknown>) => unknown) =>
        sel({ activeLanguageId: null }),
    )
    renderPage()
    expect(await screen.findByTestId('tile-speak')).toBeDisabled()
  })
})
