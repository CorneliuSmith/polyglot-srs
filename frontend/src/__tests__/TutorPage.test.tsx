import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import TutorPage from '../features/tutor/TutorPage'
import type { TutorAllowance } from '../api/tutor'

vi.mock('../api/profile', () => ({
  getLanguages: vi.fn(),
}))

vi.mock('../api/tutor', () => ({
  getTutorStatus: vi.fn(),
  getTutorSessions: vi.fn(() => Promise.resolve([])),
  sendTutorMessage: vi.fn(),
  streamTutorMessage: vi.fn(),
  endTutorSession: vi.fn(),
}))

vi.mock('../api/billing', () => ({
  createCheckout: vi.fn(),
}))

vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn(() => 'lang-tr'),
}))

import { getLanguages } from '../api/profile'
import {
  getTutorStatus,
  sendTutorMessage,
  streamTutorMessage,
  endTutorSession,
} from '../api/tutor'
import { createCheckout } from '../api/billing'

const mockGetLanguages = getLanguages as ReturnType<typeof vi.fn>
const mockGetTutorStatus = getTutorStatus as ReturnType<typeof vi.fn>
const mockSendTutorMessage = sendTutorMessage as ReturnType<typeof vi.fn>
const mockStreamTutorMessage = streamTutorMessage as ReturnType<typeof vi.fn>
const mockEndTutorSession = endTutorSession as ReturnType<typeof vi.fn>
const mockCreateCheckout = createCheckout as ReturnType<typeof vi.fn>

const turkish = { id: 'lang-tr', code: 'tr', name: 'Turkish', rtl: false }

const unlimited: TutorAllowance = {
  tier: 'unlimited', unlimited: true, entitled: true,
  limit: null, used: 0, remaining: null, resets_at: null,
}

const freeAllowance = (remaining: number): TutorAllowance => ({
  tier: 'free', unlimited: false, entitled: false,
  limit: 20, used: 20 - remaining, remaining,
  resets_at: '2026-08-01T00:00:00+00:00',
})

const plusAllowance = (remaining: number): TutorAllowance => ({
  tier: 'plus', unlimited: false, entitled: true,
  limit: 100, used: 100 - remaining, remaining,
  resets_at: '2026-07-08T00:00:00+00:00',
})

