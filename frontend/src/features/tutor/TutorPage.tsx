import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getLanguages } from '../../api/profile'
import { createCheckout } from '../../api/billing'
import { endTutorSession, getTutorStatus, sendTutorMessage } from '../../api/tutor'
import type { TutorAllowance, TutorMessage } from '../../api/tutor'
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

  const sendMutation = useMutation({
    mutationFn: (history: TutorMessage[]) =>
      sendTutorMessage(activeLanguageId!, language!.code, history),
    onSuccess: ({ reply, allowance: fresh }) => {
      setMessages((prev) => [...prev, { role: 'assistant', content: reply }])
      setSendError(null)
      if (fresh) setLiveAllowance(fresh)
    },
    onError: (err) => {
      const detail = (err as {
        response?: { status?: number; data?: { detail?: { code?: string } } }
      })?.response
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
            className="text-indigo-600 hover:underline text-sm"
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
            className="text-sm text-indigo-600 hover:underline"
          >
            End session
          </button>
        </div>

        {/* Allowance meter — flat pricing, so the cap is always visible */}
        {allowance && !allowance.unlimited && !exhausted && (
          <p className="text-xs text-gray-400 mb-3" data-testid="tutor-allowance">
            {allowance.tier === 'free' ? (
              <>
                {allowance.remaining} of {allowance.limit} free messages left this
                month.{' '}
                <button
                  type="button"
                  onClick={() => subscribeMutation.mutate()}
                  className="text-indigo-500 hover:underline"
                >
                  Plus
                </button>{' '}
                is a flat price — never per message — with a daily fair-use cap
                instead.
              </>
            ) : (
              <>
                Plus · {allowance.remaining} of {allowance.limit} messages left
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
                  ? 'ml-8 bg-indigo-600 text-white rounded-2xl rounded-br-sm px-4 py-2.5 text-sm whitespace-pre-wrap'
                  : 'mr-8 bg-white border border-gray-100 shadow-sm rounded-2xl rounded-bl-sm px-4 py-2.5 text-sm text-gray-800 whitespace-pre-wrap'
              }
            >
              {/* dir=auto: tutor turns mix English explanations with RTL practice text */}
              <span dir="auto">{msg.content}</span>
            </div>
          ))}
          {sendMutation.isPending && (
            <div className="mr-8 bg-white border border-gray-100 shadow-sm rounded-2xl rounded-bl-sm px-4 py-2.5 text-sm text-gray-400">
              Tutor is thinking…
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
            {allowance.tier === 'free' ? (
              <>
                <p>
                  You’ve used this month’s {allowance.limit} free tutor
                  messages — they come back on {resetDay(allowance.resets_at)}.
                </p>
                <p className="text-gray-500">
                  Plus is a <strong>flat price</strong>: you’re never charged
                  per message. It swaps the monthly trial for a generous daily
                  fair-use cap that resets every day.
                </p>
                <button
                  type="button"
                  onClick={() => subscribeMutation.mutate()}
                  disabled={subscribeMutation.isPending}
                  className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold rounded-xl px-5 py-2.5 text-sm"
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
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSend()
              }}
              placeholder="Message your tutor…"
              dir={language.rtl ? 'auto' : 'ltr'}
              className="flex-1 rounded-xl border border-gray-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
              style={{ minHeight: '44px' }}
            />
            <button
              type="button"
              onClick={handleSend}
              disabled={!input.trim() || sendMutation.isPending}
              className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold rounded-xl px-5 text-sm transition-colors"
              style={{ minHeight: '44px' }}
            >
              Send
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
