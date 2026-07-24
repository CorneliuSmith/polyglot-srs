import apiClient from './client'

/** One media pick in a weekly batch. */
export interface RecoItem {
  type: string // book | film | series | podcast
  title: string
  creator?: string
  year?: string
  blurb: string
  why: string
  level: string
}

/** A generated batch, kept in the history. */
export interface RecoBatch {
  id: string
  items: RecoItem[]
  level: string | null
  created_at: string
}

/** The learner's opt-in recommendation settings. */
export interface RecoProfile {
  enabled: boolean
  about: string
  genres: string[]
  media_types: string[]
}

/** State for one language: on/off, entitlement, freshness, and full history. */
export interface RecoState {
  enabled: boolean
  entitled: boolean
  stale: boolean
  batches: RecoBatch[]
}

export interface RefreshResult {
  generated: boolean
  batch: RecoBatch | null
}

export async function getRecoProfile(): Promise<RecoProfile> {
  const { data } = await apiClient.get<RecoProfile>('/api/recommendations/profile')
  return data
}

export async function updateRecoProfile(
  profile: RecoProfile,
): Promise<RecoProfile> {
  const { data } = await apiClient.put<RecoProfile>(
    '/api/recommendations/profile',
    profile,
  )
  return data
}

export async function getRecommendations(languageId: string): Promise<RecoState> {
  const { data } = await apiClient.get<RecoState>(
    `/api/recommendations/${languageId}`,
  )
  return data
}

/** Draft this week's batch if one is due (idempotent server-side). Throws 402
 * when the account isn't tutor+, 409 when the feature is off. */
export async function refreshRecommendations(
  languageId: string,
): Promise<RefreshResult> {
  const { data } = await apiClient.post<RefreshResult>(
    `/api/recommendations/${languageId}/refresh`,
  )
  return data
}

export const MEDIA_TYPE_LABELS: Record<string, string> = {
  book: 'Book',
  film: 'Film',
  series: 'Series',
  podcast: 'Podcast',
}

export const MEDIA_TYPE_ICONS: Record<string, string> = {
  book: '📖',
  film: '🎬',
  series: '📺',
  podcast: '🎧',
}
