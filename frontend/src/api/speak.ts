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

/** Card material built from the learner's OWN corrected sentence. Null when
 * the session produced nothing a cloze could be made from — the server checks
 * that `answer` really appears in `sentence`, so an Add button is never
 * offered for a card that would be rejected on save. */
export interface SpeakCard {
  sentence: string
  answer: string
  translation: string
}

/** A recurring problem, grouped by what the learner needs to understand
 * rather than by error label — three pronoun slips are one group. */
export interface SpeakGroup {
  label: string
  note: string
  examples: string[]
  count: number
  card: SpeakCard | null
}

export interface SpeakVocabulary {
  term: string
  meaning: string
  /** A sentence from this conversation using the term, so the word can be
   * practised where they met it rather than as a bare pair. */
  example?: string
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

/** 'flow' holds every correction back until the summary; 'coach' shows one
 * per turn. Both end with the same summary — flow is not "no feedback", it
 * is "feedback that does not interrupt". */
export type SpeakMode = 'flow' | 'coach'

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
  mode: SpeakMode = 'flow',
): Promise<{
  session_id: string
  mode: SpeakMode
  topic: string | null
  /** The partner's first line when the learner left the topic blank and
   * asked it to start. Null when they named a topic, or when the opener
   * could not be generated and they should start instead. */
  opening: string | null
}> {
  const response = await apiClient.post('/api/speak/start', {
    language_id: languageId,
    language_code: languageCode,
    mode,
    topic: topic || null,
  })
  return response.data
}

export async function sendSpeakTurn(
  sessionId: string,
  text: string,
): Promise<{
  reply: string
  turn_index: number
  allowance: TutorAllowance
  /** Coach mode only, and at most one — never a list. Absent in flow mode,
   * null when the turn was clean. */
  correction?: SpeakError | null
}> {
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
