import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import SpeakPage from '../features/speak/SpeakPage'

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
vi.mock('../api/profile', async (orig) => ({
  ...(await orig<typeof import('../api/profile')>()),
  getLanguages: vi.fn(() =>
    Promise.resolve([{ id: 'lang-es', code: 'es', name: 'Spanish' }]),
  ),
}))
vi.mock('../api/speak', async (orig) => ({
  ...(await orig<typeof import('../api/speak')>()),
  getSpeakStatus: vi.fn(),
  startSpeakSession: vi.fn(),
  sendSpeakTurn: vi.fn(),
  endSpeakSession: vi.fn(),
}))

import {
  endSpeakSession,
  getSpeakStatus,
  sendSpeakTurn,
  startSpeakSession,
} from '../api/speak'

const mockStatus = getSpeakStatus as ReturnType<typeof vi.fn>
const mockStart = startSpeakSession as ReturnType<typeof vi.fn>
const mockTurn = sendSpeakTurn as ReturnType<typeof vi.fn>
const mockEnd = endSpeakSession as ReturnType<typeof vi.fn>

const allowance = {
  tier: 'plus', unlimited: false, entitled: true, limit: 100, used: 3,
  remaining: 97, resets_at: null,
}

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <SpeakPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

/** Get through the topic screen and into a live conversation. */
async function startTalking() {
  mockStatus.mockResolvedValue({ available: true, allowance, sessions: [] })
  mockStart.mockResolvedValue({ session_id: 's1', mode: 'flow', topic: null })
  renderPage()
  const startButton = await screen.findByTestId('speak-start')
  fireEvent.click(startButton)
  await screen.findByTestId('speak-input')
}

describe('SpeakPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('hides the feature when the server says it is unavailable', async () => {
    // The tables land by hand, so the page can exist before the schema does.
    mockStatus.mockResolvedValue({
      available: false, allowance: null, sessions: [],
    })
    renderPage()
    await screen.findByText(/isn’t available/i)
    expect(screen.queryByTestId('speak-start')).not.toBeInTheDocument()
  })

  it('shows the partner’s reply and never the corrections', async () => {
    await startTalking()
    mockTurn.mockResolvedValue({
      reply: '¿Para tomar aquí o para llevar?',
      turn_index: 0,
      allowance,
    })

    fireEvent.change(screen.getByTestId('speak-input'), {
      target: { value: 'Yo quiero un café' },
    })
    fireEvent.click(screen.getByTestId('speak-send'))

    await screen.findByText('¿Para tomar aquí o para llevar?')
    expect(screen.getByText('Yo quiero un café')).toBeInTheDocument()
    // Flow mode's whole promise: feedback that does not interrupt.
    expect(screen.queryByText(/Quiero/)).not.toBeInTheDocument()
  })

  it('gives the message back when sending fails', async () => {
    // Losing what someone just typed is the fastest way to end a session.
    await startTalking()
    mockTurn.mockRejectedValue(new Error('network'))

    const input = screen.getByTestId('speak-input') as HTMLTextAreaElement
    fireEvent.change(input, { target: { value: 'Hola qué tal' } })
    fireEvent.click(screen.getByTestId('speak-send'))

    await waitFor(() => expect(input.value).toBe('Hola qué tal'))
  })

  it('does not send an empty message', async () => {
    await startTalking()
    fireEvent.change(screen.getByTestId('speak-input'), {
      target: { value: '   ' },
    })
    fireEvent.click(screen.getByTestId('speak-send'))
    expect(mockTurn).not.toHaveBeenCalled()
  })

  it('shows the grouped breakdown when the session ends', async () => {
    await startTalking()
    mockEnd.mockResolvedValue({
      already_ended: false,
      summary: {
        groups: [{
          label: 'Subject pronouns',
          note: 'Spanish drops these unless contrasting.',
          examples: ['yo quiero → quiero'],
          count: 3,
        }],
        vocabulary: [{ term: 'para llevar', meaning: 'to take away' }],
        stats: { turns: 4, error_count: 3, types: { pronoun: 3 } },
      },
    })

    fireEvent.click(screen.getByTestId('speak-done'))

    await screen.findByTestId('speak-summary')
    expect(screen.getByText('Subject pronouns')).toBeInTheDocument()
    expect(screen.getByText('yo quiero → quiero')).toBeInTheDocument()
    expect(screen.getByText('para llevar')).toBeInTheDocument()
  })

  it('says so plainly when a session had nothing to correct', async () => {
    await startTalking()
    mockEnd.mockResolvedValue({
      already_ended: false,
      summary: {
        groups: [],
        vocabulary: [],
        stats: { turns: 2, error_count: 0, types: {} },
      },
    })

    fireEvent.click(screen.getByTestId('speak-done'))

    await screen.findByTestId('speak-summary')
    expect(screen.getByText(/Nothing came up/i)).toBeInTheDocument()
  })

  it('shows no score anywhere in the summary', async () => {
    // The plan is explicit: the moment there is a number to chase, the
    // learner stops experimenting and starts playing it safe.
    await startTalking()
    mockEnd.mockResolvedValue({
      already_ended: false,
      summary: {
        groups: [],
        vocabulary: [],
        stats: { turns: 5, error_count: 0, types: {} },
      },
    })
    fireEvent.click(screen.getByTestId('speak-done'))
    await screen.findByTestId('speak-summary')

    expect(screen.queryByText(/%/)).not.toBeInTheDocument()
    expect(screen.queryByText(/\/\s*10\b/)).not.toBeInTheDocument()
  })
})
