import apiClient from './client'

export interface ContributorRole {
  language_id: string | null
  role: string
}

export interface ReferenceLink {
  title: string
  url: string
}

export interface GrammarPointEdit {
  id: string
  title: string
  level: string | null
  explanation: string | null
  culture_note: string | null
  explanation_source: string
  reviewed: boolean
  references: ReferenceLink[]
  ai_check_status: 'pass' | 'concerns' | null
  ai_check_notes: string | null
  reviewed_by: string | null
  reviewed_at: string | null
}

export async function getMyRoles(): Promise<{ roles: ContributorRole[]; is_admin: boolean }> {
  const response = await apiClient.get('/api/contribute/roles')
  return response.data
}

export async function getGrammarForLanguage(
  languageId: string,
): Promise<{
  points: GrammarPointEdit[]
  is_admin: boolean
  can_review: boolean
  review_policy: string
  tutor_model?: string | null
}> {
  const response = await apiClient.get('/api/contribute/grammar', {
    params: { language_id: languageId },
  })
  return response.data
}

export interface ReviewNote {
  id: string
  grammar_point_id: string
  point_title: string
  level: string | null
  note: string
  status: 'open' | 'resolved'
  author_email: string
  created_at: string | null
}

export async function flagPointIssue(pointId: string, note: string): Promise<void> {
  await apiClient.post(`/api/contribute/grammar/${pointId}/notes`, { note })
}

export async function getReviewNotes(
  languageId: string,
  includeResolved = false,
): Promise<ReviewNote[]> {
  const response = await apiClient.get('/api/contribute/notes', {
    params: { language_id: languageId, include_resolved: includeResolved },
  })
  return response.data.notes
}

export async function resolveReviewNote(noteId: string): Promise<void> {
  await apiClient.post(`/api/contribute/notes/${noteId}/resolve`)
}

/** Models an admin may assign per language; null = the global default. */
export const TUTOR_MODELS = [
  'claude-fable-5',
  'claude-opus-4-8',
  'claude-sonnet-5',
  'claude-haiku-4-5-20251001',
] as const

export async function setLanguageTutorModel(
  languageId: string,
  model: string | null,
): Promise<void> {
  await apiClient.post('/api/contribute/language-tutor-model', {
    language_id: languageId,
    model,
  })
}

export interface TutorUsageRow {
  language_id: string | null
  language_name: string | null
  model: string | null
  kind: 'chat' | 'summary'
  messages: number
  input_tokens: number
  output_tokens: number
  cache_write_tokens: number
  cache_read_tokens: number
  est_cost_usd: number
}

export interface TutorUsageSummary {
  days: number
  rows: TutorUsageRow[]
  total_messages: number
  total_est_cost_usd: number
}

/** Admin-only rollup of tutor token usage priced at list rates (WP9b). */
export async function getTutorUsage(days = 30): Promise<TutorUsageSummary> {
  const response = await apiClient.get('/api/contribute/tutor-usage', {
    params: { days },
  })
  return response.data
}

export type GrantableRole = 'contributor' | 'reviewer' | 'admin'

export interface RoleGrantRow {
  user_id: string
  email: string
  language_id: string | null
  language_code: string | null
  role: GrantableRole
  created_at: string | null
}

export async function listAllRoles(): Promise<RoleGrantRow[]> {
  const response = await apiClient.get('/api/contribute/roles/all')
  return response.data.grants
}

export async function grantRole(input: {
  email: string
  role: GrantableRole
  language_id?: string | null
}): Promise<void> {
  await apiClient.post('/api/contribute/roles', input)
}

export async function revokeRole(input: {
  user_id: string
  role: GrantableRole
  language_id?: string | null
}): Promise<void> {
  await apiClient.post('/api/contribute/roles/revoke', input)
}

export async function setLanguagePolicy(
  languageId: string,
  policy: 'strict' | 'ai_ok',
): Promise<void> {
  await apiClient.post('/api/contribute/language-policy', {
    language_id: languageId,
    policy,
  })
}

