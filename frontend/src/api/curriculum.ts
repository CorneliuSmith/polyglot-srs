import apiClient from './client'
import type { ReferenceLink, RelatedPoint } from './types'

export interface CurriculumPoint {
  id: string
  title: string
  level: string | null
  function_note: string | null
  reviewed: boolean
  learnable: boolean
  learned: boolean
}

export interface CurriculumPointDetail {
  id: string
  title: string
  level: string | null
  function_note: string | null
  explanation: string | null
  culture_note: string | null
  reviewed: boolean
  learned: boolean
  learnable: boolean
  references: ReferenceLink[]
  read_refs?: string[]
  related?: RelatedPoint[]
  examples: { sentence: string; translation: string | null; hint: string | null }[]
}

export async function getCurriculum(languageId: string): Promise<CurriculumPoint[]> {
  const response = await apiClient.get<{ points: CurriculumPoint[] }>(
    `/api/curriculum/${languageId}`,
  )
  return response.data.points
}

export async function getCurriculumPoint(
  grammarPointId: string,
): Promise<CurriculumPointDetail> {
  const response = await apiClient.get<CurriculumPointDetail>(
    `/api/curriculum/point/${grammarPointId}`,
  )
  return response.data
}

export async function setReferenceRead(
  grammarPointId: string,
  refKey: string,
  read: boolean,
): Promise<{ ref_key: string; read: boolean }> {
  const response = await apiClient.post(
    `/api/curriculum/point/${grammarPointId}/reference-read`,
    { ref_key: refKey, read },
  )
  return response.data
}

export async function learnPoint(
  grammarPointId: string,
): Promise<{ added: boolean; reason?: string; card_id?: string }> {
  const response = await apiClient.post('/api/curriculum/learn', {
    grammar_point_id: grammarPointId,
  })
  return response.data
}

export interface GrammarSearchHit {
  id: string
  title: string
  level: string | null
  function_note: string | null
  learned: boolean
}

export interface VocabSearchHit {
  id: string
  word: string
  level: string | null
  part_of_speech: string | null
  definition: string | null
  learned: boolean
}

export interface SearchResults {
  grammar: GrammarSearchHit[]
  vocabulary: VocabSearchHit[]
}

/** In-app search (WP13g) across the active language's grammar + vocabulary. */
export async function searchContent(
  languageId: string,
  q: string,
): Promise<SearchResults> {
  const response = await apiClient.get<SearchResults>('/api/curriculum/search', {
    params: { language_id: languageId, q },
  })
  return response.data
}
