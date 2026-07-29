import apiClient from './client'

/** One media pick in a weekly batch. */
export interface RecoItem {
  type: string // book | film | series | podcast | music
  title: string
  creator?: string
  year?: string
  blurb: string
  why: string
  level: string
  /** The work's genre — 'crime drama', 'indie folk', 'true crime'. */
  genre?: string
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

/**
 * Draft a batch.
 *
 * Default (force=false) is the passive weekly draft the page fires on load —
 * idempotent server-side, so it only spends a model call when a batch is
 * actually due.
 *
 * force=true is the learner pressing "Get new picks": drafts immediately
 * against their CURRENT level and progress, ignoring the weekly window. Has
 * its own daily rate limit, so this can throw 429 where the passive call
 * never does.
 *
 * Throws 402 when the account isn't tutor+, 409 when the feature is off.
 */
export async function refreshRecommendations(
  languageId: string,
  force = false,
): Promise<RefreshResult> {
  const { data } = await apiClient.post<RefreshResult>(
    `/api/recommendations/${languageId}/refresh`,
    null,
    force ? { params: { force: true } } : undefined,
  )
  return data
}

/** The newest batch the learner hasn't looked at yet — backs the weekly
 *  dashboard prompt. null when there's nothing new (or the feature is off). */
export async function getUnseenRecommendations(
  languageId: string,
): Promise<RecoBatch | null> {
  const { data } = await apiClient.get<{ batch: RecoBatch | null }>(
    `/api/recommendations/${languageId}/unseen`,
  )
  return data.batch
}

/** Dismiss the prompt — server-side, so it settles on every device. */
export async function markRecommendationsSeen(): Promise<void> {
  await apiClient.post('/api/recommendations/seen')
}

export const MEDIA_TYPE_LABELS: Record<string, string> = {
  book: 'Book',
  film: 'Film',
  series: 'Series',
  podcast: 'Podcast',
  music: 'Music',
}