export async function saveGrammarExplanation(
  pointId: string,
  explanation: string,
  cultureNote: string,
  references: ReferenceLink[] = [],
): Promise<void> {
  await apiClient.put(`/api/contribute/grammar/${pointId}`, {
    explanation,
    culture_note: cultureNote,
    references,
  })
}

export async function approveGrammar(pointId: string): Promise<void> {
  await apiClient.post(`/api/contribute/grammar/${pointId}/approve`)
}

export async function runAiCheck(
  pointId: string,
): Promise<{ status: 'pass' | 'concerns'; notes: string }> {
  const response = await apiClient.post(`/api/contribute/grammar/${pointId}/ai-check`)
  return response.data
}

export interface Drill {
  id: string
  sentence: string
  answer: string
  translation: string | null
  hint: string | null
  display_order: number
}

export async function createGrammarPoint(input: {
  language_id: string
  title: string
  level?: string | null
  explanation?: string
  culture_note?: string
}): Promise<{ id: string }> {
  const response = await apiClient.post('/api/contribute/grammar', input)
  return response.data
}

export async function getDrills(pointId: string): Promise<Drill[]> {
  const response = await apiClient.get<{ drills: Drill[] }>(
    `/api/contribute/grammar/${pointId}/drills`,
  )
  return response.data.drills
}

export async function addDrill(
  pointId: string,
  input: { sentence: string; answer: string; translation?: string; hint?: string },
): Promise<{ id: string }> {
  const response = await apiClient.post(
    `/api/contribute/grammar/${pointId}/drills`,
    input,
  )
  return response.data
}

export async function updateDrill(
  pointId: string,
  drillId: string,
  input: {
    sentence: string
    answer: string
    translation?: string
    hint?: string
    /** required rationale — lands in the point's review notes */
    change_note: string
  },
): Promise<{ saved: boolean; reviewed: boolean }> {
  const response = await apiClient.put(
    `/api/contribute/grammar/${pointId}/drills/${drillId}`,
    input,
  )
  return response.data
}

export async function deleteDrill(pointId: string, drillId: string): Promise<void> {
  await apiClient.delete(`/api/contribute/grammar/${pointId}/drills/${drillId}`)
}

export interface CardFeedbackItem {
  id: string
  card_type: 'grammar' | 'vocabulary'
  content_id: string
  card_title: string | null
  message: string
  status: string
  created_at: string | null
}

export async function getFeedback(languageId: string): Promise<CardFeedbackItem[]> {
  const response = await apiClient.get<{ feedback: CardFeedbackItem[] }>(
    '/api/contribute/feedback',
    { params: { language_id: languageId } },
  )
  return response.data.feedback
}

export async function resolveFeedback(feedbackId: string): Promise<void> {
  await apiClient.post(`/api/contribute/feedback/${feedbackId}/resolve`)
}

export interface AdminAccount {
  id: string
  email: string
  created_at: string | null
  last_sign_in_at: string | null
  plan_scope: 'single' | 'all' | null
  plan_language: string | null
  roles: string[]
  cards: number
  languages_studied: number
}

export async function listAccounts(): Promise<AdminAccount[]> {
  const response = await apiClient.get<{ users: AdminAccount[] }>(
    '/api/contribute/users',
  )
  return response.data.users
}

export async function createAccount(
  email: string,
  password: string,
): Promise<{ id: string; email: string }> {
  const response = await apiClient.post('/api/contribute/users', {
    email,
    password,
  })
  return response.data
}

export async function deleteAccount(userId: string): Promise<void> {
  await apiClient.delete(`/api/contribute/users/${userId}`)
}

export async function overridePlan(
  userId: string,
  planScope: 'single' | 'all',
  planLanguageId?: string,
): Promise<void> {
  await apiClient.put(`/api/contribute/users/${userId}/plan`, {
    plan_scope: planScope,
    plan_language_id: planLanguageId ?? null,
  })
}
