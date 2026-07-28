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
  /** 1 on a first placement, 2+ on a retake. */
  attempt?: number
  previous_level?: string | null
}

export interface PlacementScore {
  estimated_level: string
  per_level: Record<string, { correct: number; total: number }>
  attempt?: number
  previous_level?: string | null
}

export interface PlacementAttempt {
  estimated_level: string | null
  items_asked: number
  taken_at: string
}

export interface PlacementHistory {
  attempts: number
  has_placed: boolean
  last_level: string | null
  last_taken_at: string | null
  history: PlacementAttempt[]
}

/**
 * Whether this learner has ever placed in this language. Drives the
 * first-time offer (never placed → ask) and the retake entry in settings
 * (placed → show the previous estimate to measure against).
 */
export async function getPlacementHistory(
  languageId: string,
): Promise<PlacementHistory> {
  const response = await apiClient.get<PlacementHistory>(
    `/api/onboarding/placement/${languageId}/history`,
  )
  return response.data
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
  attempt?: number
  previous_level?: string | null
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

/** Whether the optional write-something level baseline is offered (token
 * guard: entitled/paid accounts or dev-mock only). */
export async function getWritingAvailability(
  languageId: string,
): Promise<{ available: boolean }> {
  const response = await apiClient.get(
    '/api/onboarding/writing-sample/availability',
    { params: { language_id: languageId } },
  )
  return response.data
}

export interface WritingAssessment {
  level: string
  notes: string
  focus: string[]
}

/** Assess a short free-writing sample: returns a CEFR estimate + note, and
 * primes the tutor/reader with the result server-side. */
export async function assessWritingSample(
  languageId: string,
  languageCode: string,
  text: string,
): Promise<WritingAssessment> {
  const response = await apiClient.post('/api/onboarding/writing-sample', {
    language_id: languageId,
    language_code: languageCode,
    text,
  })
  return response.data
}

/** Change the learner's level any time (Settings → Your level). SET
 * semantics server-side: decks at/below the level are queued, decks above
 * it are unqueued; learned cards are never touched. */
export async function setLearnerLevel(
  languageId: string,
  level: string,
): Promise<{ level: string; subscribed: number; unsubscribed: number }> {
  const response = await apiClient.put('/api/onboarding/level', {
    language_id: languageId,
    level,
  })
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
