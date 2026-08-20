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

/** Two separate facts, and neither implies the other. Speak can LISTEN to
 * Hebrew, Persian, Indonesian and Filipino, which have no neural voice; it
 * cannot listen to Latin or Māori, which do have one in the reader. A course
 * missing either half keeps the typed path — permanently, not as a stopgap. */
export interface SpeakSpeech {
  listen: boolean
  speak: boolean
}

export interface SpeakStatus {
  available: boolean
  allowance: TutorAllowance | null
  sessions: SpeakSessionRow[]
  speech: SpeakSpeech
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
  /** That same line in the learner's own language, produced by the same
   * call. Null when there is no opener, or when the model gave none. */
  opening_translation: string | null
}> {
  const response = await apiClient.post('/api/speak/start', {
    language_id: languageId,
    language_code: languageCode,
    mode,
    topic: topic || null,
  })
  return response.data
}

/**
 * One recorded turn → text. The audio is not stored anywhere, by the
 * browser or the server; it exists for the length of this request.
 *
 * Deliberately does NOT chain into sendSpeakTurn. The transcript comes
 * back for the learner to read and fix first — ASR mishears an accented
 * beginner, and being corrected for a word you did not say is the fastest
 * way to stop trusting the feature.
 *
 * An empty string is a real answer: they pressed and released without
 * saying anything.
 */
export async function transcribeTurn(
  sessionId: string,
  audio: Blob,
  audioMs?: number,
): Promise<string> {
  const form = new FormData()
  form.append('session_id', sessionId)
  // The filename matters only in that Azure reads its extension; the
  // server derives the real format from the blob's type.
  form.append('audio', audio, 'turn')
  // Speech-to-text is billed by the second, and the server never sees the
  // clip's duration — only its bytes, which vary by codec. The recorder
  // already knows how long it ran, so it tells the cost ledger.
  if (audioMs != null) form.append('audio_ms', String(Math.round(audioMs)))
  const response = await apiClient.post('/api/speak/transcribe', form)
  return response.data.text ?? ''
}

/** The partner's line as audio, base64 MP3. `slow` is "say that again" —
 * the same sentence at a pace you can actually pick apart. */
export async function speakPartnerLine(
  sessionId: string,
  turnIndex: number,
  slow = false,
): Promise<string> {
  const response = await apiClient.post('/api/speak/say', {
    session_id: sessionId,
    turn_index: turnIndex,
    slow,
  })
  return response.data.audio_b64
}

export async function sendSpeakTurn(
  sessionId: string,
  text: string,
  /** How long they spoke, when they spoke. Omitted for a typed turn — the
   * summary's speaking share counts measured audio only. */
  audioMs?: number,
): Promise<{
  reply: string
  /** What the reply means, in the learner's own language — sent WITH the
   * reply, never fetched on demand. "What did that mean?" has to be a tap
   * on something already here, not a second wait. Null when the model
   * gave none. */
  reply_translation: string | null
  turn_index: number
  allowance: TutorAllowance
  /** Coach mode only, and at most one — never a list. Absent in flow mode,
   * null when the turn was clean. */
  correction?: SpeakError | null
}> {
  const response = await apiClient.post('/api/speak/turn', {
    session_id: sessionId,
    text,
    audio_ms: audioMs ?? null,
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
