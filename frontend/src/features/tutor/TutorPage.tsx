import { useCallback, useEffect, useRef, useState } from 'react'
import { languageDisplayName } from '../../lib/languages'
import UiLanguageSwitcher from '../../components/UiLanguageSwitcher'
import { Trans, useTranslation } from 'react-i18next'
import { ArrowDown, ArrowUp, Star } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getLanguages } from '../../api/profile'
import { createCheckout } from '../../api/billing'
import {
  endTutorSession,
  getTutorSessions,
  getTutorStatus,
  resolveMasterySuggestion,
  sendTutorMessage,
  streamTutorMessage,
  TutorTurnError,
} from '../../api/tutor'
import type { TutorAllowance, TutorMessage, TutorMode } from '../../api/tutor'
import UsageMeter from '../../components/UsageMeter'
import { usePrefsStore } from '../../stores/prefsStore'
import Annotatable from '../contribute/Annotatable'
import AiDisclaimer from '../../components/AiDisclaimer'
import TutorMarkdown from './TutorMarkdown'

// Summarize into memory after this long without activity.
const IDLE_MS = 3 * 60 * 1000

function resetDay(resetsAt: string | null, locale: string): string | null {
  if (!resetsAt) return null
  return new Date(resetsAt).toLocaleDateString(locale, {
    month: 'long',
    day: 'numeric',
  })
}

