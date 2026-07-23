import apiClient from './client'

export interface GymEntry {
  point_id: string
  label: string
  usage: string | null
  example: string | null
  level: string | null
  drills: number
  nonstandard: boolean
  familiar: boolean
}

export interface GymColumn {
  kind: string
  label: string
  entries: GymEntry[]
}

export interface GymManifest {
  columns: GymColumn[]
}

/** The Gym picker (WP25): selectable form categories for one language,
 * grouped verbs | nouns | adjectives. Empty columns = no Gym for this
 * language (nothing to inflect). */
export async function getGymManifest(languageId: string): Promise<GymManifest> {
  const response = await apiClient.get<GymManifest>('/api/gym/manifest', {
    params: { language_id: languageId },
  })
  return response.data
}

export interface GymGenerateResult {
  /** Drills added to the shared pool this call. */
  generated: number
  /** Tutor-message allowance left after the one message this drew, or
   * null when the account is unlimited. */
  remaining: number | null
  unlimited: boolean
}

/** WP41: top up a few EXTRA drill variations for the chosen forms on demand.
 * Draws ONE message from the learner's tutor allowance (bounded, verified,
 * tagged 'ai'). The seeded corpus stays the main path — this is for variety
 * when a form runs thin. Throws 402 when the allowance is spent, 503 when
 * on-demand generation isn't enabled. */
export async function generateGymDrills(
  pointIds: string[],
): Promise<GymGenerateResult> {
  const response = await apiClient.post<GymGenerateResult>(
    '/api/review/gym/generate',
    { point_ids: pointIds },
  )
  return response.data
}
