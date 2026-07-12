import apiClient from './client'

export interface OnboardingStatus {
  onboarded: boolean
  active_language_id: string | null
  has_subscriptions: boolean
}

export interface PlacementItem {
  id: string
  kind: 'vocabulary' | 'grammar'
  level: string
  prompt: string
  translation: string | null
}

export interface PlacementResponse {
  available: boolean
  items: PlacementItem[]
}

export interface PlacementScore {
  estimated_level: string
  per_level: Record<string, { correct: number; total: number }>
}

export interface CompleteResponse {
  subscribed: number
  active_language_id: string
  level: string
}

export async function getOnboardingStatus(): Promise<OnboardingStatus> {
  const response = await apiClient.get<OnboardingStatus>('/api/onboarding/status')
  return response.data
}

export async function getPlacement(languageId: string): Promise<PlacementResponse> {
  const response = await apiClient.get<PlacementResponse>(
    `/api/onboarding/placement/${languageId}`,
  )
  return response.data
}

export interface PlacementNextResponse {
  available: boolean
  done: boolean
  item?: PlacementItem
  asked: number
  max_items?: number
  estimated_level?: string | null
  per_level?: Record<string, { correct: number; total: number }>
}

/**
 * Adaptive placement: send the full answer history each round; the server
 * grades it, walks its level staircase, and returns the next item or the
 * final estimate. Stateless on both ends beyond the history array.
 */
export async function placementNext(
  languageId: string,
  history: { id: string; input: string }[],
): Promise<PlacementNextResponse> {
  const response = await apiClient.post<PlacementNextResponse>(
    `/api/onboarding/placement/${languageId}/next`,
    { history },
  )
  return response.data
}

export async function scorePlacement(
  languageId: string,
  answers: { id: string; input: string }[],
): Promise<PlacementScore> {
  const response = await apiClient.post<PlacementScore>(
    `/api/onboarding/placement/${languageId}`,
    { answers },
  )
  return response.data
}

export async function completeOnboarding(input: {
  languageId: string
  level: string
  batchSize?: number
  nativeLanguage?: string
  planScope?: 'single' | 'all'
}): Promise<CompleteResponse> {
  const response = await apiClient.post<CompleteResponse>('/api/onboarding/complete', {
    language_id: input.languageId,
    level: input.level,
    batch_size: input.batchSize ?? null,
    native_language: input.nativeLanguage ?? null,
    plan_scope: input.planScope ?? null,
  })
  return response.data
}
