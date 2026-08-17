import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import SpeakPage from '../features/speak/SpeakPage'
import type { SpeakConversationPrefs } from '../stores/prefsStore'

/**
 * Speak's conversation options (owner: "the audio never auto-speaks for
 * users… create options that provide users real convo situations. Audio
 * output automatic or not. Audio response hidden or not… listen for the audio
 * input immediately and send for them when they stop for a bit").
 *
 * What these pin is the CHAIN, because each link is easy to get right alone
 * and the sequence is what makes it a conversation: the partner's line plays
 * by itself → the microphone opens only once that line has FINISHED (opening
 * it earlier records the partner) → the learner's pause ends the turn → the
 * transcript still gets shown, with a moment to stop it, before it sends.
 *
 * Everything the browser supplies is faked at the seam the page checks:
 * MediaRecorder, getUserMedia, AudioContext and HTMLMediaElement.play. A
 * course that can't be heard or a browser that can't measure silence must
 * fall back to the typed path, so those are pinned too.
 */

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (orig) => ({
  ...(await orig<typeof import('react-router-dom')>()),
  useNavigate: () => mockNavigate,
}))

/** The conversation prefs the page reads, mutable per test. */
let conversation: SpeakConversationPrefs = {
  autoSpeak: false, hideText: false, autoListen: false, autoSend: false,
}
const setConversation = vi.fn((patch: Partial<SpeakConversationPrefs>) => {
  conversation = { ...conversation, ...patch }
})

vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn((sel: (s: Record<string, unknown>) => unknown) =>
    sel({
      activeLanguageId: 'lang-es',
      speakConversation: conversation,
      setSpeakConversation: setConversation,
    }),
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
  transcribeTurn: vi.fn(),
  speakPartnerLine: vi.fn(),
}))

import {
  getSpeakStatus,
  sendSpeakTurn,
  speakPartnerLine,
  startSpeakSession,
  transcribeTurn,
} from '../api/speak'

const mockStatus = getSpeakStatus as ReturnType<typeof vi.fn>
const mockStart = startSpeakSession as ReturnType<typeof vi.fn>
const mockTurn = sendSpeakTurn as ReturnType<typeof vi.fn>
const mockTranscribe = transcribeTurn as ReturnType<typeof vi.fn>
const mockSay = speakPartnerLine as ReturnType<typeof vi.fn>

const allowance = {
  tier: 'plus', unlimited: false, entitled: true, limit: 100, used: 3,
  remaining: 97, resets_at: null,
}

const OPENING = '¿Qué tal el viaje?'

// ── Browser fakes ──────────────────────────────────────────────────────────

class FakeRecorder {
  ondataavailable: ((e: { data: Blob }) => void) | null = null
  onstop: (() => void) | null = null
  mimeType = 'audio/webm'
  start() {
    this.ondataavailable?.({ data: new Blob(['x'], { type: this.mimeType }) })
  }
  stop() {
    this.onstop?.()
  }
}

/** How many 100ms ticks of speech the fake microphone still has to give. */
let loudTicks = 0

class FakeAudioContext {
  createMediaStreamSource() {
    return { connect: () => {}, disconnect: () => {} }
  }
  createAnalyser() {
    return {
      fftSize: 8,
      getByteTimeDomainData: (array: Uint8Array) => {
        const loud = loudTicks > 0
        if (loud) loudTicks -= 1
        // 40/128 ≈ 0.31 — comfortably over the adaptive gate's ceiling.
        array.fill(loud ? 168 : 128)
      },
    }
  }
  close() {
    return Promise.resolve()
  }
}

