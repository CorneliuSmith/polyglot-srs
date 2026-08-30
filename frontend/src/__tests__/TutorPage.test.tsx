import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import TutorPage from '../features/tutor/TutorPage'
import type { TutorAllowance } from '../api/tutor'

vi.mock('../api/profile', () => ({
  getLanguages: vi.fn(),
}))

vi.mock('../api/tutor', async () => ({
  // TutorTurnError is a real class the page branches on with instanceof —
  // stubbing it as undefined made every error path throw instead of render.
  ...(await vi.importActual<typeof import('../api/tutor')>('../api/tutor')),
  getTutorStatus: vi.fn(),
  getTutorSessions: vi.fn(() => Promise.resolve([])),
  sendTutorMessage: vi.fn(),
  streamTutorMessage: vi.fn(),
  endTutorSession: vi.fn(),
  resolveMasterySuggestion: vi.fn(),
}))

vi.mock('../api/billing', async (orig) => ({
  ...(await orig()),
  createCheckout: vi.fn(),
  createTopupCheckout: vi.fn(),
  // Monetization ON by default so the upsell paths are exercisable; the
  // master-switch test overrides this to false.
  getPlanPrices: vi.fn(() =>
    Promise.resolve({
      single: null, all: null, custom: null, monetization: true,
      topup: { amount_cents: 500, currency: 'usd', messages: 200 },
    })),
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
  resolveMasterySuggestion,
  TutorTurnError,
} from '../api/tutor'
import { createCheckout, createTopupCheckout, getPlanPrices } from '../api/billing'

const mockGetLanguages = getLanguages as ReturnType<typeof vi.fn>
const mockGetTutorStatus = getTutorStatus as ReturnType<typeof vi.fn>
const mockSendTutorMessage = sendTutorMessage as ReturnType<typeof vi.fn>
const mockStreamTutorMessage = streamTutorMessage as ReturnType<typeof vi.fn>
const mockEndTutorSession = endTutorSession as ReturnType<typeof vi.fn>
const mockCreateCheckout = createCheckout as ReturnType<typeof vi.fn>
const mockCreateTopupCheckout = createTopupCheckout as ReturnType<typeof vi.fn>
const mockGetPlanPrices = getPlanPrices as ReturnType<typeof vi.fn>

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

  it('free tier chats with the usage meter — percentages, never counts', async () => {
    // Claude-style (owner): usage is a percentage of the monthly pool with a
    // reset date — raw message counts and model plumbing stay hidden.
    mockGetTutorStatus.mockResolvedValue(statusWith(freeAllowance(14)))
    renderPage()
    expect(await screen.findByText(/I’m your Turkish tutor/i)).toBeDefined()
    const meter = screen.getByTestId('tutor-allowance')
    expect(meter.textContent).toContain('Monthly usage')
    expect(meter.textContent).toContain('30% used') // 6 of 20 drawn
    expect(meter.textContent).not.toContain('messages')
    expect(meter.textContent).toContain('flat monthly') // the add-AI line
    expect(screen.getByPlaceholderText(/message your tutor/i)).toBeDefined()
  })

  it('plus tier shows the usage meter without an upsell', async () => {
    mockGetTutorStatus.mockResolvedValue(statusWith(plusAllowance(93)))
    renderPage()
    const meter = await screen.findByTestId('tutor-allowance')
    expect(meter.textContent).toContain('7% used') // 7 of 100 drawn
    expect(meter.textContent).toContain('Resets')
    expect(meter.textContent).not.toContain('flat monthly')
  })

  it('exhausted free tier blocks input and offers the flat-price AI add-on', async () => {
    mockGetTutorStatus.mockResolvedValue(statusWith(freeAllowance(0)))
    mockCreateCheckout.mockResolvedValue({ granted: false, url: 'https://checkout.stripe/x' })
    const original = window.location
    Object.defineProperty(window, 'location', { value: { href: '' }, writable: true })
    renderPage()

    const panel = await screen.findByTestId('tutor-exhausted')
    expect(panel.textContent).toContain('all of this month’s usage')
    expect(panel.textContent).toContain('flat monthly')
    expect(screen.queryByPlaceholderText(/message your tutor/i)).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: /add ai for turkish/i }))
    await waitFor(() => {
      expect(mockCreateCheckout).toHaveBeenCalledWith('lang-tr')
      expect(window.location.href).toBe('https://checkout.stripe/x')
    })
    Object.defineProperty(window, 'location', { value: original, writable: true })
  })

  it('exhausted plus tier explains the monthly reset without an upsell', async () => {
    mockGetTutorStatus.mockResolvedValue(statusWith(plusAllowance(0)))
    renderPage()
    const panel = await screen.findByTestId('tutor-exhausted')
    expect(panel.textContent).toContain('this month’s usage limit')
    expect(panel.textContent).toContain('price never changes')
    expect(screen.queryByRole('button', { name: /add ai/i })).toBeNull()
  })

  it('a top-up buys this month’s messages from the exhausted panel', async () => {
    mockGetTutorStatus.mockResolvedValue(statusWith(freeAllowance(0)))
    mockCreateTopupCheckout.mockResolvedValue({
      granted: false, url: 'https://checkout.stripe/topup',
    })
    const original = window.location
    Object.defineProperty(window, 'location', { value: { href: '' }, writable: true })
    renderPage()

    const button = await screen.findByTestId('tutor-topup')
    // The button names the deal: how many messages, this month, the price.
    expect(button.textContent).toContain('+200')
    expect(button.textContent).toContain('$5')
    fireEvent.click(button)
    await waitFor(() => {
      expect(mockCreateTopupCheckout).toHaveBeenCalled()
      expect(window.location.href).toBe('https://checkout.stripe/topup')
    })
    Object.defineProperty(window, 'location', { value: original, writable: true })
  })

  it('sells nothing anywhere while monetization is off', async () => {
    // The master switch (owner: money features stay off until the employer
    // clearance lands): no upsell under the meter, and the exhausted panel
    // states the reset date without a single purchase button.
    // Once, so the factory's monetization-on default returns for the
    // rest of the file (clearAllMocks keeps implementations).
    mockGetPlanPrices.mockResolvedValueOnce({
      single: null, all: null, custom: null, monetization: false, topup: null,
    })
    mockGetTutorStatus.mockResolvedValue(statusWith(freeAllowance(0)))
    renderPage()

    const panel = await screen.findByTestId('tutor-exhausted')
    expect(panel.textContent).toContain('It refreshes on')
    expect(panel.textContent).not.toContain('flat monthly')
    expect(screen.queryByTestId('tutor-topup')).toBeNull()
    expect(screen.queryByRole('button', { name: /add ai/i })).toBeNull()
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
    // The reply's fresh allowance re-renders the meter: 7 of 20 drawn -> 35%.
    expect(screen.getByTestId('tutor-allowance').textContent).toContain(
      '35% used',
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

const mockResolveMastery = resolveMasterySuggestion as ReturnType<typeof vi.fn>

describe('TutorPage mastery stars', () => {
  const star = {
    id: 's-1',
    item: 'Locative case',
    kind: 'grammar' as const,
    evidence: 'You used -da/-de correctly three times unprompted.',
    created_at: '2026-07-16T00:00:00+00:00',
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockGetLanguages.mockResolvedValue([turkish])
    mockEndTutorSession.mockResolvedValue(undefined)
    mockStreamTutorMessage.mockRejectedValue(new Error('no stream in jsdom'))
  })

  it('renders pending stars with the item, evidence, and both verdicts', async () => {
    mockGetTutorStatus.mockResolvedValue({
      ...statusWith(unlimited),
      mastery_suggestions: [star],
    })
    renderPage()
    const panel = await screen.findByTestId('mastery-suggestions')
    expect(panel.textContent).toContain('Locative case')
    expect(panel.textContent).toContain('three times unprompted')
    expect(screen.getByRole('button', { name: /i know it/i })).toBeDefined()
    expect(screen.getByRole('button', { name: /keep drilling/i })).toBeDefined()
  })

  it('accepting a star calls the resolve endpoint with accept', async () => {
    mockGetTutorStatus.mockResolvedValue({
      ...statusWith(unlimited),
      mastery_suggestions: [star],
    })
    mockResolveMastery.mockResolvedValue({ action: 'accept', advanced: true })
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: /i know it/i }))
    await waitFor(() =>
      expect(mockResolveMastery).toHaveBeenCalledWith('s-1', 'accept'),
    )
  })

  it('dismissing a star calls the resolve endpoint with dismiss', async () => {
    mockGetTutorStatus.mockResolvedValue({
      ...statusWith(unlimited),
      mastery_suggestions: [star],
    })
    mockResolveMastery.mockResolvedValue({ action: 'dismiss', advanced: false })
    renderPage()
    fireEvent.click(await screen.findByRole('button', { name: /keep drilling/i }))
    await waitFor(() =>
      expect(mockResolveMastery).toHaveBeenCalledWith('s-1', 'dismiss'),
    )
  })

  it('shows no panel when there are no pending stars', async () => {
    mockGetTutorStatus.mockResolvedValue(statusWith(unlimited))
    renderPage()
    await screen.findByText(/I’m your Turkish tutor/i)
    expect(screen.queryByTestId('mastery-suggestions')).toBeNull()
  })
})

