import apiClient from './client'
import type {
  DueCard,
  ValidateAnswerRequest,
  ValidateAnswerResponse,
  SubmitReviewRequest,
  SubmitReviewResponse,
  LearnResponse,
} from './types'

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

export async function startLearnSession(
  languageId: string,
): Promise<LearnResponse> {
  const response = await apiClient.post<LearnResponse>('/api/review/learn', {
    language_id: languageId,
  })
  return response.data
}
