import { apiClient } from './client'

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
