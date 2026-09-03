import apiClient from './client'
import { supabase } from '../lib/supabase'

export interface TutorMessage {
  role: 'user' | 'assistant'
  content: string
}

/**
 * The monthly usage pool for the caller's tier. Pricing is flat — the cap is
 * fair-use cost protection, surfaced only as the Claude-style percentage
 * meter (components/UsageMeter), never a billing meter.
 */
export interface TutorAllowance {
  tier: 'free' | 'single' | 'all' | 'plus' | 'granted' | 'unlimited' | 'blocked'
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

/** The usage-pool meter alone, independent of tutor-persona availability —
 * for surfaces (Gym, Reader) that draw the same monthly pool without
 * offering a tutor persona for every language. See UsageMeter. */
export async function getUsageAllowance(
  languageId: string,
): Promise<{ available: boolean; allowance: TutorAllowance | null }> {
  const response = await apiClient.get('/api/tutor/allowance', {
    params: { language_id: languageId },
  })
  return response.data
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
/**
 * The server said the turn failed, or the learner pressed Stop. Either way
 * the caller must NOT retry on the non-streaming endpoint: the server already
 * gave its verdict, and retrying spends a second full model call to be told
 * the same thing (or, on Stop, to send a message the learner cancelled).
 */
export class TutorTurnError extends Error {
  readonly aborted: boolean
  constructor(message: string, aborted = false) {
    super(message)
    this.name = 'TutorTurnError'
    this.aborted = aborted
  }
}

/** No byte from the server for this long means the turn is dead. The server
 * pings every 10s while the model thinks, so silence here is a broken
 * connection, not a slow answer — without this the reader simply waits for a
 * FIN that a dropped mobile connection never sends. */
const STREAM_SILENCE_TIMEOUT_MS = 45_000

export async function streamTutorMessage(
  languageId: string,
  languageCode: string,
  messages: TutorMessage[],
  onDelta: (textSoFar: string) => void,
  mode: TutorMode = 'practice',
  signal?: AbortSignal,
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
    signal,
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
  try {
    for (;;) {
      // Race the read against a silence timer. Without it a connection that
      // dies without closing (the phone changing networks mid-answer) leaves
      // reader.read() pending forever and the UI stuck on "thinking".
      let timer: ReturnType<typeof setTimeout> | undefined
      const silence = new Promise<never>((_, reject) => {
        timer = setTimeout(
          () => reject(new TutorTurnError('The tutor stopped responding — try again.')),
          STREAM_SILENCE_TIMEOUT_MS,
        )
      })
      let chunk: ReadableStreamReadResult<Uint8Array>
      try {
        chunk = await Promise.race([reader.read(), silence])
      } finally {
        clearTimeout(timer)
      }
      if (chunk.done) break
      buffer += decoder.decode(chunk.value, { stream: true })
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
          // The server's verdict, not a transport hiccup — don't retry.
          throw new TutorTurnError(event.message)
        }
      }
    }
  } catch (err) {
    if (signal?.aborted || (err as Error)?.name === 'AbortError') {
      throw new TutorTurnError('Stopped.', true)
    }
    throw err
  } finally {
    reader.cancel().catch(() => {})
  }
  throw new Error('Stream ended without a done event')
}

/** One durable fact the tutor holds about the learner. `source` is its
 * provenance: 'stated' = the learner said it about themselves; 'inferred' =
 * an AI's deduction (or a fact recorded before provenance was tracked). */
export interface TutorMemoryFact {
  key: string
  value: string | string[]
  source: 'stated' | 'inferred'
}

export interface TutorMemory {
  global: TutorMemoryFact[]
  languages: {
    language_id: string
    name: string
    code: string
    facts: TutorMemoryFact[]
    /** The rolling summary the post-session summarizer rewrites — the
     * largest free text the tutor keeps about a learner. */
    session_summary?: string | null
    /** The tutor-managed Active Focus list (structures under work). */
    focus?: string[]
  }[]
}

/** Forget everything for one language, or with no id every language and
 * the global profile. Past session records stay — they are history. */
export async function forgetTutorMemory(languageId?: string): Promise<void> {
  await apiClient.delete('/api/tutor/memory/all', {
    params: languageId ? { language_id: languageId } : {},
  })
}

/** Everything the tutor remembers about the caller — the Settings panel's
 * window into (and veto over) the AI-maintained learner profile. */
export async function getTutorMemory(): Promise<TutorMemory> {
  const response = await apiClient.get<TutorMemory>('/api/tutor/memory')
  return response.data
}

export async function deleteTutorMemoryFact(input: {
  scope: 'global' | 'language'
  key: string
  languageId?: string
}): Promise<void> {
  await apiClient.delete('/api/tutor/memory', {
    params: {
      scope: input.scope,
      key: input.key,
      ...(input.languageId ? { language_id: input.languageId } : {}),
    },
  })
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
