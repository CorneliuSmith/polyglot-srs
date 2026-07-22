import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import GymPage from '../features/gym/GymPage'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (orig) => ({
  ...(await orig<typeof import('react-router-dom')>()),
  useNavigate: () => mockNavigate,
}))
vi.mock('../api/gym', () => ({ getGymManifest: vi.fn() }))
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn(
    (selector: (s: Record<string, unknown>) => unknown) =>
      selector({ activeLanguageId: 'lang-ru' }),
  ),
}))

import { getGymManifest } from '../api/gym'
const mockManifest = getGymManifest as ReturnType<typeof vi.fn>

const MANIFEST = {
  columns: [
    {
      kind: 'verbs', label: 'Verbs',
      entries: [
        { point_id: 'p-present', label: 'Present', usage: 'now and habits',
          example: 'Я читаю. — I read.', level: 'A1', drills: 12,
          nonstandard: false, familiar: false },
        { point_id: 'p-past', label: 'Past', usage: 'what happened',
          example: 'Она была…', level: 'A1', drills: 10,
          nonstandard: false, familiar: true },
        { point_id: 'p-motion', label: 'Going on foot', usage: 'two walk verbs',
          example: 'Я иду…', level: 'A2', drills: 14,
          nonstandard: true, familiar: false },
      ],
    },
    {
      kind: 'nouns', label: 'Nouns',
      entries: [
        { point_id: 'p-acc', label: 'Accusative (what)', usage: 'the object',
          example: 'Я читаю книгу.', level: 'A1', drills: 18,
          nonstandard: false, familiar: false },
      ],
    },
  ],
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <GymPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('GymPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockManifest.mockResolvedValue(MANIFEST)
  })

  it('renders columns, familiar-first, with hover previews in the DOM', async () => {
    renderPage()
    expect(await screen.findByText('Verbs')).toBeDefined()
    expect(screen.getByText('Nouns')).toBeDefined()
    // familiar 'Past' sorts above 'Present'
    const labels = screen
      .getAllByRole('button', { pressed: false })
      .map((b) => b.textContent)
    expect(labels.findIndex((t) => t?.includes('Past'))).toBeLessThan(
      labels.findIndex((t) => t?.includes('Present')),
    )
    expect(screen.getByText('known')).toBeDefined()
    // hover preview content is rendered (revealed on hover/focus via CSS)
    expect(screen.getByText('now and habits')).toBeDefined()
    expect(screen.getByText('Я читаю. — I read.')).toBeDefined()
  })

  it('hides non-standard forms until the toggle, and deselects on untoggle', async () => {
    renderPage()
    await screen.findByText('Verbs')
    expect(screen.queryByText('Going on foot')).toBeNull()
    fireEvent.click(screen.getByLabelText(/include non-standard words/i))
    const motion = await screen.findByRole('button', { name: /going on foot/i })
    fireEvent.click(motion)
    expect(motion.getAttribute('aria-pressed')).toBe('true')
    // untoggling hides AND deselects it
    fireEvent.click(screen.getByLabelText(/include non-standard words/i))
    expect(screen.queryByText('Going on foot')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: /past/i }))
    fireEvent.click(screen.getByRole('button', { name: /start training/i }))
    // Default count of 20 rides along in the URL.
    expect(mockNavigate).toHaveBeenCalledWith('/cram?points=p-past&mix=1&count=20')
  })

  it('starts a mixed cram session with every selected form and chosen count', async () => {
    renderPage()
    await screen.findByText('Verbs')
    fireEvent.click(screen.getByRole('button', { name: /present/i }))
    fireEvent.click(screen.getByRole('button', { name: /accusative/i }))
    // Choose 30 questions instead of the default.
    fireEvent.click(screen.getByRole('button', { name: /^30$/ }))
    fireEvent.click(
      screen.getByRole('button', { name: /start training · 30 questions/i }),
    )
    await waitFor(() => expect(mockNavigate).toHaveBeenCalled())
    const url = mockNavigate.mock.calls[0][0] as string
    expect(url).toContain('/cram?points=')
    expect(url).toContain('p-present')
    expect(url).toContain('p-acc')
    expect(url).toContain('mix=1')
    expect(url).toContain('count=30')
  })

  it('explains when a language has nothing to train', async () => {
    mockManifest.mockResolvedValue({ columns: [] })
    renderPage()
    expect(
      await screen.findByText(/doesn't bend its words enough/i),
    ).toBeDefined()
  })
})
