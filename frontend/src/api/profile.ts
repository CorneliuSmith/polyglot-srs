import apiClient from './client'
import type { Language, UserProfile, ProfileUpdate } from './types'

export async function getProfile(): Promise<UserProfile> {
  const response = await apiClient.get<UserProfile>('/api/auth/profile')
  return response.data
}

export async function updateProfile(data: ProfileUpdate): Promise<UserProfile> {
  const response = await apiClient.post<UserProfile>('/api/auth/profile', data)
  return response.data
}

/**
 * The language the learner reads HELP in — glosses, translations, tutor
 * and Speak explanations. The same rule the backend resolves in
 * repositories/profile.py, stated once for the frontend:
 *
 *   explicit Settings choice (support_locale)  →  wins
 *   otherwise                                  →  the interface language
 *
 * The automatic case is DERIVED, never stored. Storing it is how the app
 * got into "interface in English, corrections in French": the globe once
 * materialized the automatic case into support_locale, which then counted
 * as a choice and stopped following.
 */
export function effectiveSupportLocale(
  profile:
    | Pick<UserProfile, 'support_locale' | 'ui_language'>
    | null
    | undefined,
): string {
  return profile?.support_locale ?? profile?.ui_language ?? 'en'
}

export async function getLanguages(): Promise<Language[]> {
  const response = await apiClient.get<Language[]>('/api/languages/')
  return response.data
}
