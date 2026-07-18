import { useCallback, useEffect, useRef, useState } from 'react'
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
} from '../../api/tutor'
import type { TutorAllowance, TutorMessage, TutorMode } from '../../api/tutor'
import { usePrefsStore } from '../../stores/prefsStore'

// Summarize into memory after this long without activity.
const IDLE_MS = 3 * 60 * 1000

function resetDay(resetsAt: string | null): string {
  if (!resetsAt) return 'soon'
  return new Date(resetsAt).toLocaleDateString(undefined, {
    month: 'long',
    day: 'numeric',
  })
}

export default function TutorPage() {
  const navigate = useNavigate()
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
      try {
        return await streamTutorMessage(
          activeLanguageId!, language!.code, history, setStreamingText, mode,
        )
      } catch (err) {
        const status = (err as { response?: { status?: number } })?.response?.status
        if (status === 402) throw err
        setStreamingText(null)
        return sendTutorMessage(activeLanguageId!, language!.code, history, mode)
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
      } else {
        setSendError('The tutor could not respond. Check your connection and try again.')
      }
    },
  })

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
        <p className="text-gray-500">Loading tutor…</p>
      </div>
    )
  }

  if (!status?.available) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="text-center space-y-4">
          <p className="text-xl text-gray-700">
            The AI tutor isn’t available for {language.name} yet.
          </p>
          <button
            type="button"
            onClick={() => navigate('/')}
            className="text-lang hover:underline text-sm"
          >
            Back to Dashboard
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
      <div className="max-w-2xl mx-auto w-full px-4 py-6 flex flex-col flex-1">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-xl font-bold text-gray-900">
              {language.name} Tutor
            </h1>
            <p className="text-xs text-gray-500">
              Coaching based on your review history
            </p>
          </div>
          <button
            type="button"
            onClick={handleEndSession}
            className="text-sm text-lang hover:underline"
          >
            End session
          </button>
        </div>

        {/* Practice vs Reference (WP18c): reference questions get direct
            answers with no drilling and no memory writes. */}
        <div className="flex flex-wrap items-center gap-2 mb-2 text-xs">
          <div
            role="group"
            aria-label="Tutor mode"
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
              Practice
            </button>
            <button
              type="button"
              onClick={() => setMode('reference')}
              aria-pressed={mode === 'reference'}
              title="Ask a quick question — no drills, nothing saved to your profile"
              className={
                mode === 'reference'
                  ? 'px-3 py-1 bg-lang text-lang-on font-semibold'
                  : 'px-3 py-1 bg-white text-gray-500 hover:text-lang'
              }
            >
              Reference
            </button>
          </div>
          <button
            type="button"
            onClick={() => setHistoryOpen((v) => !v)}
            aria-expanded={historyOpen}
            className="text-gray-500 hover:text-lang"
          >
            {historyOpen ? 'Hide past sessions' : 'Past sessions'}
          </button>
          <button
            type="button"
            onClick={() => navigate('/read')}
            title="A text written at your level, on your topic"
            className="text-gray-500 hover:text-lang"
          >
            Read →
          </button>
        </div>

        {/* One-line explainer of the two modes (beta request). */}
        <p className="text-[11px] text-gray-400 mb-2">
          {mode === 'practice'
            ? 'Practice — the tutor drills you and remembers what you covered.'
            : 'Reference — a quick answer, no drills, nothing saved to your profile.'}
        </p>

        {/* Active Focus (WP18b): the structures the tutor is deliberately
            working on with this learner — tutor-managed, read-only here. */}
        {(status?.focus?.length ?? 0) > 0 && (
          <div
            className="flex flex-wrap items-center gap-1.5 mb-2"
            data-testid="active-focus"
          >
            <span className="text-[10px] uppercase tracking-wide text-gray-400">
              Active focus
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
              ⭐ Your tutor thinks you already know these
            </p>
            <p className="text-[11px] text-amber-800/80">
              Agree, and the card's next review moves about a month out —
              nothing changes unless you say so.
            </p>
            {status!.mastery_suggestions!.map((s) => (
              <div
                key={s.id}
                className="flex items-start justify-between gap-3 bg-white/70 rounded-lg px-2.5 py-2"
              >
                <div className="min-w-0 text-sm">
                  <span className="font-medium text-gray-900">{s.item}</span>
                  <span className="ml-1.5 text-[10px] uppercase tracking-wide text-gray-400">
                    {s.kind === 'grammar' ? 'grammar' : 'vocab'}
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
                    I know it
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
                    Keep drilling
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
              <p className="text-xs text-gray-400">
                No past sessions yet — they appear here after you end one.
              </p>
            )}
            {pastSessions.map((sess) => (
              <div key={sess.id} className="text-xs">
                <p className="text-gray-400">
                  {new Date(sess.created_at).toLocaleDateString(undefined, {
                    month: 'short', day: 'numeric',
                  })}{' '}
                  · {sess.message_count} messages
                </p>
                <p className="text-gray-700">{sess.summary}</p>
              </div>
            ))}
          </div>
        )}

        {/* Allowance meter — flat pricing, so the cap is always visible.
            free/single/all are MONTHLY (included with the plan); plus/granted
            are the DAILY fair-use tiers (Tutor+ add-on / admin grant). */}
        {allowance && !allowance.unlimited && !exhausted && (
          <p className="text-xs text-gray-400 mb-3" data-testid="tutor-allowance">
            {['free', 'single', 'all'].includes(allowance.tier) ? (
              <>
                {allowance.remaining} of {allowance.limit}{' '}
                {allowance.tier === 'free' ? 'free ' : 'included '}messages left
                this month.{' '}
                <button
                  type="button"
                  onClick={() => subscribeMutation.mutate()}
                  className="text-lang hover:underline"
                >
                  Tutor+
                </button>{' '}
                is a flat price — never per message — with a daily fair-use cap
                instead.
              </>
            ) : (
              <>
                Tutor+ · {allowance.remaining} of {allowance.limit} messages left
                today (fair use — resets daily, your price never changes).
              </>
            )}
          </p>
        )}

        {/* Messages */}
        <div
          className="flex-1 overflow-y-auto space-y-3 pb-4"
          data-testid="tutor-messages"
        >
          {messages.length === 0 && (
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 text-sm text-gray-600">
              Hi! I’m your {language.name} tutor. I can see which words you’ve
              been struggling with in your reviews. Say hello, or ask me to
              drill your weak spots.
            </div>
          )}
          {messages.map((msg, i) => (
            <div
              key={i}
              className={
                msg.role === 'user'
                  ? 'ml-8 bg-lang text-white rounded-2xl rounded-br-sm px-4 py-2.5 text-sm whitespace-pre-wrap'
                  : 'mr-8 bg-white border border-gray-100 shadow-sm rounded-2xl rounded-bl-sm px-4 py-2.5 text-sm text-gray-800 whitespace-pre-wrap'
              }
            >
              {/* dir=auto: tutor turns mix English explanations with RTL practice text */}
              <span dir="auto">{msg.content}</span>
            </div>
          ))}
          {sendMutation.isPending && (
            <div className="mr-8 bg-white border border-gray-100 shadow-sm rounded-2xl rounded-bl-sm px-4 py-2.5 text-sm">
              {streamingText ? (
                <span dir="auto" className="text-gray-800 whitespace-pre-wrap">
                  {streamingText}
                  <span className="text-lang/70">▍</span>
                </span>
              ) : (
                <span className="text-gray-400">Tutor is thinking…</span>
              )}
            </div>
          )}
          <div ref={bottomRef} />
        </div>

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
                  You’ve used this month’s {allowance.limit}{' '}
                  {allowance.tier === 'free' ? 'free' : 'included'} tutor
                  messages — they come back on {resetDay(allowance.resets_at)}.
                </p>
                <p className="text-gray-500">
                  Tutor+ is a <strong>flat price</strong>: you’re never charged
                  per message. It swaps the monthly allowance for a generous
                  daily fair-use cap that resets every day.
                </p>
                <button
                  type="button"
                  onClick={() => subscribeMutation.mutate()}
                  disabled={subscribeMutation.isPending}
                  className="bg-lang hover:bg-lang-dark disabled:opacity-50 text-lang-on font-semibold rounded-xl px-5 py-2.5 text-sm"
                  style={{ minHeight: '44px' }}
                >
                  {subscribeMutation.isPending
                    ? 'Starting…'
                    : `Get Plus for ${language.name}`}
                </button>
                {subscribeMutation.isError && (
                  <p className="text-xs text-red-500">
                    Couldn’t start checkout — try again.
                  </p>
                )}
              </>
            ) : (
              <p>
                You’ve reached today’s fair-use cap of {allowance.limit}{' '}
                messages. It resets tomorrow — nothing extra to pay, your
                price never changes with usage.
              </p>
            )}
          </div>
        ) : (
          <form
            className="flex gap-2"
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
              placeholder="Message your tutor…"
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
              Send
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
