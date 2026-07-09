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

export async function getDueCards(languageId: string): Promise<DueCard[]> {
  const response = await apiClient.get<DueCard[]>('/api/review/due', {
    params: { language_id: languageId },
  })
  return response.data
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