describe('a turn that never comes back', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetLanguages.mockResolvedValue([turkish])
    mockEndTutorSession.mockResolvedValue(undefined)
    mockGetTutorStatus.mockResolvedValue(statusWith(unlimited))
  })

  const sendSomething = async () => {
    const input = await screen.findByPlaceholderText(/message your tutor/i)
    fireEvent.change(input, { target: { value: "that's all for now" } })
    fireEvent.keyDown(input, { key: 'Enter' })
  }

  it('offers a way out while the tutor is thinking', async () => {
    // The server pings every 10s to survive the gateway timeout, which means
    // a stalled turn looks exactly like a slow one — forever. Leaving the
    // page was the only escape.
    mockStreamTutorMessage.mockReturnValue(new Promise(() => {}))
    renderPage()
    await sendSomething()

    expect(await screen.findByText(/thinking/i)).toBeDefined()
    expect(screen.getByRole('button', { name: /^stop$/i })).toBeDefined()
  })

  it('gives the typed message back instead of swallowing it', async () => {
    mockStreamTutorMessage.mockRejectedValue(
      new TutorTurnError('The tutor stopped responding — try again.'),
    )
    renderPage()
    await sendSomething()

    // The message goes back in the box: it was never answered, and retyping
    // a paragraph you already wrote is the wrong thing to ask of anyone.
    await waitFor(() => {
      const input = screen.getByPlaceholderText(
        /message your tutor/i,
      ) as HTMLTextAreaElement | HTMLInputElement
      expect(input.value).toBe("that's all for now")
    })
    expect(await screen.findByRole('alert')).toBeDefined()
  })

  it('does not retry a turn the server already failed', async () => {
    // A TutorTurnError is the server's verdict. Falling back to the plain
    // endpoint spends a second billed model call to be told the same thing.
    mockStreamTutorMessage.mockRejectedValue(new TutorTurnError('nope'))
    renderPage()
    await sendSomething()

    await waitFor(() => expect(mockStreamTutorMessage).toHaveBeenCalled())
    expect(mockSendTutorMessage).not.toHaveBeenCalled()
  })

  it('still falls back when the transport itself is unavailable', async () => {
    // The old behaviour has to survive: a plain transport failure (no SSE in
    // this browser) should still reach the non-streaming endpoint.
    mockStreamTutorMessage.mockRejectedValue(new Error('no stream in jsdom'))
    mockSendTutorMessage.mockResolvedValue({ reply: 'Görüşürüz!', allowance: null })
    renderPage()
    await sendSomething()

    expect(await screen.findByText(/Görüşürüz/)).toBeDefined()
  })
})

