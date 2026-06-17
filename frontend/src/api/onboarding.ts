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
}): Promise<CompleteResponse> {
  const response = await apiClient.post<CompleteResponse>('/api/onboarding/complete', {
    language_id: input.languageId,
    level: input.level,
    batch_size: input.batchSize ?? null,
    native_language: input.nativeLanguage ?? null,
  })
  return response.data
}
