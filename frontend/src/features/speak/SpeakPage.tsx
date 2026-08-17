import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  Check,
  Eye,
  Loader2,
  Mic,
  Send,
  Square,
  Volume2,
  X,
} from 'lucide-react'
import {
  endSpeakSession,
  getSpeakStatus,
  sendSpeakTurn,
  speakPartnerLine,
  startSpeakSession,
  transcribeTurn,
} from '../../api/speak'
import { recordingSupported, useRecorder } from './useRecorder'
import { canDetectSilence } from './silence'
import type { AutoStopReason } from './silence'
import type { SpeakError, SpeakMode, SpeakSummary } from '../../api/speak'
import type { TutorAllowance } from '../../api/tutor'
import type { SpeakConversationPrefs } from '../../stores/prefsStore'
import { createPersonalCard } from '../../api/notes'
import { getLanguages } from '../../api/profile'
import { usePrefsStore } from '../../stores/prefsStore'
import LanguageWrapper from '../../components/LanguageWrapper'
import SectionHeader from '../../components/SectionHeader'
import UsageMeter from '../../components/UsageMeter'

interface Exchange {
  /** Empty for the partner's opening line — nobody spoke before it. */
  learner: string
  partner: string
  /** Coach mode only, and at most one. */
  correction?: SpeakError | null
}

/**
 * How long a transcript sits on screen before a hands-free turn sends
 * itself. Short enough to feel automatic, long enough to catch "I didn't say
 * that" — the transcript-review decision from stage 2 survives as a grace
 * window rather than being deleted.
 */
export const AUTO_SEND_GRACE_MS = 2000

/** A one-sample silent clip, played on the Start tap purely to unlock the
 * audio element. iOS only lets a media element play programmatically once it
 * has played inside a real gesture, and Start is the last gesture before the
 * partner speaks. */
const SILENT_WAV =
  'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA='

const CONVERSATION_DEFAULTS: SpeakConversationPrefs = {
  autoSpeak: false,
  hideText: false,
  autoListen: false,
  autoSend: false,
}

/**
 * Speak (docs/plans/speak.md) — conversation practice.
 *
 * Stage 1: typed Flow mode. They talk, the partner answers, and nothing
 * interrupts. Every mistake is noticed server-side and held back until they
 * press Done, at which point the whole session is grouped into a handful of
 * things worth understanding.
 *
 * The deliberate absence here is a score. Counting turns and minutes is
 * fine; grading the conversation would turn a place to experiment into a
 * thing to game, and the learner would stop taking risks — which is the
 * only reason to practise speaking at all.
 */
