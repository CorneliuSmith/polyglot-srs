import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import LanguageScopePicker from '../components/LanguageScopePicker'
import StaffNotifications from '../features/contribute/StaffNotifications'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (orig) => ({
  ...(await orig<typeof import('react-router-dom')>()),
  useNavigate: () => mockNavigate,
}))
vi.mock('../api/contribute', async (orig) => ({
  ...(await orig<typeof import('../api/contribute')>()),
  getReviewNotifications: vi.fn(),
}))

const setWorkspaceLanguageId = vi.fn()
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn((sel: (s: Record<string, unknown>) => unknown) =>
    sel({ activeLanguageId: 'lang-es', setWorkspaceLanguageId }),
  ),
}))

import { getReviewNotifications } from '../api/contribute'

const mockNotifications = getReviewNotifications as ReturnType<typeof vi.fn>

const LANGUAGES = [
  { id: 'lang-es', code: 'es', name: 'Spanish', rtl: false, is_visible: true },
  { id: 'lang-he', code: 'he', name: 'Hebrew', rtl: true, is_visible: true },
  { id: 'lang-ko', code: 'ko', name: 'Korean', rtl: false, is_visible: true },
]

function renderWithQuery(ui: React.ReactNode) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  )
}

function notifications(over: Record<string, unknown> = {}) {
  return {
    languages: [
      {
        id: 'lang-he', code: 'he', name: 'Hebrew', is_visible: true,
        total: 9, counts: { pending_drills: 7, notes: 2 },
      },
      {
        id: 'lang-es', code: 'es', name: 'Spanish', is_visible: true,
        total: 0, counts: {},
      },
    ],
    review_total: 9,
    feedback: [],
    feedback_total: 0,
    is_admin: false,
    is_staff: true,
    ...over,
  }
}

describe('cycling the working language', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockNotifications.mockResolvedValue(notifications())
  })

  it('steps to the next language on one tap', async () => {
    // The verb the owner used was "cycle": working through every course
    // should be a repeated single tap, not open-menu-find-next-select.
    const onChange = vi.fn()
    renderWithQuery(
      <LanguageScopePicker
        languages={LANGUAGES}
        value="lang-es"
        onChange={onChange}
      />,
    )
    fireEvent.click(screen.getByTestId('scope-next'))
    expect(onChange).toHaveBeenCalledWith('lang-he')
  })

  it('wraps around at the ends rather than dead-ending', async () => {
    const onChange = vi.fn()
    renderWithQuery(
      <LanguageScopePicker
        languages={LANGUAGES}
        value="lang-ko"
        onChange={onChange}
      />,
    )
    fireEvent.click(screen.getByTestId('scope-next'))
    expect(onChange).toHaveBeenCalledWith('lang-es')

    fireEvent.click(screen.getByTestId('scope-prev'))
    expect(onChange).toHaveBeenLastCalledWith('lang-he')
  })

  it('puts the waiting count on the options themselves', async () => {
    // So the choice of where to work next is made before the click, rather
    // than by switching to a language and looking.
    renderWithQuery(
      <LanguageScopePicker
        languages={LANGUAGES}
        value="lang-es"
        onChange={vi.fn()}
      />,
    )
    await waitFor(() =>
      expect(screen.getByRole('option', { name: /Hebrew · 9 waiting/ }))
        .toBeInTheDocument(),
    )
    // A quiet language says nothing rather than "0 waiting".
    expect(screen.getByRole('option', { name: 'Spanish' })).toBeInTheDocument()
  })

  it('offers the loudest other language when this one is clear', async () => {
    const onChange = vi.fn()
    renderWithQuery(
      <LanguageScopePicker
        languages={LANGUAGES}
        value="lang-es"
        onChange={onChange}
      />,
    )
    fireEvent.click(await screen.findByTestId('scope-jump'))
    expect(onChange).toHaveBeenCalledWith('lang-he')
  })

  it('does not nag when the language you are on has the work', async () => {
    renderWithQuery(
      <LanguageScopePicker
        languages={LANGUAGES}
        value="lang-he"
        onChange={vi.fn()}
      />,
    )
    await waitFor(() => expect(mockNotifications).toHaveBeenCalled())
    expect(screen.queryByTestId('scope-jump')).not.toBeInTheDocument()
  })
})

describe('what is waiting, per language', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockNotifications.mockResolvedValue(notifications())
  })

  it('opens the workspace already scoped to the language you picked', async () => {
    // Scope first, then navigate: landing on the workspace and watching it
    // re-scope a frame later is the flash removed everywhere else.
    renderWithQuery(<StaffNotifications onClose={vi.fn()} />)
    fireEvent.click(await screen.findByTestId('staff-lang-he'))
    expect(setWorkspaceLanguageId).toHaveBeenCalledWith('lang-he')
    expect(mockNavigate).toHaveBeenCalledWith('/contribute')
  })

  it('names the biggest queue, not just the total', async () => {
    // "8 waiting" says there is work; "8 waiting · generated drills" says
    // whether it is yours to do.
    renderWithQuery(<StaffNotifications onClose={vi.fn()} />)
    expect(await screen.findByText(/7 generated drills/)).toBeInTheDocument()
  })

  it('leaves out the languages with nothing in them', async () => {
    renderWithQuery(<StaffNotifications onClose={vi.fn()} />)
    await screen.findByTestId('staff-lang-he')
    expect(screen.queryByTestId('staff-lang-es')).not.toBeInTheDocument()
  })

  it('says so plainly when nothing is waiting anywhere', async () => {
    mockNotifications.mockResolvedValue(
      notifications({ languages: [], review_total: 0 }),
    )
    renderWithQuery(<StaffNotifications onClose={vi.fn()} />)
    expect(await screen.findByTestId('staff-all-clear')).toBeInTheDocument()
  })

  it('shows an admin the feedback channel, including what belongs to no course', async () => {
    mockNotifications.mockResolvedValue(
      notifications({
        is_admin: true,
        feedback: [
          { language_id: 'lang-es', language_name: 'Spanish', count: 2 },
          { language_id: null, language_name: null, count: 1 },
        ],
        feedback_total: 3,
      }),
    )
    renderWithQuery(<StaffNotifications onClose={vi.fn()} />)
    expect(await screen.findByText('Not about one language')).toBeInTheDocument()
  })
})
