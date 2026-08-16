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
  transcribeTurn: vi.fn(),
  speakPartnerLine: vi.fn(),
}))

vi.mock('../api/notes', async (orig) => ({
  ...(await orig<typeof import('../api/notes')>()),
  createPersonalCard: vi.fn(),
}))

import {
  endSpeakSession,
  getSpeakStatus,
  sendSpeakTurn,
  speakPartnerLine,
  startSpeakSession,
  transcribeTurn,
} from '../api/speak'
import { createPersonalCard } from '../api/notes'

const mockAddCard = createPersonalCard as ReturnType<typeof vi.fn>

const mockStatus = getSpeakStatus as ReturnType<typeof vi.fn>
const mockStart = startSpeakSession as ReturnType<typeof vi.fn>
const mockTurn = sendSpeakTurn as ReturnType<typeof vi.fn>
const mockEnd = endSpeakSession as ReturnType<typeof vi.fn>
const mockTranscribe = transcribeTurn as ReturnType<typeof vi.fn>
const mockSay = speakPartnerLine as ReturnType<typeof vi.fn>

/** What the server reports about this course. Both halves default OFF, so a
 * test that wants a microphone has to say so — the typed path is the one
 * that must keep working everywhere. */
const NO_SPEECH = { listen: false, speak: false }

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

function fullSummary() {
  return {
    groups: [{
      label: 'Subject pronouns',
      note: 'Spanish drops these unless contrasting.',
      examples: ['yo quiero → quiero'],
      count: 3,
      card: {
        sentence: 'Quiero un café con leche.',
        answer: 'Quiero',
        translation: 'I want a coffee with milk.',
      },
    }],
    vocabulary: [{
      term: 'para llevar',
      meaning: 'to take away',
      example: '¿Para tomar aquí o para llevar?',
    }],
    stats: { turns: 4, error_count: 3, types: { pronoun: 3 } },
  }
}

