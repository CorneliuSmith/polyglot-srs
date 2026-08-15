import apiClient from './client'
import type { TutorAllowance } from './tutor'

/** One mistake the partner noticed. Never sent to the client during a flow
 * session — these only ever arrive grouped, inside the summary. */
export interface SpeakError {
  type: string
  learner_said: string
  should_be: string
  note: string
}

/** A recurring problem, grouped by what the learner needs to understand
 * rather than by error label — three pronoun slips are one group. */
export interface SpeakGroup {
  label: string
  note: string
  examples: string[]
  count: number
}

export interface SpeakVocabulary {
  term: string
  meaning: string
}

/** Counts, deliberately not a score: the plan is explicit that the moment
 * there is a number, flow mode becomes a thing to game. */
export interface SpeakStats {
  turns: number
  error_count: number
  types: Record<string, number>
}

export interface SpeakSummary {
  groups: SpeakGroup[]
  vocabulary: SpeakVocabulary[]
  stats: SpeakStats
}

export interface SpeakSessionRow {
  id: string
  mode: string
  topic: string | null
  started_at: string
  ended_at: string | null
  turn_count: number
}

export interface SpeakStatus {
  available: boolean
  allowance: TutorAllowance | null
  sessions: SpeakSessionRow[]
}

export async function getSpeakStatus(languageId: string): Promise<SpeakStatus> {
  const response = await apiClient.get('/api/speak/status', {
    params: { language_id: languageId },
  })
  return response.data
}

export async function startSpeakSession(
  languageId: string,
  languageCode: string,
  topic?: string,
): Promise<{ session_id: string; mode: string; topic: string | null }> {
  const response = await apiClient.post('/api/speak/start', {
    language_id: languageId,
    language_code: languageCode,
    mode: 'flow',
    topic: topic || null,
  })
  return response.data
}

export async function sendSpeakTurn(
  sessionId: string,
  text: string,
): Promise<{ reply: string; turn_index: number; allowance: TutorAllowance }> {
  const response = await apiClient.post('/api/speak/turn', {
    session_id: sessionId,
    text,
  })
  return response.data
}

export async function endSpeakSession(
  sessionId: string,
): Promise<{ summary: SpeakSummary; already_ended: boolean }> {
  const response = await apiClient.post('/api/speak/end', {
    session_id: sessionId,
  })
  return response.data
}