export default function TutorPage() {
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()
  const queryClient = useQueryClient()
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)
  const [messages, setMessages] = useState<TutorMessage[]>([])
  const [input, setInput] = useState('')
  const [sendError, setSendError] = useState<string | null>(null)
  // The live meter: seeded by /status, updated from each reply, zeroed by a
  // structured 402 — always the freshest number the server has given us.
  const [liveAllowance, setLiveAllowance] = useState<TutorAllowance | null>(null)
  const allowanceRef = useRef<TutorAllowance | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  // Refs so the session-end flush reads live values without re-subscribing.
  const messagesRef = useRef<TutorMessage[]>([])
  const endedRef = useRef(false)
  const langRef = useRef<{ id: string; code: string } | null>(null)
  const idleTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  // Live turn, so Stop can cancel it.
  const abortRef = useRef<AbortController | null>(null)
  // The scroll container, so the jump buttons have something to move.
  const scrollRef = useRef<HTMLDivElement>(null)
  messagesRef.current = messages

  const { data: languages = [] } = useQuery({
    queryKey: ['languages'],
    queryFn: getLanguages,
  })
  const language = languages.find((l) => l.id === activeLanguageId)
  if (language) langRef.current = { id: language.id, code: language.code }

  // Flush the conversation into durable memory. Fire-and-forget, idempotent
  // per session (endedRef guards double-sends from button + unmount + idle).
  const flushSession = useCallback(() => {
    const lang = langRef.current
    const convo = messagesRef.current
    if (endedRef.current || !lang || convo.length < 2) return
    if (!hadPractice.current) return // reference-only: nothing to summarize
    endedRef.current = true
    void endTutorSession(lang.id, lang.code, convo).catch(() => {
      // Best-effort: memory summary is not critical to the user's flow.
    })
  }, [])

  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ['tutor-status', activeLanguageId, language?.code],
    queryFn: () => getTutorStatus(activeLanguageId!, language!.code),
    enabled: !!activeLanguageId && !!language,
  })

  // Start a subscription. Real mode hands back a Stripe Checkout URL to
  // redirect to; dev-mock grants directly, so we just refetch entitlement.
  const subscribeMutation = useMutation({
    mutationFn: () => createCheckout(activeLanguageId!),
    onSuccess: (res) => {
      if (res.url) {
        window.location.href = res.url
      } else {
        queryClient.invalidateQueries({ queryKey: ['tutor-status'] })
      }
    },
  })

  // Partial assistant text while a streamed reply is arriving (WP9d).
  const [streamingText, setStreamingText] = useState<string | null>(null)
  // WP18c: reference questions are answered without drilling or memory
  // writes; only practice turns make a session worth summarizing.
  const [mode, setMode] = useState<TutorMode>('practice')
  const hadPractice = useRef(false)
  const [historyOpen, setHistoryOpen] = useState(false)

  const { data: pastSessions = [] } = useQuery({
    queryKey: ['tutor-sessions', activeLanguageId],
    queryFn: () => getTutorSessions(activeLanguageId!),
    enabled: !!activeLanguageId && historyOpen,
  })

  // WP19(e): the learner's verdict on a mastery star. Accepting moves the
  // card's next review ~a month out, so invalidate everything due-shaped.
  const resolveMastery = useMutation({
    mutationFn: ({ id, action }: { id: string; action: 'accept' | 'dismiss' }) =>
      resolveMasterySuggestion(id, action),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tutor-status'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['due-cards'] })
    },
  })

  const sendMutation = useMutation({
    mutationFn: async (history: TutorMessage[]) => {
      // Stream when the transport allows it; fall back to the plain
      // endpoint on any transport failure (except allowance 402s, which
      // both endpoints report identically).
      const controller = new AbortController()
      abortRef.current = controller
      try {
        return await streamTutorMessage(
          activeLanguageId!, language!.code, history, setStreamingText, mode,
          controller.signal,
        )
      } catch (err) {
        const status = (err as { response?: { status?: number } })?.response?.status
        if (status === 402) throw err
        // A TutorTurnError is the server's answer (or the learner pressing
        // Stop) — retrying it on the non-streaming endpoint spends a second
        // full model call to be told the same thing.
        if (err instanceof TutorTurnError) throw err
        setStreamingText(null)
        return sendTutorMessage(activeLanguageId!, language!.code, history, mode)
      } finally {
        abortRef.current = null
      }
    },
    onSuccess: ({ reply, allowance: fresh, starred }) => {
      setStreamingText(null)
      setMessages((prev) => [...prev, { role: 'assistant', content: reply }])
      setSendError(null)
      if (fresh) setLiveAllowance(fresh)
      // A new mastery star landed — refetch status so the panel shows it.
      if (starred > 0) {
        queryClient.invalidateQueries({ queryKey: ['tutor-status'] })
      }
    },
    onError: (err) => {
      const detail = (err as {
        response?: { status?: number; data?: { detail?: { code?: string } } }
      })?.response
      setStreamingText(null)
      if (detail?.status === 402 && detail.data?.detail?.code === 'allowance_exhausted') {
        // Zero the meter — the exhausted panel takes over the input area.
        const base = allowanceRef.current
        if (base) setLiveAllowance({ ...base, remaining: 0, used: base.limit })
        setSendError(null)
      } else if (err instanceof TutorTurnError) {
        // Drop the unanswered message back into the box so a stalled or
        // stopped turn doesn't lose what the learner typed.
        setMessages((prev) => {
          const last = prev[prev.length - 1]
          if (last?.role === 'user') {
            setInput((cur) => cur || last.content)
            return prev.slice(0, -1)
          }
          return prev
        })
        setSendError(err.aborted ? null : err.message)
      } else {
        setSendError(t('tutor.sendError'))
      }
    },
  })

  const handleStop = () => {
    abortRef.current?.abort()
  }

  useEffect(() => {
    // Optional chaining on the method too — jsdom doesn't implement it
    bottomRef.current?.scrollIntoView?.({ behavior: 'smooth' })
  }, [messages, sendMutation.isPending])

  // Flush on unmount (navigating away ends the session).
  useEffect(() => {
    return () => {
      if (idleTimer.current) clearTimeout(idleTimer.current)
      flushSession()
    }
  }, [flushSession])

  const handleSend = () => {
    const text = input.trim()
    if (!text || sendMutation.isPending || !language) return
    if (mode === 'practice') hadPractice.current = true
    const history = [...messages, { role: 'user' as const, content: text }]
    setMessages(history)
    setInput('')
    sendMutation.mutate(history)
    // New activity reopens the session and resets the idle countdown.
    endedRef.current = false
    if (idleTimer.current) clearTimeout(idleTimer.current)
    idleTimer.current = setTimeout(flushSession, IDLE_MS)
  }

  const handleEndSession = () => {
    if (idleTimer.current) clearTimeout(idleTimer.current)
    flushSession()
    navigate('/')
  }

  if (statusLoading || !language) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-500">{t('tutor.loading')}</p>
      </div>
    )
  }

  if (!status?.available) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="text-center space-y-4">
          <p className="text-xl text-gray-700">
            {t('tutor.notAvailable', {
              language: languageDisplayName(language.code, language.name, i18n.language),
            })}
          </p>
          <button
            type="button"
            onClick={() => navigate('/')}
            className="text-lang hover:underline text-sm"
          >
            {t('review.backToDashboard')}
          </button>
        </div>
      </div>
    )
  }

  // The freshest meter we have: live (from replies/402s) beats the status
  // snapshot. `allowance` is null only in operator free-access mode… which
  // the API reports as unlimited, so a missing meter also means unlimited.
  const allowance = liveAllowance ?? status.allowance
  allowanceRef.current = allowance
  const exhausted =
    !!allowance && !allowance.unlimited && (allowance.remaining ?? 0) <= 0

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <div className="relative max-w-2xl mx-auto w-full px-4 py-6 flex flex-col flex-1">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-xl font-bold text-gray-900">
              {t('tutor.title', { language: languageDisplayName(language.code, language.name, i18n.language) })}
            </h1>
            <p className="text-xs text-gray-500">{t('tutor.subtitle')}</p>
          </div>
          <span className="flex items-center gap-3">
            <UiLanguageSwitcher />
            <button
              type="button"
              onClick={handleEndSession}
              className="text-sm text-lang hover:underline"
            >
              {t('tutor.endSession')}
            </button>
          </span>
        </div>

        {/* Practice vs Reference (WP18c): reference questions get direct
            answers with no drilling and no memory writes. */}
        <div className="flex flex-wrap items-center gap-2 mb-2 text-xs">
          <div
            role="group"
            aria-label={t('tutor.modeGroupAria')}
            className="inline-flex rounded-lg border border-gray-200 overflow-hidden"
          >
            <button
              type="button"
              onClick={() => setMode('practice')}
              aria-pressed={mode === 'practice'}
              className={
                mode === 'practice'
                  ? 'px-3 py-1 bg-lang text-lang-on font-semibold'
                  : 'px-3 py-1 bg-white text-gray-500 hover:text-lang'
              }
            >
              {t('tutor.practice')}
            </button>
            <button
              type="button"
              onClick={() => setMode('reference')}
              aria-pressed={mode === 'reference'}
              title={t('tutor.referenceTitle')}
              className={
                mode === 'reference'
                  ? 'px-3 py-1 bg-lang text-lang-on font-semibold'
                  : 'px-3 py-1 bg-white text-gray-500 hover:text-lang'
              }
            >
              {t('tutor.reference')}
            </button>
          </div>
          <button
            type="button"
            onClick={() => setHistoryOpen((v) => !v)}
            aria-expanded={historyOpen}
            className="text-gray-500 hover:text-lang"
          >
            {historyOpen ? t('tutor.hidePastSessions') : t('tutor.pastSessions')}
          </button>
          <button
            type="button"
            onClick={() => navigate('/read')}
            title={t('tutor.readLinkTitle')}
            className="text-gray-500 hover:text-lang"
          >
            {t('tutor.readLink')}
          </button>
        </div>

        {/* One-line explainer of the two modes (beta request). */}
        <p className="text-[11px] text-gray-500 mb-2">
          {mode === 'practice'
            ? t('tutor.practiceLine')
            : t('tutor.referenceLine')}
        </p>

        {/* Active Focus (WP18b): the structures the tutor is deliberately
            working on with this learner — tutor-managed, read-only here. */}
        {(status?.focus?.length ?? 0) > 0 && (
          <div
            className="flex flex-wrap items-center gap-1.5 mb-2"
            data-testid="active-focus"
          >
            <span className="text-[10px] uppercase tracking-wide text-gray-500">
              {t('tutor.activeFocus')}
            </span>
            {status!.focus!.map((f) => (
              <span
                key={f.structure}
                title={f.reason}
                className="text-xs rounded-full px-2 py-0.5 bg-lang-soft text-lang-dark"
              >
                {f.structure}
              </span>
            ))}
          </div>
        )}

        {/* Mastery stars (WP19e): the tutor's "you've already got this"
            suggestions. The learner decides — accept moves the card's next
            review ~a month out; dismiss keeps drilling it. */}
        {(status?.mastery_suggestions?.length ?? 0) > 0 && (
          <div
            className="mb-3 rounded-xl border border-amber-200 bg-amber-50 p-3 space-y-2"
            data-testid="mastery-suggestions"
          >
            <p className="text-xs font-semibold text-amber-900">
              <Star aria-hidden className="me-1 inline h-3.5 w-3.5 align-[-2px] fill-amber-400 text-amber-400" />{t('tutor.masteryTitle')}
            </p>
            <p className="text-[11px] text-amber-800/80">
              {t('tutor.masteryExplain')}
            </p>
            {status!.mastery_suggestions!.map((s) => (
              <div
                key={s.id}
                className="flex items-start justify-between gap-3 bg-white/70 rounded-lg px-2.5 py-2"
              >
                <div className="min-w-0 text-sm">
                  <span className="font-medium text-gray-900">{s.item}</span>
                  <span className="ms-1.5 text-[10px] uppercase tracking-wide text-gray-500">
                    {s.kind === 'grammar' ? t('tutor.kindGrammar') : t('tutor.kindVocab')}
                  </span>
                  {s.evidence && (
                    <p className="text-xs text-gray-600 mt-0.5">{s.evidence}</p>
                  )}
                </div>
                <span className="flex gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={() =>
                      resolveMastery.mutate({ id: s.id, action: 'accept' })
                    }
                    disabled={resolveMastery.isPending}
                    className="text-xs font-semibold rounded-lg bg-lang hover:bg-lang-dark text-lang-on px-2.5 py-1.5 disabled:opacity-50"
                    style={{ minHeight: '32px' }}
                  >
                    {t('tutor.iKnowIt')}
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      resolveMastery.mutate({ id: s.id, action: 'dismiss' })
                    }
                    disabled={resolveMastery.isPending}
                    className="text-xs rounded-lg border border-gray-300 bg-white text-gray-600 hover:text-lang px-2.5 py-1.5 disabled:opacity-50"
                    style={{ minHeight: '32px' }}
                  >
                    {t('tutor.keepDrilling')}
                  </button>
                </span>
              </div>
            ))}
          </div>
        )}

        {historyOpen && (
          <div
            className="mb-3 rounded-xl border border-gray-100 bg-white p-3 space-y-2 max-h-48 overflow-y-auto"
            data-testid="past-sessions"
          >
            {pastSessions.length === 0 && (
              <p className="text-xs text-gray-500">
                {t('tutor.noPastSessions')}
              </p>
            )}
            {pastSessions.map((sess) => (
              <div key={sess.id} className="text-xs">
                <p className="text-gray-500">
                  {new Date(sess.created_at).toLocaleDateString(i18n.language, {
                    month: 'short', day: 'numeric',
                  })}{' '}
                  · {t('tutor.messages', { count: sess.message_count })}
                </p>
                <p className="text-gray-700">{sess.summary}</p>
              </div>
            ))}
          </div>
        )}

        {/* Usage meter — Claude-style (owner): a percentage of the monthly
            pool and a reset date, never message counts or model plumbing.
            Every tier is a MONTHLY pool; plus/granted just get a much larger
            one. Flat pricing, so drawing it down never costs extra. */}
        {allowance && !allowance.unlimited && !exhausted && (
          <div className="mb-3" data-testid="tutor-allowance">
            <UsageMeter allowance={allowance} />
            {['free', 'single', 'all'].includes(allowance.tier) && (
              <p className="mt-1 text-xs text-gray-500">
                <button
                  type="button"
                  onClick={() => subscribeMutation.mutate()}
                  className="text-lang hover:underline"
                >
                  {t('tutor.plus')}
                </button>{' '}
                {t('tutor.plusNote')}
              </p>
            )}
          </div>
        )}

        {/* Messages */}
        <div
          ref={scrollRef}
          className="relative flex-1 overflow-y-auto space-y-3 pb-4"
          data-testid="tutor-messages"
        >
          {messages.length === 0 && (
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 text-sm text-gray-600">
              {t('tutor.greeting', {
                language: languageDisplayName(language.code, language.name, i18n.language),
              })}
            </div>
          )}
          {messages.map((msg, i) =>
            msg.role === 'user' ? (
              <div
                key={i}
                className="ms-8 bg-lang text-white rounded-2xl rounded-ee-sm px-4 py-2.5 text-sm whitespace-pre-wrap"
              >
                <span dir="auto">{msg.content}</span>
              </div>
            ) : (
              /* Tutor turns are flaggable in Review Mode: a bad explanation or
                 an unnatural example matters as much as a bad card, and until
                 now there was no way to report one. Nothing here is stored
                 content, so the quote and its context ARE the record. */
              <Annotatable
                key={i}
                languageId={activeLanguageId}
                targetType="tutor_message"
                targetLabel={msg.content.slice(0, 200)}
                field="other"
                source="tutor"
                className="me-8 bg-white border border-gray-100 shadow-sm rounded-2xl rounded-es-sm px-4 py-2.5 text-sm text-gray-800"
              >
                {/* Rendered as Markdown: the tutor writes tables (catalán
                    vs español pronouns), bold, and lists — raw pipes and
                    asterisks made those unreadable. */}
                <TutorMarkdown content={msg.content} />
              </Annotatable>
            ),
          )}
          {sendMutation.isPending && (
            <div className="me-8 bg-white border border-gray-100 shadow-sm rounded-2xl rounded-es-sm px-4 py-2.5 text-sm">
              {streamingText ? (
                <span dir="auto" className="text-gray-800">
                  {/* Markdown live during the stream too — a half-arrived
                      table flickers less than raw pipes snapping into a
                      table at the end. */}
                  <TutorMarkdown content={streamingText} />
                  <span className="text-lang/70">▍</span>
                </span>
              ) : (
                <span className="text-gray-500">{t('tutor.thinking')}</span>
              )}
              {/* An escape hatch from a turn that isn't coming back. The
                  server's heartbeat keeps the connection alive while the
                  model thinks, which is right — but it also means a stalled
                  turn looks exactly like a slow one, and there was no way
                  out but to leave the page. */}
              <button
                type="button"
                onClick={handleStop}
                className="mt-1 block text-xs text-gray-500 hover:text-gray-600 hover:underline"
              >
                {t('tutor.stop')}
              </button>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* "End session" lives in the header, so ending a long conversation
            meant scrolling the whole thing back up by hand. These jump to
            either end in one tap — up to finish, down to get back to where
            you were typing. */}
        {messages.length > 0 && (
          <div className="pointer-events-none absolute end-5 bottom-28 z-10 flex flex-col gap-1.5">
            <button
              type="button"
              aria-label={t('tutor.scrollTop')}
              title={t('tutor.scrollTopTitle')}
              onClick={() =>
                scrollRef.current?.scrollTo?.({ top: 0, behavior: 'smooth' })
              }
              className="pointer-events-auto flex h-9 w-9 items-center justify-center rounded-full border border-gray-200 bg-white/90 text-gray-500 shadow-sm backdrop-blur hover:text-gray-800"
            >
              <ArrowUp aria-hidden className="h-4 w-4" />
            </button>
            <button
              type="button"
              aria-label={t('tutor.scrollBottom')}
              title={t('tutor.scrollBottomTitle')}
              onClick={() =>
                bottomRef.current?.scrollIntoView?.({ behavior: 'smooth' })
              }
              className="pointer-events-auto flex h-9 w-9 items-center justify-center rounded-full border border-gray-200 bg-white/90 text-gray-500 shadow-sm backdrop-blur hover:text-gray-800"
            >
              <ArrowDown aria-hidden className="h-4 w-4" />
            </button>
          </div>
        )}

        {sendError && (
          <div
            role="alert"
            className="mb-2 bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl px-4 py-2"
          >
            {sendError}
          </div>
        )}

        {/* Input — or the exhausted panel when the allowance is spent */}
        {exhausted && allowance ? (
          <div
            className="bg-white border border-gray-200 rounded-2xl p-4 text-sm text-gray-700 space-y-2"
            data-testid="tutor-exhausted"
          >
            {['free', 'single', 'all'].includes(allowance.tier) ? (
              <>
                <p>
                  {t('tutor.exhaustedFree', {
                    date: resetDay(allowance.resets_at, i18n.language) ?? t('tutor.soon'),
                  })}
                </p>
                <p className="text-gray-500">
                  <Trans
                    i18nKey="tutor.plusPitch"
                    components={{ strong: <strong /> }}
                  />
                </p>
                <button
                  type="button"
                  onClick={() => subscribeMutation.mutate()}
                  disabled={subscribeMutation.isPending}
                  className="bg-lang hover:bg-lang-dark disabled:opacity-50 text-lang-on font-semibold rounded-xl px-5 py-2.5 text-sm"
                  style={{ minHeight: '44px' }}
                >
                  {subscribeMutation.isPending
                    ? t('tutor.starting')
                    : t('tutor.getPlus', {
                        language: languageDisplayName(language.code, language.name, i18n.language),
                      })}
                </button>
                {subscribeMutation.isError && (
                  <p className="text-xs text-red-500">
                    {t('tutor.checkoutError')}
                  </p>
                )}
              </>
            ) : (
              <p>
                {t('tutor.exhaustedPaid', {
                  date: resetDay(allowance.resets_at, i18n.language) ?? t('tutor.soon'),
                })}
              </p>
            )}
          </div>
        ) : (
          <form
            /* Pinned to the bottom of the viewport, not to the bottom of the
             * page. The column is `min-h-screen`, so it has no ceiling: the
             * message list is `flex-1 overflow-y-auto` but nothing constrains
             * its height, so it grows with the conversation instead of
             * scrolling inside itself, the document grows past the viewport,
             * and this box gets pushed under the fold. Reported as "the entry
             * bar is at the bottom of the screen and sometimes hidden because
             * you need to scroll down but don't know that" — the worst kind
             * of missing control, because nothing on screen suggests there is
             * anywhere to scroll to.
             *
             * `sticky bottom-0` rather than giving the column a fixed height:
             * StaffBar renders as a SIBLING above this page in ProtectedRoute,
             * so an `h-screen` here would be a full viewport BELOW that bar
             * and would push the composer under the fold by exactly the bar's
             * height — for staff only, which is who reported it. Sticky needs
             * no such arithmetic and is right whatever sits above.
             *
             * The background is opaque on purpose: messages scroll underneath
             * this, and a transparent bar would let them read through it. */
            className="sticky bottom-0 z-10 flex gap-2 bg-gray-50 pt-2 pb-[max(0.5rem,env(safe-area-inset-bottom))]"
            onSubmit={(e) => {
              e.preventDefault()
              handleSend()
            }}
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.nativeEvent.isComposing) {
                  e.preventDefault()
                  handleSend()
                }
              }}
              enterKeyHint="send"
              placeholder={t('tutor.inputPlaceholder')}
              dir={language.rtl ? 'auto' : 'ltr'}
              className="flex-1 rounded-xl border border-gray-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-lang bg-white"
              style={{ minHeight: '44px' }}
            />
            <button
              type="submit"
              disabled={!input.trim() || sendMutation.isPending}
              className="bg-lang hover:bg-lang-dark disabled:opacity-50 text-lang-on font-semibold rounded-xl px-5 text-sm transition-colors"
              style={{ minHeight: '44px' }}
            >
              {t('tutor.send')}
            </button>
          </form>
        )}
        <AiDisclaimer className="mt-1.5 text-center" />
      </div>
    </div>
  )
}