function fakeBrowser({ audioContext = true } = {}) {
  Object.defineProperty(globalThis.navigator, 'mediaDevices', {
    configurable: true,
    value: { getUserMedia: vi.fn(async () => ({ getTracks: () => [{ stop: vi.fn() }] })) },
  })
  ;(globalThis as unknown as { MediaRecorder: unknown }).MediaRecorder =
    FakeRecorder
  const w = globalThis.window as unknown as { AudioContext?: unknown }
  if (audioContext) w.AudioContext = FakeAudioContext
  else delete w.AudioContext

  // jsdom throws "Not implemented" from play/pause. Resolve, then report the
  // clip as finished, which is the event the page waits on before listening.
  HTMLMediaElement.prototype.play = vi.fn(function (this: HTMLMediaElement) {
    setTimeout(() => this.dispatchEvent(new Event('ended')), 0)
    return Promise.resolve()
  })
  HTMLMediaElement.prototype.pause = vi.fn()
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

/** Into a live conversation that opens with the partner speaking first. */
async function startTalking(
  prefs: Partial<SpeakConversationPrefs>,
  speech = { listen: true, speak: true },
) {
  conversation = {
    autoSpeak: false, hideText: false, autoListen: false, autoSend: false,
    ...prefs,
  }
  mockStatus.mockResolvedValue({
    available: true, allowance, sessions: [], speech,
  })
  mockStart.mockResolvedValue({
    session_id: 's1', mode: 'flow', topic: null, opening: OPENING,
  })
  mockSay.mockResolvedValue('BASE64AUDIO')
  renderPage()
  fireEvent.click(await screen.findByTestId('speak-start'))
  await screen.findByTestId('speak-input')
}

describe('Speak — conversation options', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    loudTicks = 0
    fakeBrowser()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('leaves everything manual by default — no clip is fetched unasked', async () => {
    // The whole point of the options is that they are options. With none of
    // them on, the page behaves exactly as it did before they existed.
    await startTalking({})
    expect(screen.getByText(OPENING)).toBeInTheDocument()
    await waitFor(() => expect(mockSay).not.toHaveBeenCalled())
    expect((navigator.mediaDevices.getUserMedia as ReturnType<typeof vi.fn>))
      .not.toHaveBeenCalled()
  })

  it('speaks the partner’s line by itself when asked to', async () => {
    await startTalking({ autoSpeak: true })
    await waitFor(() => expect(mockSay).toHaveBeenCalledWith('s1', 0, false))
  })

  it('withholds the words for listening practice, and shows them on request', async () => {
    await startTalking({ autoSpeak: true, hideText: true })
    expect(screen.queryByText(OPENING)).not.toBeInTheDocument()

    fireEvent.click(await screen.findByTestId('speak-reveal-0'))
    expect(screen.getByText(OPENING)).toBeInTheDocument()
  })

  it('opens the microphone only after the partner has finished speaking', async () => {
    // Ordering is the substance: arming the recorder while the clip is still
    // playing records the partner's own voice back into the transcript.
    await startTalking({ autoSpeak: true, autoListen: true })
    await waitFor(() => expect(mockSay).toHaveBeenCalled())
    await waitFor(() =>
      expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalled(),
    )
    await waitFor(() =>
      expect(screen.getByTestId('speak-mic')).toHaveAttribute(
        'aria-pressed', 'true',
      ),
    )
  })

  it('sends the turn when the learner stops talking, after a moment to stop it', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    mockTranscribe.mockResolvedValue('Muy bien, gracias')
    mockTurn.mockResolvedValue({
      reply: 'Me alegro.', turn_index: 1, allowance,
    })
    await startTalking({ autoSpeak: true, autoListen: true, autoSend: true })
    await waitFor(() =>
      expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalled(),
    )

    // 800ms of speech, then quiet: past minSpeechMs, then past silenceMs.
    loudTicks = 8
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000)
    })

    // The transcript is SHOWN — not swallowed — and then goes on its own.
    const pending = await screen.findByTestId('speak-pending')
    expect(pending).toHaveTextContent('Muy bien, gracias')
    expect(mockTurn).not.toHaveBeenCalled()

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2100)
    })
    // The measured speaking time rides along with the turn — that is what
    // the summary's speaking share counts, and it must not be lost just
    // because nobody pressed Send.
    await waitFor(() => expect(mockTurn).toHaveBeenCalledTimes(1))
    const [session, text, audioMs] = mockTurn.mock.calls[0]
    expect([session, text]).toEqual(['s1', 'Muy bien, gracias'])
    expect(audioMs).toBeGreaterThan(0)
  })

  it('cancelling a hands-free turn hands the words back for editing', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    mockTranscribe.mockResolvedValue('Muy bein, gracais')
    await startTalking({ autoListen: true, autoSend: true })
    await waitFor(() =>
      expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalled(),
    )

    loudTicks = 8
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000)
    })
    fireEvent.click(await screen.findByTestId('speak-pending-cancel'))

    // Nothing sent, and the misheard text is in the box to be fixed.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000)
    })
    expect(mockTurn).not.toHaveBeenCalled()
    expect(screen.getByTestId('speak-input')).toHaveValue('Muy bein, gracais')
  })

  it('says nothing to the provider when the room was empty', async () => {
    // 'nothing' costs a transcription request and buys no words, so the
    // recording is dropped and the learner is told the microphone is idle.
    vi.useFakeTimers({ shouldAdvanceTime: true })
    await startTalking({ autoListen: true, autoSend: true })
    await waitFor(() =>
      expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalled(),
    )

    loudTicks = 0
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000)
    })
    expect(mockTranscribe).not.toHaveBeenCalled()
    expect(await screen.findByText(/didn’t hear anything/i)).toBeInTheDocument()
  })

  it('refuses to offer auto-send in a browser that cannot measure silence', async () => {
    // Latin-era browsers and some WebViews have no AudioContext. The switch
    // is shown disabled with the reason rather than doing nothing quietly.
    fakeBrowser({ audioContext: false })
    conversation = {
      autoSpeak: false, hideText: false, autoListen: false, autoSend: true,
    }
    mockStatus.mockResolvedValue({
      available: true, allowance, sessions: [],
      speech: { listen: true, speak: true },
    })
    renderPage()
    await screen.findByTestId('speak-options')

    const row = screen.getByTestId('speak-opt-autoSend')
    expect(row.querySelector('input')).toBeDisabled()
    expect(row).toHaveTextContent(/can’t tell when you stop talking/i)
  })

  it('offers no voice options at all for a course with no voice', async () => {
    mockStatus.mockResolvedValue({
      available: true, allowance, sessions: [],
      speech: { listen: true, speak: false },
    })
    renderPage()
    await screen.findByTestId('speak-options')

    expect(
      screen.getByTestId('speak-opt-autoSpeak').querySelector('input'),
    ).toBeDisabled()
    expect(
      screen.getByTestId('speak-opt-hideText').querySelector('input'),
    ).toBeDisabled()
    // …and the microphone half is untouched by the missing voice.
    expect(
      screen.getByTestId('speak-opt-autoListen').querySelector('input'),
    ).not.toBeDisabled()
  })

  it('the hands-free button turns on all three at once', async () => {
    mockStatus.mockResolvedValue({
      available: true, allowance, sessions: [],
      speech: { listen: true, speak: true },
    })
    conversation = {
      autoSpeak: false, hideText: false, autoListen: false, autoSend: false,
    }
    renderPage()
    fireEvent.click(await screen.findByTestId('speak-hands-free'))

    expect(setConversation).toHaveBeenCalledWith({
      autoSpeak: true, autoListen: true, autoSend: true,
    })
  })
})
