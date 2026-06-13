import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { getLanguages } from '../../api/profile'
import { endTutorSession, getTutorStatus, sendTutorMessage } from '../../api/tutor'
import type { TutorMessage } from '../../api/tutor'
import { usePrefsStore } from '../../stores/prefsStore'

// Summarize into memory after this long without activity.
const IDLE_MS = 3 * 60 * 1000

export default function TutorPage() {
  const navigate = useNavigate()
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)
  const [messages, setMessages] = useState<TutorMessage[]>([])
  const [input, setInput] = useState('')
  const [sendError, setSendError] = useState<string | null>(null)
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

  const sendMutation = useMutation({
    mutationFn: (history: TutorMessage[]) =>
      sendTutorMessage(activeLanguageId!, language!.code, history),
    onSuccess: (reply) => {
      setMessages((prev) => [...prev, { role: 'assistant', content: reply }])
      setSendError(null)
    },
    onError: () => {
      setSendError('The tutor could not respond. Check your connection and try again.')
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

  if (!status.entitled) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="text-center space-y-4 max-w-md">
          <h1 className="text-2xl font-bold text-gray-900">AI Tutor</h1>
          <p className="text-gray-600">
            The {language.name} tutor is a paid add-on. It coaches you on the
            exact words you keep missing in reviews — subscribe to unlock it.
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

        {/* Input */}
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
      </div>
    </div>
  )
}