const statusWith = (allowance: TutorAllowance) => ({
  available: true,
  entitled: allowance.entitled,
  allowance,
})

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/tutor']}>
        <TutorPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('TutorPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetLanguages.mockResolvedValue([turkish])
    mockEndTutorSession.mockResolvedValue(undefined)
    // Default: streaming transport unavailable -> the page falls back to
    // the plain endpoint, which most tests exercise.
    mockStreamTutorMessage.mockRejectedValue(new Error('no stream in jsdom'))
  })

  it('shows the welcome message (operator unlimited mode, no meter)', async () => {
    mockGetTutorStatus.mockResolvedValue(statusWith(unlimited))
    renderPage()
    expect(await screen.findByText(/I’m your Turkish tutor/i)).toBeDefined()
    expect(screen.queryByTestId('tutor-allowance')).toBeNull()
  })

  it('free tier chats with a visible monthly meter — no paywall', async () => {
    mockGetTutorStatus.mockResolvedValue(statusWith(freeAllowance(14)))
    renderPage()
    expect(await screen.findByText(/I’m your Turkish tutor/i)).toBeDefined()
    const meter = screen.getByTestId('tutor-allowance')
    expect(meter.textContent).toContain('14 of 20 free messages')
    expect(meter.textContent).toContain('never per message')
    expect(screen.getByPlaceholderText(/message your tutor/i)).toBeDefined()
  })

  it('plus tier shows the daily fair-use meter', async () => {
    mockGetTutorStatus.mockResolvedValue(statusWith(plusAllowance(93)))
    renderPage()
    const meter = await screen.findByTestId('tutor-allowance')
    expect(meter.textContent).toContain('93 of 100 messages left today')
    expect(meter.textContent).toContain('your price never changes')
  })

  it('exhausted free tier blocks input and offers flat-price Plus', async () => {
    mockGetTutorStatus.mockResolvedValue(statusWith(freeAllowance(0)))
    mockCreateCheckout.mockResolvedValue({ granted: false, url: 'https://checkout.stripe/x' })
    const original = window.location
    Object.defineProperty(window, 'location', { value: { href: '' }, writable: true })
    renderPage()

    const panel = await screen.findByTestId('tutor-exhausted')
    expect(panel.textContent).toContain('free tutor messages')
    expect(panel.textContent).toContain('flat price')
    expect(screen.queryByPlaceholderText(/message your tutor/i)).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: /get plus for turkish/i }))
    await waitFor(() => {
      expect(mockCreateCheckout).toHaveBeenCalledWith('lang-tr')
      expect(window.location.href).toBe('https://checkout.stripe/x')
    })
    Object.defineProperty(window, 'location', { value: original, writable: true })
  })

  it('exhausted plus tier explains the daily reset without an upsell', async () => {
    mockGetTutorStatus.mockResolvedValue(statusWith(plusAllowance(0)))
    renderPage()
    const panel = await screen.findByTestId('tutor-exhausted')
    expect(panel.textContent).toContain('resets tomorrow')
    expect(panel.textContent).toContain('price never changes')
    expect(screen.queryByRole('button', { name: /get plus/i })).toBeNull()
  })

  it('shows unavailable state when the tutor is not configured', async () => {
    mockGetTutorStatus.mockResolvedValue({
      available: false, entitled: false, allowance: null,
    })
    renderPage()
    expect(await screen.findByText(/isn’t available/i)).toBeDefined()
  })

  it('sends a message, renders the reply, and updates the meter', async () => {
    mockGetTutorStatus.mockResolvedValue(statusWith(freeAllowance(14)))
    mockSendTutorMessage.mockResolvedValue({
      reply: 'Harika! Let’s drill the locative.',
      allowance: freeAllowance(13),
    })
    renderPage()

    const input = await screen.findByPlaceholderText(/message your tutor/i)
    fireEvent.change(input, { target: { value: 'Help me with -de' } })
    fireEvent.keyDown(input, { key: 'Enter' })

    expect(await screen.findByText('Help me with -de')).toBeDefined()
    expect(
      await screen.findByText(/Harika! Let’s drill the locative\./),
    ).toBeDefined()
    expect(mockSendTutorMessage).toHaveBeenCalledWith('lang-tr', 'tr', [
      { role: 'user', content: 'Help me with -de' },
    ], 'practice')
    expect(screen.getByTestId('tutor-allowance').textContent).toContain(
      '13 of 20',
    )
  })

  it('a structured 402 flips to the exhausted panel instead of an error', async () => {
    mockGetTutorStatus.mockResolvedValue(statusWith(freeAllowance(1)))
    mockSendTutorMessage.mockRejectedValue({
      response: { status: 402, data: { detail: { code: 'allowance_exhausted' } } },
    })
    renderPage()

    const input = await screen.findByPlaceholderText(/message your tutor/i)
    fireEvent.change(input, { target: { value: 'hello' } })
    fireEvent.keyDown(input, { key: 'Enter' })

    expect(await screen.findByTestId('tutor-exhausted')).toBeDefined()
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('reference mode sends mode=reference (WP18c)', async () => {
    mockGetTutorStatus.mockResolvedValue(statusWith(freeAllowance(14)))
    mockSendTutorMessage.mockResolvedValue({ reply: 'ok', allowance: null })
    renderPage()

    fireEvent.click(await screen.findByRole('button', { name: /^reference$/i }))
    const input = screen.getByPlaceholderText(/message your tutor/i)
    fireEvent.change(input, { target: { value: 'what does -de mean?' } })
    fireEvent.keyDown(input, { key: 'Enter' })

    await screen.findByText('what does -de mean?')
    await waitFor(() =>
      expect(mockSendTutorMessage).toHaveBeenCalledWith(
        'lang-tr', 'tr',
        [{ role: 'user', content: 'what does -de mean?' }],
        'reference',
      ),
    )
  })

  it('shows the tutor-managed Active Focus chips (WP18b)', async () => {
    mockGetTutorStatus.mockResolvedValue({
      ...statusWith(freeAllowance(14)),
      focus: [
        { structure: 'Locative case', reason: 'confuses -de/-da' },
        { structure: 'Vowel harmony', reason: 'suffix selection errors' },
      ],
    })
    renderPage()
    const chips = await screen.findByTestId('active-focus')
    expect(chips.textContent).toContain('Locative case')
    expect(chips.textContent).toContain('Vowel harmony')
  })

  it('lists past sessions on demand (WP18a)', async () => {
    const { getTutorSessions } = await import('../api/tutor')
    ;(getTutorSessions as ReturnType<typeof vi.fn>).mockResolvedValue([
      { id: 's1', summary: 'Drilled the locative; retry -de/-da tomorrow.',
        message_count: 9, created_at: '2026-07-15T10:00:00Z' },
    ])
    mockGetTutorStatus.mockResolvedValue(statusWith(freeAllowance(14)))
    renderPage()

    fireEvent.click(await screen.findByRole('button', { name: /past sessions/i }))
    expect(await screen.findByText(/Drilled the locative/)).toBeDefined()
    expect(screen.getByTestId('past-sessions').textContent).toContain(
      '9 messages',
    )
  })

  it('flushes the session to memory when End session is clicked', async () => {
    mockGetTutorStatus.mockResolvedValue(statusWith(unlimited))
    mockSendTutorMessage.mockResolvedValue({ reply: 'Harika!', allowance: null })
    renderPage()

    const input = await screen.findByPlaceholderText(/message your tutor/i)
    fireEvent.change(input, { target: { value: 'Help me with -de' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    await screen.findByText(/Harika!/)

    fireEvent.click(screen.getByRole('button', { name: /end session/i }))
    await waitFor(() => {
      expect(mockEndTutorSession).toHaveBeenCalledWith(
        'lang-tr',
        'tr',
        expect.arrayContaining([
          { role: 'user', content: 'Help me with -de' },
          { role: 'assistant', content: 'Harika!' },
        ]),
      )
    })
  })

  it('renders streamed text incrementally, then the final reply', async () => {
    mockGetTutorStatus.mockResolvedValue(statusWith(unlimited))
    mockStreamTutorMessage.mockImplementation(
      async (_id, _code, _msgs, onDelta: (t: string) => void) => {
        onDelta('Harika! ')
        onDelta('Harika! Devam edelim.')
        return { reply: 'Harika! Devam edelim.', allowance: null }
      },
    )
    renderPage()

    const input = await screen.findByPlaceholderText(/message your tutor/i)
    fireEvent.change(input, { target: { value: 'Merhaba' } })
    fireEvent.keyDown(input, { key: 'Enter' })

    expect(await screen.findByText(/Devam edelim\./)).toBeDefined()
    expect(mockSendTutorMessage).not.toHaveBeenCalled() // no fallback needed
  })

  it('shows an error banner when sending fails for other reasons', async () => {
    mockGetTutorStatus.mockResolvedValue(statusWith(unlimited))
    mockSendTutorMessage.mockRejectedValue(new Error('network'))
    renderPage()

    const input = await screen.findByPlaceholderText(/message your tutor/i)
    fireEvent.change(input, { target: { value: 'hello' } })
    fireEvent.keyDown(input, { key: 'Enter' })

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeDefined()
    })
  })
})
