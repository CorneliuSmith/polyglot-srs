import apiClient from './client'
import type { TutorAllowance } from './tutor'

export interface ReaderToken {
  t: string
  gloss: string
  new?: boolean
}

export interface ReaderSentence {
  text: string
  translation: string
  tokens: ReaderToken[]
}

export interface Reading {
  id: string
  topic: string
  title: string
  level: string | null
  sentences: ReaderSentence[]
  new_words: { word: string; gloss: string; sentence_index: number }[]
  structures: string[]
  created_at?: string
}

export interface ReadingSummary {
  id: string
  topic: string
  title: string
  level: string | null
  created_at: string
  new_word_count: number
}

/** Bounded per-text options: how long, whose voice, how hard. */
export interface ReadingOptions {
  length: 'short' | 'medium' | 'long'
  voice: 'any' | 'first' | 'third' | 'dialogue'
  /** Relative, an explicit CEFR pin, or one of the registers above the
   * ladder — CEFR stops at C2, so "harder than C2" is a kind of prose
   * rather than a level. */
  complexity:
    | 'easier'
    | 'level'
    | 'stretch'
    | 'A1'
    | 'A2'
    | 'B1'
    | 'B2'
    | 'C1'
    | 'C2'
    | 'native'
    | 'academic'
    | 'literary'
}

export interface GeneratedReading {
  id: string
  reading: Omit<Reading, 'id' | 'topic'>
  level: string
  allowance: TutorAllowance
}

interface GenerateStatus extends Partial<GeneratedReading> {
  generating: boolean
  error?: string
}

/** How often to ask whether the text has landed, and how long to keep
 * asking. A graded, once-rewritten C2 text is the slow case (two full
 * generations); past this the write is not coming back. */
const POLL_MS = 3000
const GIVE_UP_MS = 5 * 60 * 1000

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))

export async function getReadingStatus(): Promise<GenerateStatus> {
  const response = await apiClient.get<GenerateStatus>(
    '/api/reader/generate/status',
  )
  return response.data
}

/**
 * Write a text, and don't hang up while it happens.
 *
 * The POST only STARTS the write now; the server hands the model call to a
 * background task and this polls until it lands. Holding one request open
 * through a graded-and-rewritten C2 text is what DigitalOcean's gateway
 * killed at about a minute — the same failure recommendations hit, fixed
 * the same way. Callers see one promise either way.
 */
export async function generateReading(
  languageId: string,
  languageCode: string,
  topic: string,
  options?: Partial<ReadingOptions>,
): Promise<GeneratedReading> {
  await apiClient.post('/api/reader/generate', {
    language_id: languageId,
    language_code: languageCode,
    topic,
    ...options,
  })

  const deadline = Date.now() + GIVE_UP_MS
  for (;;) {
    await sleep(POLL_MS)
    const status = await getReadingStatus()
    if (status.error) throw new Error(status.error)
    if (status.id && status.reading) {
      return status as GeneratedReading
    }
    // Not writing and nothing to show: the process restarted mid-write, or
    // the result was already collected. Either way it isn't coming.
    if (!status.generating) {
      throw new Error('The text stopped being written — try again.')
    }
    if (Date.now() > deadline) {
      throw new Error('Writing took too long — try again.')
    }
  }
}

export async function getReadings(languageId: string): Promise<ReadingSummary[]> {
  const response = await apiClient.get<{ readings: ReadingSummary[] }>(
    '/api/reader/readings',
    { params: { language_id: languageId } },
  )
  return response.data.readings
}

/** Remove a finished text from the shelf. Words saved out of it are the
 * learner's own cards and are untouched — nothing links one to the other. */
export async function deleteReading(readingId: string): Promise<void> {
  await apiClient.delete(`/api/reader/readings/${readingId}`)
}

export async function getReading(readingId: string): Promise<Reading> {
  const response = await apiClient.get<Reading>(
    `/api/reader/readings/${readingId}`,
  )
  return response.data
}

export async function explainSentence(
  readingId: string,
  sentenceIndex: number,
): Promise<string> {
  const response = await apiClient.post<{ explanation: string }>(
    `/api/reader/readings/${readingId}/explain`,
    { sentence_index: sentenceIndex },
  )
  return response.data.explanation
}
