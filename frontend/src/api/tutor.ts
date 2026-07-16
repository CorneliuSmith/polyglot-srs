import apiClient from './client'
import { supabase } from '../lib/supabase'

export interface TutorMessage {
  role: 'user' | 'assistant'
  content: string
}

/**
 * The message allowance for the caller's tier. Pricing is flat — the cap is
 * fair-use cost protection, shown openly, never a billing meter.
 */
export interface TutorAllowance {
  tier: 'free' | 'plus' | 'unlimited'
  unlimited: boolean
  entitled: boolean
  limit: number | null
  used: number | null
  remaining: number | null
  resets_at: string | null
}

export interface FocusItem {
  structure: string
  reason: string
}

/** A mastery star (WP19e): the tutor believes this card is already known;
 * the learner confirms or dismisses — SRS state never moves on its own. */
export interface MasterySuggestion {
  id: string
  item: string
  kind: 'vocabulary' | 'grammar'
  evidence: string | null
  created_at: string
}

export interface TutorStatus {
  available: boolean
  entitled: boolean
  allowance: TutorAllowance | null
  /** Active Focus: structures the tutor is deliberately working on. */
  focus?: FocusItem[]
  /** Pending mastery stars awaiting the learner's verdict. */
  mastery_suggestions?: MasterySuggestion[]
}

export type TutorMode = 'practice' | 'reference'

export interface TutorSessionRow {
  id: string
  summary: string
  message_count: number
  created_at: string
}

/** Past tutor sessions, newest first (the practice log). */
export async function getTutorSessions(
  languageId: string,
): Promise<TutorSessionRow[]> {
  const response = await apiClient.get<{ sessions: TutorSessionRow[] }>(
    '/api/tutor/sessions',
    { params: { language_id: languageId } },
  )
  return response.data.sessions
}

export async function getTutorStatus(
  languageId: string,
  languageCode: string,
): Promise<TutorStatus> {
  const response = await apiClient.get<TutorStatus>('/api/tutor/status', {
    params: { language_id: languageId, language_code: languageCode },
  })
  return response.data
}

export async function sendTutorMessage(
  languageId: string,
  languageCode: string,
  messages: TutorMessage[],
  mode: TutorMode = 'practice',
): Promise<{ reply: string; allowance: TutorAllowance | null; starred: number }> {
  const response = await apiClient.post<{
    reply: string
    allowance?: TutorAllowance
    starred?: number
  }>('/api/tutor/chat', {
    language_id: languageId,
    language_code: languageCode,
    messages,
    mode,
  })
  return {
    reply: response.data.reply,
    allowance: response.data.allowance ?? null,
    starred: response.data.starred ?? 0,
  }
}

export type TutorStreamEvent =
  | { type: 'delta'; text: string }
  | { type: 'reset' }
  | {
      type: 'done'
      reply: string
      remembered: number
      starred?: number
      allowance: TutorAllowance | null
    }
  | { type: 'error'; message: string }

/** Parse complete `data: {json}` SSE lines out of a buffer; returns the
 * events found and the unconsumed remainder. Exported for tests. */
export function parseSSE(buffer: string): { events: TutorStreamEvent[]; rest: string } {
  const events: TutorStreamEvent[] = []
  const parts = buffer.split('\n\n')
  const rest = parts.pop() ?? ''
  for (const part of parts) {
    for (const line of part.split('\n')) {
      if (line.startsWith('data: ')) {
        try {
          events.push(JSON.parse(line.slice(6)))
        } catch {
          // tolerate a malformed frame rather than killing the stream
        }
      }
    }
  }
  return { events, rest }
}

/**
 * Streaming tutor turn (SSE over fetch — axios can't stream). Calls
 * onDelta with the text so far as chunks arrive; resolves with the final
 * reply + allowance. Non-OK responses reject with an axios-shaped error
 * ({response: {status, data}}) so callers reuse their /chat handling.
 */
export async function streamTutorMessage(
  languageId: string,
  languageCode: string,
  messages: TutorMessage[],
  onDelta: (textSoFar: string) => void,
  mode: TutorMode = 'practice',
): Promise<{ reply: string; allowance: TutorAllowance | null; starred: number }> {
  const { data: sessionData } = await supabase.auth.getSession()
  const token = sessionData.session?.access_token
  const base = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? ''
  const resp = await fetch(`${base}/api/tutor/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      language_id: languageId,
      language_code: languageCode,
      messages,
      mode,
    }),
  })
  if (!resp.ok) {
    let data: unknown = null
    try {
      data = await resp.json()
    } catch {
      /* no body */
    }
    throw { response: { status: resp.status, data } }
  }
  if (!resp.body) throw new Error('Streaming not supported')

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let text = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const { events, rest } = parseSSE(buffer)
    buffer = rest
    for (const event of events) {
      if (event.type === 'delta') {
        text += event.text
        onDelta(text)
      } else if (event.type === 'reset') {
        text = ''
        onDelta(text)
      } else if (event.type === 'done') {
        return {
          reply: event.reply,
          allowance: event.allowance ?? null,
          starred: event.starred ?? 0,
        }
      } else if (event.type === 'error') {
        throw new Error(event.message)
      }
    }
  }
  throw new Error('Stream ended without a done event')
}

/** The learner's verdict on a mastery star: accept advances the card's
 * schedule (~a month out), dismiss clears the star. */
export async function resolveMasterySuggestion(
  suggestionId: string,
  action: 'accept' | 'dismiss',
): Promise<{ action: string; advanced: boolean }> {
  const response = await apiClient.post<{ action: string; advanced: boolean }>(
    `/api/tutor/suggestions/${suggestionId}`,
    { action },
  )
  return response.data
}

/**
 * Tell the backend a session is over so it can summarize the conversation
 * into the learner's durable memory. Best-effort — callers ignore failures.
 */
export async function endTutorSession(
  languageId: string,
  languageCode: string,
  messages: TutorMessage[],
): Promise<void> {
  await apiClient.post('/api/tutor/session/end', {
    language_id: languageId,
    language_code: languageCode,
    messages,
  })
}
