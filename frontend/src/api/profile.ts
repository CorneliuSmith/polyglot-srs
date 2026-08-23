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

/** Switch yourself between variants of an experiment the admin has opened
 *  to learner choice. `variant: null` gives you back whatever the rollout
 *  says — "whatever everyone else is getting" is a real answer. */
export async function chooseExperimentVariant(
  key: string,
  variant: string | null,
): Promise<{ key: string; variant: string | null }> {
  const response = await apiClient.post('/api/auth/experiment', { key, variant })
  return response.data
}

/** Rollouts this account may switch itself between — only the ones an admin
 *  has opened to learner choice, so the page can never offer a switch the
 *  server would refuse. */
export interface ChoosableExperiment {
  key: string
  name: string
  description: string | null
  variants: { key: string; label: string }[]
  current: string
  /** False when the admin chooses for the account: the section still shows
   *  what this account is on, with the feedback box — just no switch. */
  learner_choice: boolean
}

export async function getMyExperiments(): Promise<ChoosableExperiment[]> {
  const response = await apiClient.get('/api/auth/experiments')
  return response.data.experiments
}