/** Get through the topic screen and into a live conversation. */
async function startTalking(speech = NO_SPEECH) {
  mockStatus.mockResolvedValue({
    available: true, allowance, sessions: [], speech,
  })
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
      available: false, allowance: null, sessions: [], speech: NO_SPEECH,
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
    mockEnd.mockResolvedValue({ already_ended: false, summary: fullSummary() })

    fireEvent.click(screen.getByTestId('speak-done'))

    await screen.findByTestId('speak-summary')
    expect(screen.getByText('Subject pronouns')).toBeInTheDocument()
    expect(screen.getByText('yo quiero → quiero')).toBeInTheDocument()
    expect(screen.getByText('para llevar')).toBeInTheDocument()
  })

  it('adds nothing until the learner asks', async () => {
    // A summary that quietly filled their reviews would make them wary of
    // finishing a session at all.
    await startTalking()
    mockEnd.mockResolvedValue({ already_ended: false, summary: fullSummary() })
    fireEvent.click(screen.getByTestId('speak-done'))
    await screen.findByTestId('speak-summary')

    expect(mockAddCard).not.toHaveBeenCalled()
    // …and there's nowhere to practise until something has been kept.
    expect(screen.queryByTestId('speak-practise')).not.toBeInTheDocument()
  })

  it('keeps a grammar card built from the learner’s own sentence', async () => {
    await startTalking()
    mockEnd.mockResolvedValue({ already_ended: false, summary: fullSummary() })
    mockAddCard.mockResolvedValue({ id: 'c1', sentence: '…', deck_name: null })
    fireEvent.click(screen.getByTestId('speak-done'))
    await screen.findByTestId('speak-summary')

    fireEvent.click(screen.getByTestId('speak-add-group-0'))

    await waitFor(() => expect(mockAddCard).toHaveBeenCalledTimes(1))
    expect(mockAddCard).toHaveBeenCalledWith(
      expect.objectContaining({
        sentence: 'Quiero un café con leche.',
        answer: 'Quiero',
        source: 'speak',
      }),
    )
    await screen.findByTestId('speak-practise')
  })

  it('keeps a word in the sentence they met it in', async () => {
    await startTalking()
    mockEnd.mockResolvedValue({ already_ended: false, summary: fullSummary() })
    mockAddCard.mockResolvedValue({ id: 'c2', sentence: '…', deck_name: null })
    fireEvent.click(screen.getByTestId('speak-done'))
    await screen.findByTestId('speak-summary')

    fireEvent.click(screen.getByTestId('speak-add-word-0'))

    await waitFor(() =>
      expect(mockAddCard).toHaveBeenCalledWith(
        expect.objectContaining({
          sentence: '¿Para tomar aquí o para llevar?',
          answer: 'para llevar',
          gloss: 'to take away',
          source: 'speak',
        }),
      ),
    )
  })

  it('offers no Add button for a group with no usable card', async () => {
    // The mechanical fallback grouping records the phrase that was wrong,
    // not the sentence around it, so there is nothing to blank out.
    await startTalking()
    mockEnd.mockResolvedValue({
      already_ended: false,
      summary: {
        ...fullSummary(),
        groups: [{
          label: 'Gender', note: 'la, not el.',
          examples: ['el casa → la casa'], count: 1, card: null,
        }],
      },
    })
    fireEvent.click(screen.getByTestId('speak-done'))
    await screen.findByTestId('speak-summary')

    expect(screen.getByText('Gender')).toBeInTheDocument()
    expect(screen.queryByTestId('speak-add-group-0')).not.toBeInTheDocument()
  })

  it('says so and lets them retry when a card fails to save', async () => {
    await startTalking()
    mockEnd.mockResolvedValue({ already_ended: false, summary: fullSummary() })
    mockAddCard.mockRejectedValue(new Error('nope'))
    fireEvent.click(screen.getByTestId('speak-done'))
    await screen.findByTestId('speak-summary')

    fireEvent.click(screen.getByTestId('speak-add-group-0'))

    await screen.findByText(/Try again/i)
    expect(screen.queryByTestId('speak-practise')).not.toBeInTheDocument()
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

describe('SpeakPage — choosing when to be corrected', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('offers both modes before the session starts', async () => {
    mockStatus.mockResolvedValue({
      available: true, allowance, sessions: [], speech: NO_SPEECH,
    })
    renderPage()
    await screen.findByTestId('speak-start')

    expect(screen.getByTestId('speak-mode-coach')).toBeInTheDocument()
    expect(screen.getByTestId('speak-mode-flow')).toBeInTheDocument()
    expect(screen.getByText(/One correction as you go/i)).toBeInTheDocument()
    expect(screen.getByText(/Corrections at the end/i)).toBeInTheDocument()
  })

  it('starts in flow unless coach is chosen', async () => {
    mockStatus.mockResolvedValue({
      available: true, allowance, sessions: [], speech: NO_SPEECH,
    })
    mockStart.mockResolvedValue({ session_id: 's1', mode: 'flow', topic: null })
    renderPage()
    fireEvent.click(await screen.findByTestId('speak-start'))

    await waitFor(() => expect(mockStart).toHaveBeenCalled())
    expect(mockStart.mock.calls[0][3]).toBe('flow')
  })

  it('passes coach through when the learner picks it', async () => {
    mockStatus.mockResolvedValue({
      available: true, allowance, sessions: [], speech: NO_SPEECH,
    })
    mockStart.mockResolvedValue({ session_id: 's1', mode: 'coach', topic: null })
    renderPage()
    await screen.findByTestId('speak-start')

    fireEvent.click(screen.getByTestId('speak-mode-coach').querySelector('input')!)
    fireEvent.click(screen.getByTestId('speak-start'))

    await waitFor(() => expect(mockStart).toHaveBeenCalled())
    expect(mockStart.mock.calls[0][3]).toBe('coach')
  })

  it('shows one correction, never a list', async () => {
    // A learner corrected three times per turn stops talking.
    mockStatus.mockResolvedValue({
      available: true, allowance, sessions: [], speech: NO_SPEECH,
    })
    mockStart.mockResolvedValue({ session_id: 's1', mode: 'coach', topic: null })
    renderPage()
    fireEvent.click(await screen.findByTestId('speak-start'))
    await screen.findByTestId('speak-input')

    mockTurn.mockResolvedValue({
      reply: '¿Para tomar aquí?',
      turn_index: 0,
      allowance,
      correction: {
        type: 'pronoun',
        learner_said: 'Yo quiero',
        should_be: 'Quiero',
        note: 'Spanish drops the subject pronoun.',
      },
    })
    fireEvent.change(screen.getByTestId('speak-input'), {
      target: { value: 'Yo quiero un café' },
    })
    fireEvent.click(screen.getByTestId('speak-send'))

    await screen.findByTestId('speak-correction-0')
    expect(screen.getByText(/Yo quiero → Quiero/)).toBeInTheDocument()
    expect(
      screen.getByText('Spanish drops the subject pronoun.'),
    ).toBeInTheDocument()
  })

  it('shows nothing mid-session in flow mode', async () => {
    mockStatus.mockResolvedValue({
      available: true, allowance, sessions: [], speech: NO_SPEECH,
    })
    mockStart.mockResolvedValue({ session_id: 's1', mode: 'flow', topic: null })
    renderPage()
    fireEvent.click(await screen.findByTestId('speak-start'))
    await screen.findByTestId('speak-input')

    // Flow sends no correction key at all.
    mockTurn.mockResolvedValue({
      reply: '¿Para tomar aquí?', turn_index: 0, allowance,
    })
    fireEvent.change(screen.getByTestId('speak-input'), {
      target: { value: 'Yo quiero un café' },
    })
    fireEvent.click(screen.getByTestId('speak-send'))

    await screen.findByText('¿Para tomar aquí?')
    expect(screen.queryByTestId('speak-correction-0')).not.toBeInTheDocument()
  })

  it('says nothing when a coached turn was clean', async () => {
    mockStatus.mockResolvedValue({
      available: true, allowance, sessions: [], speech: NO_SPEECH,
    })
    mockStart.mockResolvedValue({ session_id: 's1', mode: 'coach', topic: null })
    renderPage()
    fireEvent.click(await screen.findByTestId('speak-start'))
    await screen.findByTestId('speak-input')

    mockTurn.mockResolvedValue({
      reply: 'Claro.', turn_index: 0, allowance, correction: null,
    })
    fireEvent.change(screen.getByTestId('speak-input'), {
      target: { value: 'Quiero un café' },
    })
    fireEvent.click(screen.getByTestId('speak-send'))

    await screen.findByText('Claro.')
    expect(screen.queryByTestId('speak-correction-0')).not.toBeInTheDocument()
  })
})

/**
 * Stage 2 — speech (docs/plans/speak.md).
 *
 * The rule under all of these: the typed path must keep working
 * everywhere, and the microphone appears only where BOTH the browser and
 * the course can support it. A dead mic button on a Latin course is worse
 * than no mic button, because the learner presses it.
 */
class FakeRecorder {
  static supported: string[] = ['audio/webm;codecs=opus']
  static isTypeSupported = (t: string) => FakeRecorder.supported.includes(t)
  ondataavailable: ((e: { data: Blob }) => void) | null = null
  onstop: (() => void) | null = null
  mimeType: string
  constructor(_stream: unknown, opts?: { mimeType?: string }) {
    this.mimeType = opts?.mimeType ?? 'audio/webm'
  }
  start() {
    this.ondataavailable?.({ data: new Blob(['x'], { type: this.mimeType }) })
  }
  stop() {
    this.onstop?.()
  }
}

function grantMicrophone(granted = true) {
  const track = { stop: vi.fn() }
  Object.defineProperty(globalThis.navigator, 'mediaDevices', {
    configurable: true,
    value: {
      getUserMedia: granted
        ? vi.fn(async () => ({ getTracks: () => [track] }))
        : vi.fn(async () => {
            const err = new Error('no') as Error & { name: string }
            err.name = 'NotAllowedError'
            throw err
          }),
    },
  })
  ;(globalThis as unknown as { MediaRecorder: unknown }).MediaRecorder =
    FakeRecorder
  return track
}

describe('SpeakPage — speech', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    grantMicrophone()
  })

  it('offers no microphone for a language that cannot be heard', async () => {
    // Latin, Māori, Yoruba. The browser is perfectly capable; the course
    // has no recognizer, and that is permanent rather than a stopgap — so
    // the page says so on the way in rather than showing a dead button.
    mockStatus.mockResolvedValue({
      available: true, allowance, sessions: [],
      speech: { listen: false, speak: true },
    })
    mockStart.mockResolvedValue({ session_id: 's1', mode: 'flow', topic: null })
    renderPage()
    await screen.findByTestId('speak-no-listen')
    fireEvent.click(screen.getByTestId('speak-start'))
    await screen.findByTestId('speak-input')
    expect(screen.queryByTestId('speak-mic')).not.toBeInTheDocument()
  })

  it('offers no microphone when the browser cannot record', async () => {
    // Same page, same course, no MediaRecorder — an old browser, or an
    // http:// origin where getUserMedia is simply absent.
    delete (globalThis as unknown as { MediaRecorder?: unknown }).MediaRecorder
    await startTalking({ listen: true, speak: true })
    expect(screen.queryByTestId('speak-mic')).not.toBeInTheDocument()
    // …and the typed path is untouched.
    expect(screen.getByTestId('speak-input')).toBeInTheDocument()
  })

  it('puts the transcript in the box instead of sending it', async () => {
    // The load-bearing decision. ASR mishears an accented beginner, and
    // being corrected for a word you did not say is the fastest way to
    // stop trusting the feature — so the learner reads and fixes it first.
    await startTalking({ listen: true, speak: false })
    mockTranscribe.mockResolvedValue('Quiero un café con leche')

    fireEvent.click(screen.getByTestId('speak-mic'))
    await waitFor(() =>
      expect(screen.getByTestId('speak-mic')).toHaveAttribute(
        'aria-pressed', 'true',
      ),
    )
    fireEvent.click(screen.getByTestId('speak-mic'))

    await waitFor(() =>
      expect(screen.getByTestId('speak-input')).toHaveValue(
        'Quiero un café con leche',
      ),
    )
    expect(mockTurn).not.toHaveBeenCalled()
    await screen.findByTestId('speak-transcript-note')
  })

  it('sends how long they spoke, and nothing when they typed', async () => {
    await startTalking({ listen: true, speak: false })
    mockTranscribe.mockResolvedValue('Hola')
    mockTurn.mockResolvedValue({
      reply: '¡Hola!', turn_index: 0, allowance,
    })

    fireEvent.click(screen.getByTestId('speak-mic'))
    await waitFor(() =>
      expect(screen.getByTestId('speak-mic')).toHaveAttribute(
        'aria-pressed', 'true',
      ),
    )
    fireEvent.click(screen.getByTestId('speak-mic'))
    await waitFor(() =>
      expect(screen.getByTestId('speak-input')).toHaveValue('Hola'),
    )
    fireEvent.click(screen.getByTestId('speak-send'))
    await waitFor(() => expect(mockTurn).toHaveBeenCalled())
    expect(typeof mockTurn.mock.calls[0][2]).toBe('number')

    // A typed turn carries no duration at all — the summary's speaking
    // share is a measurement, not an estimate from character counts.
    fireEvent.change(screen.getByTestId('speak-input'), {
      target: { value: 'Otra vez' },
    })
    fireEvent.click(screen.getByTestId('speak-send'))
    await waitFor(() => expect(mockTurn).toHaveBeenCalledTimes(2))
    expect(mockTurn.mock.calls[1][2]).toBeUndefined()
  })

  it('says so when it heard nothing, and posts no turn', async () => {
    await startTalking({ listen: true, speak: false })
    mockTranscribe.mockResolvedValue('')
    fireEvent.click(screen.getByTestId('speak-mic'))
    await waitFor(() =>
      expect(screen.getByTestId('speak-mic')).toHaveAttribute(
        'aria-pressed', 'true',
      ),
    )
    fireEvent.click(screen.getByTestId('speak-mic'))
    await screen.findByText(/didn’t catch anything/i)
    expect(mockTurn).not.toHaveBeenCalled()
  })

  it('explains a blocked microphone instead of failing silently', async () => {
    grantMicrophone(false)
    await startTalking({ listen: true, speak: false })
    fireEvent.click(screen.getByTestId('speak-mic'))
    await screen.findByTestId('speak-mic-denied')
    expect(screen.getByTestId('speak-mic')).toHaveAttribute(
      'aria-pressed', 'false',
    )
  })

  it('states what happens to the recording before one is made', async () => {
    // A permission prompt is not consent. One plain line, in view, before
    // the first press.
    await startTalking({ listen: true, speak: false })
    expect(screen.getByTestId('speak-mic-state')).toHaveTextContent(
      /transcribed and discarded/i,
    )
  })

  it('replays the partner’s line, and again slower', async () => {
    // The control the plan argued hardest for: comprehension failure is
    // the commonest reason a conversation dies, and without a replay the
    // learner's only recovery is to quit.
    await startTalking({ listen: false, speak: true })
    mockTurn.mockResolvedValue({
      reply: '¿Para tomar aquí o para llevar?', turn_index: 0, allowance,
    })
    mockSay.mockResolvedValue('QUJD')
    fireEvent.change(screen.getByTestId('speak-input'), {
      target: { value: 'Un café' },
    })
    fireEvent.click(screen.getByTestId('speak-send'))

    const play = await screen.findByTestId('speak-play-0')
    fireEvent.click(play)
    await waitFor(() => expect(mockSay).toHaveBeenCalledWith('s1', 0, false))
    fireEvent.click(screen.getByTestId('speak-play-slow-0'))
    await waitFor(() => expect(mockSay).toHaveBeenCalledWith('s1', 0, true))
  })

  it('offers no replay for a language with no voice', async () => {
    await startTalking({ listen: true, speak: false })
    mockTurn.mockResolvedValue({ reply: 'Vale.', turn_index: 0, allowance })
    fireEvent.change(screen.getByTestId('speak-input'), {
      target: { value: 'Hola' },
    })
    fireEvent.click(screen.getByTestId('speak-send'))
    await screen.findByText('Vale.')
    expect(screen.queryByTestId('speak-play-0')).not.toBeInTheDocument()
  })
})
