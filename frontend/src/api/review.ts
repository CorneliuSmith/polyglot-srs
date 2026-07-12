import apiClient from './client'
import type {
  CardDetail,
  DueCard,
  ValidateAnswerRequest,
  ValidateAnswerResponse,
  SubmitReviewRequest,
  SubmitReviewResponse,
  LearnDeck,
  LearnResponse,
} from './types'

export async function getCardDetail(cardId: string): Promise<CardDetail> {
  const response = await apiClient.get<CardDetail>(
    `/api/review/card/${cardId}/detail`,
  )
  return response.data
}

export async function getDueCards(
  languageId: string,
  limit?: number,
): Promise<DueCard[]> {
  const response = await apiClient.get<DueCard[]>('/api/review/due', {
    params: { language_id: languageId, ...(limit ? { limit } : {}) },
  })
  return response.data
}

export interface DeckPreview {
  id: string
  title: string
  list_type: 'vocabulary' | 'grammar'
  level: string | null
  items: { item: string; detail: string | null }[]
}

/** Peek inside a deck (its first items) before adding it to the queue. */
export async function getDeckPreview(listId: string): Promise<DeckPreview> {
  const response = await apiClient.get<DeckPreview>(
    `/api/review/decks/${listId}/preview`,
  )
  return response.data
}

/** Add or remove a deck from the learn queue (removal never loses progress). */
export async function setDeckSubscription(
  listId: string,
  subscribed: boolean,
): Promise<void> {
  await apiClient.post(`/api/review/decks/${listId}/subscription`, { subscribed })
}

/** Quick-Cram (WP13f): ungraded practice cards for a set of grammar points.
 * Nothing here touches SRS state — cram sessions never call submitReview. */
export async function getCramCards(pointIds: string[]): Promise<DueCard[]> {
  const response = await apiClient.get<DueCard[]>('/api/review/cram', {
    params: { point_ids: pointIds.join(',') },
  })
  return response.data
}

export async function validateAnswer(
  req: ValidateAnswerRequest,
): Promise<ValidateAnswerResponse> {
  const response = await apiClient.post<ValidateAnswerResponse>(
    '/api/review/validate-answer',
    req,
  )
  return response.data
}

export async function submitReview(
  req: SubmitReviewRequest,
): Promise<SubmitReviewResponse> {
  const response = await apiClient.post<SubmitReviewResponse>(
    '/api/review/submit',
    req,
  )
  return response.data
}

export async function submitCardFeedback(
  cardId: string,
  message: string,
): Promise<void> {
  await apiClient.post(`/api/review/card/${cardId}/feedback`, { message })
}

export async function startLearnSession(
  languageId: string,
  cardType: 'vocabulary' | 'grammar' = 'vocabulary',
  level?: string,
): Promise<LearnResponse> {
  const response = await apiClient.post<LearnResponse>('/api/review/learn', {
    language_id: languageId,
    card_type: cardType,
    ...(level ? { level } : {}),
  })
  return response.data
}

export async function confirmLearnSession(
  cardIds: string[],
): Promise<{ confirmed: number }> {
  const response = await apiClient.post<{ confirmed: number }>(
    '/api/review/learn/confirm',
    { card_ids: cardIds },
  )
  return response.data
}

export async function getLearnDecks(languageId: string): Promise<LearnDeck[]> {
  const response = await apiClient.get<{ decks: LearnDeck[] }>(
    '/api/review/decks',
    { params: { language_id: languageId } },
  )
  return response.data.decks
}

export async function resetDeckProgress(
  listId: string,
): Promise<{ cards_deleted: number }> {
  const response = await apiClient.delete<{ cards_deleted: number }>(
    `/api/review/decks/${listId}/progress`,
  )
  return response.data
}

export async function resetProgress(
  languageId?: string,
): Promise<{ cards_deleted: number }> {
  const response = await apiClient.delete<{ cards_deleted: number }>(
    '/api/review/progress',
    { params: languageId ? { language_id: languageId } : {} },
  )
  return response.data
}

export interface DeckItem {
  id: string
  kind: 'grammar' | 'vocabulary'
  item: string
  detail: string | null
  level: string | null
  reviewed: boolean
}

export interface DeckListing {
  id: string
  title: string
  list_type: 'grammar' | 'vocabulary'
  level: string | null
  items: DeckItem[]
}

export async function getDeckItems(listId: string): Promise<DeckListing> {
  const response = await apiClient.get<DeckListing>(
    `/api/review/decks/${listId}/items`,
  )
  return response.data
}

export interface VocabItemDetail {
  id: string
  word: string
  reading: string | null
  part_of_speech: string | null
  usage_note: string | null
  definition: string | null
  level: string | null
  language_code: string
  morphology: Record<string, unknown> | string | null
  examples: { sentence: string; translation: string | null }[]
}

export async function getVocabItem(vocabId: string): Promise<VocabItemDetail> {
  const response = await apiClient.get<VocabItemDetail>(
    `/api/review/vocab/${vocabId}`,
  )
  return response.data
}
