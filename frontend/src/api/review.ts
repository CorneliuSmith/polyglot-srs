import apiClient from './client'
import type {
  CardDetail,
  DueCard,
  ValidateAnswerRequest,
  ValidateAnswerResponse,
  SubmitReviewRequest,
  SubmitReviewResponse,
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
): Promise<LearnResponse> {
  const response = await apiClient.post<LearnResponse>('/api/review/learn', {
    language_id: languageId,
    card_type: cardType,
  })
  return response.data
}