describe('reaching End session in a long conversation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetLanguages.mockResolvedValue([turkish])
    mockEndTutorSession.mockResolvedValue(undefined)
    mockGetTutorStatus.mockResolvedValue(statusWith(unlimited))
    mockStreamTutorMessage.mockRejectedValue(new Error('no stream in jsdom'))
    mockSendTutorMessage.mockResolvedValue({ reply: 'Tamam.', allowance: null })
  })

  it('offers jump-to-top and jump-to-bottom once there is a conversation', async () => {
    // "End session" is in the header. In a long chat that is a lot of manual
    // scrolling away from where you are typing.
    renderPage()
    expect(screen.queryByRole('button', { name: /scroll to top/i })).toBeNull()

    const input = await screen.findByPlaceholderText(/message your tutor/i)
    fireEvent.change(input, { target: { value: 'Merhaba' } })
    fireEvent.keyDown(input, { key: 'Enter' })

    expect(
      await screen.findByRole('button', { name: /scroll to top/i }),
    ).toBeDefined()
    expect(screen.getByRole('button', { name: /scroll to bottom/i })).toBeDefined()
  })

  /* The composer sits at the END of a `min-h-screen` column whose message
   * list is `flex-1 overflow-y-auto` with nothing capping its height — so
   * the list grows with the conversation instead of scrolling inside
   * itself, the document outgrows the viewport, and the entry box lands
   * under the fold with nothing on screen suggesting there is anywhere to
   * scroll to. Measured in Chromium before the fix: 1403px down a 800px
   * viewport.
   *
   * jsdom has no layout, so this pins the mechanism. `sticky bottom-0` in
   * particular, NOT a fixed height on the column: StaffBar is a sibling
   * above this page, so `h-screen` would sit a whole viewport below it and
   * push the composer under the fold by the bar's height — for staff only,
   * which is who reported this. */
  it('pins the composer to the viewport instead of the end of the page', async () => {
    mockGetTutorStatus.mockResolvedValue(statusWith(freeAllowance(14)))
    renderPage()
    const input = await screen.findByPlaceholderText(/message your tutor/i)
    const form = input.closest('form')
    expect(form).not.toBeNull()
    expect(form!.className).toContain('sticky')
    expect(form!.className).toContain('bottom-0')
  })

  it('gives the pinned composer an opaque background', async () => {
    // Messages scroll underneath it; a transparent bar reads through.
    mockGetTutorStatus.mockResolvedValue(statusWith(freeAllowance(14)))
    renderPage()
    const input = await screen.findByPlaceholderText(/message your tutor/i)
    expect(input.closest('form')!.className).toMatch(/bg-\w/)
  })
})