export default function SpeakPage() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)

  const { data: languages = [] } = useQuery({
    queryKey: ['languages'],
    queryFn: getLanguages,
  })
  const language = languages.find((l) => l.id === activeLanguageId)

  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ['speak-status', activeLanguageId],
    queryFn: () => getSpeakStatus(activeLanguageId!),
    enabled: !!activeLanguageId,
    retry: false,
  })

  const [topic, setTopic] = useState('')
  const [mode, setMode] = useState<SpeakMode>('flow')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [exchanges, setExchanges] = useState<Exchange[]>([])
  const [draft, setDraft] = useState('')
  const [allowance, setAllowance] = useState<TutorAllowance | null>(null)
  const [summary, setSummary] = useState<SpeakSummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const endRef = useRef<HTMLDivElement>(null)

  // Speech. The recorder is a browser fact, `status.speech` is a server
  // fact, and the microphone needs both: a course Azure cannot transcribe
  // is as mute as a browser with no MediaRecorder.
  const canListen = recordingSupported() && !!status?.speech?.listen
  const canHear = !!status?.speech?.speak
  // Held from the recording that produced the current draft, so a turn
  // the learner edits before sending still reports the time they spoke.
  const [spokenMs, setSpokenMs] = useState<number | null>(null)

  // ── Conversation options (owner request) ──────────────────────────────
  // Four switches, each defaulting off, and each one only ON if the thing it
  // needs exists: no voice for this course means no auto-speak, no analyser
  // in this browser means no auto-send. A toggle that silently does nothing
  // is worse than one that isn't offered.
  const storedConversation = usePrefsStore((s) => s.speakConversation)
  const setConversation = usePrefsStore((s) => s.setSpeakConversation)
  const conv = { ...CONVERSATION_DEFAULTS, ...(storedConversation ?? {}) }
  const canAutoSend = canDetectSilence()
  const autoSpeak = conv.autoSpeak && canHear
  const maskText = conv.hideText && canHear
  const autoListen = conv.autoListen && canListen
  const autoSend = conv.autoSend && canListen && canAutoSend

  // Which partner lines the learner has asked to read, in a hidden-text
  // session. Reset with each conversation.
  const [revealed, setRevealed] = useState<Record<number, boolean>>({})
  // A transcript waiting out its grace window before it sends itself.
  const [pending, setPending] = useState<{ text: string; ms: number } | null>(
    null,
  )
  // Set when the browser refused to play audio we didn't ask a finger for.
  // The manual play buttons still work, so this is a note, not an error.
  const [autoplayBlocked, setAutoplayBlocked] = useState(false)
  // Synthesized clips, keyed by turn and pace. Auto-speak and the replay
  // buttons share it, so hearing a line again costs nothing.
  const clips = useRef(new Map<string, string>())
  const player = useRef<HTMLAudioElement | null>(null)
  // How many exchanges have already been spoken/armed, so a re-render never
  // plays the same line twice.
  const announced = useRef(0)
  // Read inside callbacks that outlive the render that made them.
  const flags = useRef({ autoSpeak, autoListen, autoSend })
  flags.current = { autoSpeak, autoListen, autoSend }

  const recorder = useRecorder({
    onAutoStop: autoSend ? (reason) => handleAutoStop(reason) : undefined,
  })

  useEffect(() => {
    if (status?.allowance) setAllowance(status.allowance)
  }, [status?.allowance])

  useEffect(() => {
    // Optional-called: scrollIntoView is absent in jsdom and on some older
    // mobile browsers, and failing to scroll must never take the page down
    // mid-conversation.
    endRef.current?.scrollIntoView?.({ behavior: 'smooth' })
  }, [exchanges.length])

  const start = useMutation({
    mutationFn: () =>
      startSpeakSession(activeLanguageId!, language!.code, topic.trim(), mode),
    onSuccess: (data) => {
      setSessionId(data.session_id)
      // "Leave it blank and your partner will start" — so when it did, the
      // conversation opens with its line rather than an empty screen.
      setExchanges(
        data.opening ? [{ learner: '', partner: data.opening }] : [],
      )
      setSummary(null)
      setError(null)
      // A new conversation starts with nothing spoken, nothing revealed and
      // no clips worth keeping — the turn indexes belong to the old session.
      announced.current = 0
      clips.current.clear()
      setRevealed({})
      setPending(null)
      setAutoplayBlocked(false)
    },
    onError: () => setError(t('speak.startFailed')),
  })

  /** One synthesized clip, fetched once and remembered. */
  async function getClip(turnIndex: number, slow: boolean): Promise<string> {
    const key = `${turnIndex}:${slow ? 1 : 0}`
    const cached = clips.current.get(key)
    if (cached) return cached
    const b64 = await speakPartnerLine(sessionId!, turnIndex, slow)
    clips.current.set(key, b64)
    return b64
  }

  /**
   * Unlock the audio element inside the Start tap.
   *
   * Mobile Safari will only play a media element programmatically after that
   * element has played once inside a real gesture. Start is the last gesture
   * before the partner speaks, so a one-sample silent clip is played here and
   * the same element carries every line afterwards. Failure is fine: the page
   * falls back to the manual play buttons and says so.
   */
  function primePlayer() {
    if (player.current) return
    try {
      const el = new Audio(SILENT_WAV)
      player.current = el
      void el.play()?.then?.(() => el.pause())?.catch?.(() => {})
    } catch {
      // No Audio in this environment; auto-speak degrades to the buttons.
    }
  }

  /** Speak one partner line and resolve when it has finished — false if the
   * browser wouldn't play it. Waiting for the END matters: arming the
   * microphone early would record the partner's own voice. */
  async function playLine(turnIndex: number): Promise<boolean> {
    try {
      const b64 = await getClip(turnIndex, false)
      const el = player.current ?? new Audio()
      player.current = el
      el.src = `data:audio/mpeg;base64,${b64}`
      await new Promise<void>((resolve, reject) => {
        el.onended = () => resolve()
        el.onerror = () => reject(new Error('playback'))
        const started = el.play() as Promise<void> | undefined
        started?.catch?.(reject)
      })
      return true
    } catch {
      return false
    }
  }

  /** Open the microphone for the learner's reply, if they asked for that. */
  function armListening() {
    if (!flags.current.autoListen) return
    if (recorder.recording || transcribe.isPending || turn.isPending) return
    setError(null)
    void recorder.start()
  }

  /**
   * The partner has just said something: read it out, then listen.
   *
   * Both halves are optional and independent, and the order is the point —
   * speaking first and listening after is what makes a hands-free session a
   * conversation instead of two things talking over each other.
   */
  async function announce(turnIndex: number) {
    if (flags.current.autoSpeak) {
      const played = await playLine(turnIndex)
      if (!played) setAutoplayBlocked(true)
    }
    armListening()
  }

  /**
   * The detector says the learner stopped. What that means depends on why.
   *
   * 'nothing' is an empty room: throw the recording away without calling the
   * provider, because an empty transcription costs money and buys nothing,
   * and say something rather than leaving the microphone light on.
   */
  function handleAutoStop(reason: AutoStopReason) {
    if (reason === 'nothing') {
      recorder.cancel()
      setError(t('speak.micStillThere'))
      return
    }
    transcribe.mutate()
  }

  /**
   * Stop recording, transcribe, and put the result in the draft box —
   * NOT straight into a turn.
   *
   * The transcript is shown for the learner to read and fix first. ASR
   * mishears an accented beginner, and being corrected for a word you did
   * not say is the fastest way to stop trusting the whole feature. It also
   * means the typed path and the spoken path converge on the same box, so
   * there is one Send and one thing to test.
   */
  const transcribe = useMutation({
    mutationFn: async () => {
      const recorded = await recorder.stop()
      if (!recorded) return null
      const text = await transcribeTurn(sessionId!, recorded.blob)
      return { text, ms: recorded.ms }
    },
    onSuccess: (result) => {
      if (!result || !result.text.trim()) {
        setError(t('speak.micHeardNothing'))
        return
      }
      setError(null)
      // Hands-free: the transcript still gets read, it just isn't waited on.
      // It goes up with a countdown and a Cancel, so "that isn't what I said"
      // remains a two-second decision instead of a lost one.
      if (flags.current.autoSend) {
        setPending({ text: result.text, ms: result.ms })
        return
      }
      setDraft(result.text)
      setSpokenMs(result.ms)
    },
    onError: () => setError(t('speak.micFailed')),
  })

  // The duration travels WITH the turn rather than being read out of state
  // inside the mutation. submit() clears it in the same tick it fires, and
  // react-query resolves the mutation function a beat later — so reading
  // `spokenMs` in here saw the cleared value and every spoken turn was
  // recorded as though it had been typed.
  const turn = useMutation({
    mutationFn: ({ text, audioMs }: { text: string; audioMs?: number }) =>
      sendSpeakTurn(sessionId!, text, audioMs),
    onSuccess: (data, { text }) => {
      setExchanges((prev) => [
        ...prev,
        { learner: text, partner: data.reply, correction: data.correction },
      ])
      setAllowance(data.allowance)
      setError(null)
    },
    // The draft is put back on failure — losing what someone just typed
    // because the network hiccuped is the fastest way to end a session.
    onError: (_err, { text }) => {
      setDraft(text)
      setError(t('speak.turnFailed'))
    },
  })

  const finish = useMutation({
    mutationFn: () => {
      // Done means done: stop listening and stop talking before the summary
      // arrives, or a hands-free session keeps holding the microphone and a
      // clip plays over the next screen.
      recorder.cancel()
      player.current?.pause?.()
      setPending(null)
      return endSpeakSession(sessionId!)
    },
    onSuccess: (data) => {
      setSummary(data.summary)
      setSessionId(null)
    },
    onError: () => setError(t('speak.endFailed')),
  })

  /** The partner's newest line, spoken and answered. Keyed on how many
   * exchanges exist, and guarded by a counter rather than the effect's deps,
   * because a re-render must never replay a line the learner already heard. */
  useEffect(() => {
    if (!sessionId) return
    const index = exchanges.length - 1
    if (index < 0 || announced.current > index) return
    announced.current = index + 1
    void announce(index)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [exchanges.length, sessionId])

  /** A pending transcript sends itself when its grace window runs out. */
  useEffect(() => {
    if (!pending) return
    const timer = window.setTimeout(() => {
      setPending(null)
      turn.mutate({ text: pending.text, audioMs: pending.ms })
    }, AUTO_SEND_GRACE_MS)
    return () => window.clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pending])

  /** Leaving the page mid-sentence must not leave a voice talking. */
  useEffect(() => {
    return () => {
      player.current?.pause?.()
      player.current = null
    }
  }, [])

  function submit() {
    const text = draft.trim()
    if (!text || turn.isPending) return
    setDraft('')
    turn.mutate({ text, audioMs: spokenMs ?? undefined })
    setSpokenMs(null)
  }

  function toggleMic() {
    setError(null)
    if (recorder.recording) transcribe.mutate()
    else void recorder.start()
  }

  if (!activeLanguageId || statusLoading) {
    return (
      <Shell title={t('nav.speak')}>
        <p className="text-sm text-gray-500">{t('speak.loading')}</p>
      </Shell>
    )
  }

  // Unavailable covers both "no AI configured here" and "the migration
  // hasn't landed yet" — from the learner's side those are the same fact.
  if (!status?.available) {
    return (
      <Shell title={t('nav.speak')}>
        <p className="text-sm text-gray-600">{t('speak.unavailable')}</p>
        <button
          type="button"
          onClick={() => navigate('/practice')}
          className="mt-4 text-sm font-semibold text-lang"
        >
          {t('speak.backToPractice')}
        </button>
      </Shell>
    )
  }

  if (summary) {
    return (
      <Shell title={t('nav.speak')}>
        <SummaryView
          summary={summary}
          languageCode={language?.code ?? 'en'}
          languageId={activeLanguageId}
          onAgain={() => {
            setSummary(null)
            setExchanges([])
          }}
        />
      </Shell>
    )
  }

  if (!sessionId) {
    return (
      <Shell title={t('nav.speak')} allowance={allowance}>
        <p className="text-sm text-gray-600">{t('speak.intro')}</p>

        <fieldset className="mt-4">
          <legend className="text-sm font-semibold text-gray-800">
            {t('speak.modeLegend')}
          </legend>
          <div className="mt-2 space-y-2">
            {(['coach', 'flow'] as SpeakMode[]).map((m) => (
              <label
                key={m}
                data-testid={`speak-mode-${m}`}
                className={`flex items-start gap-3 rounded-xl border p-3 cursor-pointer ${
                  mode === m
                    ? 'border-lang bg-lang-soft/40'
                    : 'border-gray-200 bg-white'
                }`}
              >
                <input
                  type="radio"
                  name="speak-mode"
                  value={m}
                  checked={mode === m}
                  onChange={() => setMode(m)}
                  className="mt-0.5 accent-[color:var(--lang)]"
                />
                <span>
                  <span className="block text-sm font-bold text-gray-900">
                    {t(m === 'coach' ? 'speak.modeCoach' : 'speak.modeFlow')}
                  </span>
                  <span className="block text-xs text-gray-500">
                    {t(m === 'coach'
                      ? 'speak.modeCoachSub'
                      : 'speak.modeFlowSub')}
                  </span>
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        <label
          htmlFor="speak-topic"
          className="block mt-4 text-sm font-semibold text-gray-800"
        >
          {t('speak.topicLabel')}
        </label>
        <input
          id="speak-topic"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          maxLength={120}
          placeholder={t('speak.topicPlaceholder')}
          className="mt-1 w-full rounded-xl border border-gray-300 px-4 py-3 text-sm"
        />
        <p className="mt-1 text-xs text-gray-500">{t('speak.topicHint')}</p>
        {/* Said once, up front, rather than discovered as a missing
            button mid-conversation. Latin, Māori, Yoruba, Hausa, Xhosa and
            Jamaican Patois have no recognizer, and that is permanent
            rather than a stopgap — so the session is a typed one and says
            so before it starts. */}
        {!status.speech?.listen && (
          <p
            className="mt-3 text-xs text-gray-600"
            data-testid="speak-no-listen"
          >
            {t('speak.micUnsupportedLanguage')}
          </p>
        )}
        <ConversationOptions
          value={conv}
          onChange={setConversation}
          canHear={canHear}
          canListen={canListen}
          canAutoSend={canAutoSend}
        />

        <button
          type="button"
          data-testid="speak-start"
          onClick={() => {
            // Inside the gesture, so the partner can speak later.
            if (conv.autoSpeak && canHear) primePlayer()
            start.mutate()
          }}
          disabled={start.isPending || !language}
          className="mt-4 w-full rounded-xl bg-lang px-6 py-3 text-sm font-bold text-white disabled:opacity-50"
          style={{ minHeight: '44px' }}
        >
          {start.isPending ? t('speak.starting') : t('speak.startButton')}
        </button>
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      </Shell>
    )
  }

  return (
    <Shell title={t('nav.speak')} allowance={allowance}>
      <div className="space-y-3" data-testid="speak-transcript">
        {exchanges.length === 0 && !turn.isPending && (
          <p className="text-sm text-gray-500">{t('speak.yourMove')}</p>
        )}
        {exchanges.map((x, i) => (
          <div key={i} className="space-y-2">
            {x.learner && (
              <p className="ms-auto max-w-[85%] rounded-2xl bg-lang-soft/60 px-4 py-2 text-sm text-gray-900 w-fit">
                {x.learner}
              </p>
            )}
            {/* One line, one point, then the conversation moves on. Never a
                list — a learner corrected three times per turn stops
                talking. The rest are kept for the summary. */}
            {x.correction && (
              // Amber-family TEXT on the amber chip, never gray: the dark
              // theme remaps the whole gray ramp light while amber tints
              // deliberately stay light (index.css — "highlighted callouts
              // on dark"), so gray-900 here rendered near-white on cream
              // and the correction — the one line Coach mode exists for —
              // was illegible in dark mode. Same convention as the Tutor
              // mastery card and FeedbackPanel.
              <div
                data-testid={`speak-correction-${i}`}
                className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-2 text-sm"
              >
                <span className="font-semibold text-amber-900">
                  <LanguageWrapper languageCode={language?.code ?? 'en'}>
                    <span>
                      {x.correction.learner_said} → {x.correction.should_be}
                    </span>
                  </LanguageWrapper>
                </span>
                <span className="block mt-0.5 text-amber-800">
                  {x.correction.note}
                </span>
              </div>
            )}
            {/* Listening practice: heard, not read, until they ask. The
                words are withheld rather than absent — one tap shows them,
                because a learner stuck on one word should be able to look
                instead of abandoning the conversation. */}
            {maskText && !revealed[i] ? (
              <button
                type="button"
                onClick={() => setRevealed((prev) => ({ ...prev, [i]: true }))}
                data-testid={`speak-reveal-${i}`}
                className="flex items-center gap-2 rounded-2xl border border-dashed border-gray-300 bg-white px-4 py-2 text-sm text-gray-500 w-fit"
                style={{ minHeight: '44px' }}
              >
                <Eye aria-hidden className="h-4 w-4" />
                {t('speak.showText')}
              </button>
            ) : (
              <LanguageWrapper languageCode={language?.code ?? 'en'}>
                <p className="max-w-[85%] rounded-2xl bg-white border border-gray-200 px-4 py-2 text-sm text-gray-900 w-fit">
                  {x.partner}
                </p>
              </LanguageWrapper>
            )}
            {canHear && sessionId && (
              <PartnerAudio
                turnIndex={i}
                getClip={getClip}
                onError={() => setError(t('speak.playFailed'))}
              />
            )}
          </div>
        ))}
        {turn.isPending && (
          <p className="flex items-center gap-2 text-sm text-gray-500">
            <Loader2 aria-hidden className="h-4 w-4 animate-spin" />
            {t('speak.thinking')}
          </p>
        )}
        <div ref={endRef} />
      </div>

      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      {recorder.error === 'denied' && (
        <p className="mt-3 text-sm text-red-600" data-testid="speak-mic-denied">
          {t('speak.micDenied')}
        </p>
      )}

      {/* The transcript lands in the same box a typed turn is written in,
          and is editable there. Two reasons: ASR mishears an accented
          beginner and the learner must be able to fix it before being
          corrected for a word they didn't say — and it leaves exactly one
          Send, rather than a spoken path that bypasses the typed one. */}
      {spokenMs !== null && draft && (
        <p className="mt-3 text-xs text-gray-500" data-testid="speak-transcript-note">
          {t('speak.transcriptLabel')}
        </p>
      )}

      {/* Hands-free: what was heard, on its way, with two seconds to stop it.
          Sending without showing anything would be faster and would also mean
          being corrected for words you never said — so the transcript still
          gets read, it just doesn't need a tap. */}
      {pending && (
        <div
          data-testid="speak-pending"
          className="mt-3 flex items-start gap-3 rounded-xl border border-lang/40 bg-lang-soft/40 px-4 py-2"
        >
          <span className="flex-1 text-sm text-gray-800">
            <span className="block text-xs text-lang-label">
              {t('speak.autoSending')}
            </span>
            {pending.text}
          </span>
          <button
            type="button"
            onClick={() => {
              // Not what they said: keep the text, let them fix it, and don't
              // send anything until they do.
              setDraft(pending.text)
              setSpokenMs(pending.ms)
              setPending(null)
            }}
            aria-label={t('speak.autoSendCancel')}
            data-testid="speak-pending-cancel"
            className="shrink-0 rounded-lg border border-gray-300 bg-white p-2 text-gray-600"
            style={{ minHeight: '44px', minWidth: '44px' }}
          >
            <X aria-hidden className="h-4 w-4" />
          </button>
        </div>
      )}

      <div className="mt-4 flex items-end gap-2">
        {canListen && (
          <button
            type="button"
            onClick={toggleMic}
            disabled={transcribe.isPending || turn.isPending}
            aria-pressed={recorder.recording}
            aria-label={
              recorder.recording ? t('speak.micStop') : t('speak.micStart')
            }
            data-testid="speak-mic"
            className={`rounded-xl p-3 disabled:opacity-50 ${
              recorder.recording
                ? 'bg-red-600 text-white animate-pulse'
                : 'border border-lang text-lang bg-white'
            }`}
            style={{ minHeight: '44px', minWidth: '44px' }}
          >
            {recorder.recording ? (
              <Square aria-hidden className="h-5 w-5" />
            ) : (
              <Mic aria-hidden className="h-5 w-5" />
            )}
          </button>
        )}
        <textarea
          value={draft}
          onChange={(e) => {
            setDraft(e.target.value)
            // Edited by hand after a recording: the duration still stands.
            // They spoke for that long; fixing a misheard word doesn't
            // change how long they talked.
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              submit()
            }
          }}
          rows={2}
          maxLength={2000}
          aria-label={t('speak.inputLabel')}
          placeholder={t('speak.inputPlaceholder')}
          data-testid="speak-input"
          className="flex-1 resize-none rounded-xl border border-gray-300 px-4 py-3 text-sm"
        />
        <button
          type="button"
          onClick={submit}
          disabled={!draft.trim() || turn.isPending}
          aria-label={t('speak.send')}
          data-testid="speak-send"
          className="rounded-xl bg-lang p-3 text-white disabled:opacity-50"
          style={{ minHeight: '44px', minWidth: '44px' }}
        >
          <Send aria-hidden className="h-5 w-5" />
        </button>
      </div>

      {canListen && (
        <p className="mt-2 text-xs text-gray-500" data-testid="speak-mic-state">
          {recorder.recording
            ? autoSend
              ? t('speak.micListeningHandsFree')
              : t('speak.micListening')
            : transcribe.isPending
              ? t('speak.micTranscribing')
              /* A permission prompt is not consent. One plain line, before
                 the first recording, saying what happens to the audio. */
              : t('speak.micPrivacy')}
        </p>
      )}

      {/* The browser refused to play a clip nobody's finger asked for. The
          replay buttons still work, so this explains rather than alarms. */}
      {autoplayBlocked && (
        <p className="mt-2 text-xs text-gray-600" data-testid="speak-autoplay-blocked">
          {t('speak.autoplayBlocked')}
        </p>
      )}

      {/* Mid-conversation, the options are a disclosure rather than a panel:
          the escape hatch has to be reachable without ending the session
          (a hands-free session in a suddenly-crowded room). */}
      <details className="mt-4">
        <summary className="cursor-pointer text-xs font-semibold text-lang">
          {t('speak.conversationOptions')}
        </summary>
        <div className="mt-2">
          <ConversationOptions
            value={conv}
            onChange={setConversation}
            canHear={canHear}
            canListen={canListen}
            canAutoSend={canAutoSend}
            compact
          />
        </div>
      </details>

      <button
        type="button"
        onClick={() => finish.mutate()}
        disabled={finish.isPending}
        data-testid="speak-done"
        className="mt-4 w-full rounded-xl border border-gray-300 bg-white px-6 py-3 text-sm font-semibold text-gray-800 disabled:opacity-50"
        style={{ minHeight: '44px' }}
      >
        {finish.isPending ? t('speak.ending') : t('speak.done')}
      </button>
    </Shell>
  )
}

/**
 * The partner's line, out loud — and again, slower.
 *
 * "Say that again" is the one control the plan argued hardest for.
 * Comprehension failure is the commonest reason a conversation dies, and
 * without a replay the learner's only recovery is to quit the session.
 *
 * Each clip is fetched on press rather than with the turn: most lines are
 * never replayed, and synthesizing every one of them up front would spend
 * real money on audio nobody listens to.
 */
function PartnerAudio({
  turnIndex,
  getClip,
  onError,
}: {
  turnIndex: number
  /** Shared with auto-speak, so a line already spoken replays for free —
   * which is also why this component no longer needs the session id: the
   * page owns both the cache and the fetch. */
  getClip: (turnIndex: number, slow: boolean) => Promise<string>
  onError: () => void
}) {
  const { t } = useTranslation()
  const [busy, setBusy] = useState<'normal' | 'slow' | null>(null)
  const audio = useRef<HTMLAudioElement | null>(null)

  useEffect(() => {
    // Stop a clip still playing when the component goes — leaving a voice
    // talking over the next screen is worse than silence.
    return () => {
      audio.current?.pause()
      audio.current = null
    }
  }, [])

  async function play(slow: boolean) {
    if (busy) return
    setBusy(slow ? 'slow' : 'normal')
    try {
      const b64 = await getClip(turnIndex, slow)
      audio.current?.pause()
      const el = new Audio(`data:audio/mpeg;base64,${b64}`)
      audio.current = el
      // play() rejects when autoplay policy blocks it — a real outcome,
      // not an exception to swallow, so it is reported like any failure.
      await el.play()
    } catch {
      onError()
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="flex items-center gap-1">
      <button
        type="button"
        onClick={() => play(false)}
        disabled={busy !== null}
        aria-label={t('speak.playPartner')}
        data-testid={`speak-play-${turnIndex}`}
        className="rounded-lg p-2 text-gray-500 hover:text-lang disabled:opacity-50"
        style={{ minHeight: '44px', minWidth: '44px' }}
      >
        {busy === 'normal' ? (
          <Loader2 aria-hidden className="h-4 w-4 animate-spin" />
        ) : (
          <Volume2 aria-hidden className="h-4 w-4" />
        )}
      </button>
      <button
        type="button"
        onClick={() => play(true)}
        disabled={busy !== null}
        data-testid={`speak-play-slow-${turnIndex}`}
        className="rounded-lg px-2 py-1 text-xs text-gray-500 hover:text-lang disabled:opacity-50"
        style={{ minHeight: '44px' }}
      >
        {t('speak.playSlower')}
      </button>
    </div>
  )
}

function Shell({
  title,
  allowance,
  children,
}: {
  title: string
  allowance?: TutorAllowance | null
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen bg-gray-50 overflow-x-hidden">
      <div className="max-w-3xl mx-auto px-4 py-6 space-y-4 pb-24 md:pb-6">
        <SectionHeader title={title} />
        {allowance && <UsageMeter allowance={allowance} />}
        {children}
      </div>
    </div>
  )
}

function SummaryView({
  summary,
  languageCode,
  languageId,
  onAgain,
}: {
  summary: SpeakSummary
  languageCode: string
  languageId: string | null
  onAgain: () => void
}) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  // Nothing is added on its own. These track what the learner chose, so a
  // second tap can't duplicate a card and the button can say it worked.
  const [added, setAdded] = useState<Record<string, boolean>>({})
  const [failed, setFailed] = useState<Record<string, boolean>>({})

  const add = useMutation({
    mutationFn: async ({
      key, sentence, answer, translation, gloss,
    }: {
      key: string
      sentence: string
      answer: string
      translation?: string
      gloss?: string
    }) => {
      await createPersonalCard({
        languageId: languageId!,
        languageCode,
        sentence,
        answer,
        translation,
        gloss,
        source: 'speak',
      })
      return key
    },
    onSuccess: (key) => {
      setAdded((prev) => ({ ...prev, [key]: true }))
      setFailed((prev) => ({ ...prev, [key]: false }))
    },
    onError: (_e, vars) => setFailed((prev) => ({ ...prev, [vars.key]: true })),
  })

  const anyAdded = Object.values(added).some(Boolean)

  return (
    <div data-testid="speak-summary">
      <p className="text-sm text-gray-600">
        {t('speak.summaryStats', { count: summary.stats?.turns ?? 0 })}
      </p>

      {summary.groups.length === 0 ? (
        <p className="mt-4 rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-700">
          {t('speak.nothingCameUp')}
        </p>
      ) : (
        <>
          <h2 className="mt-5 text-sm font-bold text-gray-900">
            {t('speak.whatCameUp')}
          </h2>
          <ul className="mt-2 space-y-2">
            {summary.groups.map((g, i) => (
              <li
                key={i}
                className="rounded-xl border border-gray-200 bg-white p-4"
              >
                <div className="flex items-baseline justify-between gap-3">
                  <span className="text-sm font-bold text-gray-900">
                    {g.label}
                  </span>
                  <span className="text-xs text-gray-500">
                    {t('speak.timesCount', { count: g.count })}
                  </span>
                </div>
                <p className="mt-1 text-sm text-gray-700">{g.note}</p>
                {g.examples.length > 0 && (
                  <LanguageWrapper languageCode={languageCode}>
                    <ul className="mt-2 space-y-0.5">
                      {g.examples.map((ex, j) => (
                        <li key={j} className="text-sm text-gray-600">
                          {ex}
                        </li>
                      ))}
                    </ul>
                  </LanguageWrapper>
                )}
                {/* Absent when the session produced nothing a card could be
                    built from — better than a button that fails on tap. */}
                {g.card && (
                  <AddButton
                    testId={`speak-add-group-${i}`}
                    added={!!added[`g${i}`]}
                    failed={!!failed[`g${i}`]}
                    disabled={add.isPending || !languageId}
                    onClick={() =>
                      add.mutate({
                        key: `g${i}`,
                        sentence: g.card!.sentence,
                        answer: g.card!.answer,
                        translation: g.card!.translation,
                      })
                    }
                  />
                )}
              </li>
            ))}
          </ul>
        </>
      )}

      {summary.vocabulary.length > 0 && (
        <>
          <h2 className="mt-5 text-sm font-bold text-gray-900">
            {t('speak.wordsYouReachedFor')}
          </h2>
          <ul className="mt-2 rounded-xl border border-gray-200 bg-white p-4 space-y-2">
            {summary.vocabulary.map((v, i) => (
              <li
                key={i}
                className="flex items-baseline justify-between gap-3 text-sm text-gray-700"
              >
                <span>
                  <LanguageWrapper languageCode={languageCode}>
                    <span className="font-semibold">{v.term}</span>
                  </LanguageWrapper>
                  <span className="text-gray-500"> — {v.meaning}</span>
                </span>
                <AddButton
                  testId={`speak-add-word-${i}`}
                  added={!!added[`v${i}`]}
                  failed={!!failed[`v${i}`]}
                  disabled={add.isPending || !languageId}
                  onClick={() =>
                    add.mutate({
                      key: `v${i}`,
                      // Prefer the sentence they met it in; the server falls
                      // back to a type-the-word card from the gloss when the
                      // term isn't a whole word there.
                      sentence: v.example || v.term,
                      answer: v.term,
                      gloss: v.meaning,
                    })
                  }
                />
              </li>
            ))}
          </ul>
        </>
      )}

      {anyAdded && (
        <button
          type="button"
          onClick={() => navigate('/review')}
          data-testid="speak-practise"
          className="mt-5 w-full rounded-xl bg-lang px-6 py-3 text-sm font-bold text-white"
          style={{ minHeight: '44px' }}
        >
          {t('speak.practiseThese')}
        </button>
      )}

      <button
        type="button"
        onClick={onAgain}
        data-testid="speak-again"
        className={`mt-3 w-full rounded-xl px-6 py-3 text-sm font-bold ${
          anyAdded
            ? 'border border-gray-300 bg-white text-gray-800'
            : 'bg-lang text-white'
        }`}
        style={{ minHeight: '44px' }}
      >
        {t('speak.talkAgain')}
      </button>
    </div>
  )
}

/** Opt-in, one tap, and honest about what happened. Nothing is ever added
 * without the learner asking — a summary that quietly filled their reviews
 * would make them wary of finishing a session at all. */
function AddButton({
  testId,
  added,
  failed,
  disabled,
  onClick,
}: {
  testId: string
  added: boolean
  failed: boolean
  disabled: boolean
  onClick: () => void
}) {
  const { t } = useTranslation()
  if (added) {
    return (
      <span
        data-testid={testId}
        className="shrink-0 inline-flex items-center gap-1 text-xs font-semibold text-green-700"
      >
        <Check aria-hidden className="h-3.5 w-3.5" />
        {t('speak.added')}
      </span>
    )
  }
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      data-testid={testId}
      className="shrink-0 rounded-lg border border-lang/40 px-3 py-1.5 text-xs font-semibold text-lang disabled:opacity-50"
      style={{ minHeight: '32px' }}
    >
      {failed ? t('speak.addRetry') : t('speak.add')}
    </button>
  )
}

/**
 * The four conversation switches (owner: "create options that provide users
 * real convo situations").
 *
 * Four independent checkboxes rather than one hands-free mode, plus a button
 * that sets all four at once for the people who want exactly that. They are
 * independent because they fail differently — someone on a train wants the
 * partner's text without its voice, and someone practising listening wants
 * the voice without the text — and because a single mode would have to pick
 * one of those for everybody.
 *
 * A switch whose prerequisite is missing is shown DISABLED with the reason,
 * not hidden: "why can't I turn this on" is answerable, and a control that
 * silently vanishes on some courses reads as a bug.
 */
function ConversationOptions({
  value,
  onChange,
  canHear,
  canListen,
  canAutoSend,
  compact = false,
}: {
  value: SpeakConversationPrefs
  onChange: (patch: Partial<SpeakConversationPrefs>) => void
  canHear: boolean
  canListen: boolean
  canAutoSend: boolean
  compact?: boolean
}) {
  const { t } = useTranslation()

  const rows: Array<{
    key: keyof SpeakConversationPrefs
    label: string
    hint: string
    enabled: boolean
    blockedBecause: string
  }> = [
    {
      key: 'autoSpeak',
      label: t('speak.optAutoSpeak'),
      hint: t('speak.optAutoSpeakHint'),
      enabled: canHear,
      blockedBecause: t('speak.optNoVoice'),
    },
    {
      key: 'hideText',
      label: t('speak.optHideText'),
      hint: t('speak.optHideTextHint'),
      enabled: canHear,
      blockedBecause: t('speak.optNoVoice'),
    },
    {
      key: 'autoListen',
      label: t('speak.optAutoListen'),
      hint: t('speak.optAutoListenHint'),
      enabled: canListen,
      blockedBecause: t('speak.optNoMic'),
    },
    {
      key: 'autoSend',
      label: t('speak.optAutoSend'),
      hint: t('speak.optAutoSendHint'),
      enabled: canListen && canAutoSend,
      blockedBecause: canListen
        ? t('speak.optNoSilenceDetection')
        : t('speak.optNoMic'),
    },
  ]

  const handsFreeAvailable = canHear && canListen && canAutoSend
  const handsFreeOn =
    value.autoSpeak && value.autoListen && value.autoSend

  return (
    <fieldset className={compact ? '' : 'mt-4'} data-testid="speak-options">
      {!compact && (
        <legend className="text-sm font-semibold text-gray-800">
          {t('speak.conversationOptions')}
        </legend>
      )}
      <div className="mt-2 space-y-1.5">
        {rows.map((row) => (
          <label
            key={row.key}
            data-testid={`speak-opt-${row.key}`}
            className={`flex items-start gap-3 rounded-xl border p-2.5 ${
              row.enabled
                ? 'cursor-pointer border-gray-200 bg-white'
                : 'border-gray-100 bg-gray-50 opacity-70'
            }`}
          >
            <input
              type="checkbox"
              checked={row.enabled && value[row.key]}
              disabled={!row.enabled}
              onChange={(e) => onChange({ [row.key]: e.target.checked })}
              className="mt-0.5 accent-[color:var(--lang)]"
            />
            <span>
              <span className="block text-sm font-semibold text-gray-900">
                {row.label}
              </span>
              <span className="block text-xs text-gray-500">
                {row.enabled ? row.hint : row.blockedBecause}
              </span>
            </span>
          </label>
        ))}
      </div>
      {handsFreeAvailable && !handsFreeOn && (
        <button
          type="button"
          onClick={() =>
            onChange({ autoSpeak: true, autoListen: true, autoSend: true })
          }
          data-testid="speak-hands-free"
          className="mt-2 rounded-xl border border-lang px-4 py-2 text-xs font-bold text-lang"
          style={{ minHeight: '36px' }}
        >
          {t('speak.handsFree')}
        </button>
      )}
    </fieldset>
  )
}
