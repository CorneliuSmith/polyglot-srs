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

export async function generateReading(
  languageId: string,
  languageCode: string,
  topic: string,
): Promise<{ id: string; reading: Omit<Reading, 'id' | 'topic'>; level: string; allowance: TutorAllowance }> {
  const response = await apiClient.post('/api/reader/generate', {
    language_id: languageId,
    language_code: languageCode,
    topic,
  })
  return response.data
}

export async function getReadings(languageId: string): Promise<ReadingSummary[]> {
  const response = await apiClient.get<{ readings: ReadingSummary[] }>(
    '/api/reader/readings',
    { params: { language_id: languageId } },
  )
  return response.data.readings
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
