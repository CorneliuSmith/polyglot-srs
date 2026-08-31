import apiClient from './client'
import { useViewAsStore } from '../stores/viewAsStore'
import { downgradeFlags, downgradeRoles } from '../lib/viewAs'
import type { PublishPolicy } from '../lib/publishPolicy'

/** The admin "view as" preview is applied HERE, at the single boundary every
 * role-gated surface already reads from, so no consumer needs to know it
 * exists. It only ever removes capability (see lib/viewAs.ts) and the server
 * re-derives real roles on every privileged call, so it cannot grant
 * anything — it just answers "what does a contributor actually see?". */
const currentViewAs = () => useViewAsStore.getState().viewAs

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

export async function getMyRoles(): Promise<{
  roles: ContributorRole[]
  is_admin: boolean
  /** Untouched by the "view as" preview — see ViewAsBar. */
  real_is_admin?: boolean
  /** May mint accounts: admin or ambassador. Answered by the server rather
   *  than derived from `roles`, because an ambassador grant carries no
   *  language scope for the client to reason about. */
  can_add_accounts?: boolean
}> {
  const response = await apiClient.get('/api/contribute/roles')
  const viewAs = currentViewAs()
  if (!viewAs) return response.data
  return {
    // real_is_admin rides through the spread deliberately: the bar that
    // ends the preview must stay reachable while one is active.
    ...response.data,
    roles: downgradeRoles(response.data.roles ?? [], viewAs),
    is_admin: false,
    // Previewing as a learner must not leave the account-minting form on
    // screen. The server still refuses; this stops the UI lying about it.
    can_add_accounts: viewAs === 'ambassador',
  }
}

export async function getGrammarForLanguage(
  languageId: string,
): Promise<{
  points: GrammarPointEdit[]
  is_admin: boolean
  can_review: boolean
  can_trial_review?: boolean
  can_contribute: boolean
  review_policy: string
  /** Unreviewed points with no AI-check verdict — invisible to learners
   *  even under 'ai_ok', because the policy is only half the gate. */
  unchecked_points?: number
  tutor_model?: string | null
  default_tutor_model?: string
}> {
  const response = await apiClient.get('/api/contribute/grammar', {
    params: { language_id: languageId },
  })
  return downgradeFlags(response.data, currentViewAs())
}

export interface VocabItemEdit {
  id: string
  word: string
  reading: string | null
  part_of_speech: string | null
  level: string | null
  frequency_rank: number | null
  definition: string | null
  example_count: number
  /** Example sentences on this word the recheck flagged. Always an int (0
   * when the column isn't migrated) — the per-word locator behind the
   * "Flagged examples" inbox tile. */
  flagged_count: number
  /** Example sentences carrying a pending suggested translation — the
   * locator behind the "Translation fixes" tile. */
  suggestion_count: number
  ai_check_status: 'pass' | 'concerns' | null
  ai_check_notes: string | null
}

export async function getVocabForLanguage(
  languageId: string,
): Promise<{
  items: VocabItemEdit[]
  is_admin: boolean
  can_review: boolean
  /** Testers reach this list too (advisory only): true for them, while
   * can_contribute stays false. */
  can_trial_review?: boolean
  can_contribute: boolean
}> {
  const response = await apiClient.get('/api/contribute/vocab', {
    params: { language_id: languageId },
  })
  return response.data
}

export interface ReviewNote {
  id: string
  grammar_point_id: string | null
  vocabulary_id: string | null
  entity_type: 'grammar' | 'vocab'
  entity_label: string
  // Kept for the existing grammar UI; mirrors entity_label.
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

/** File a reviewer note against a vocabulary word (advisory; publishes nothing). */
export async function flagVocabIssue(vocabularyId: string, note: string): Promise<void> {
  await apiClient.post(`/api/contribute/vocab/${vocabularyId}/notes`, { note })
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

export interface LanguageReadiness {
  id: string
  code: string
  name: string
  is_visible: boolean
  /** Raw stored policy — may be the legacy 'strict'; normalize before use. */
  review_policy?: string | null
  tutor_model?: string | null
  draft_points: number
  pending_drills: number
  pending_examples: number
  /** Unreviewed CONTENT — what gates a first release. */
  awaiting_review: number
  /** Human-raised traffic (notes, change requests, feedback). */
  open_reports: number
}

/** Per-language review backlog behind the release (visibility) decision. */
export async function getLanguageReadiness(): Promise<LanguageReadiness[]> {
  const response = await apiClient.get<{ languages: LanguageReadiness[] }>(
    '/api/contribute/language-readiness',
  )
  return response.data?.languages ?? []
}

export async function setLanguageTutorModel(
  languageId: string,
  model: string | null,
  allLanguages = false,
): Promise<void> {
  await apiClient.post('/api/contribute/language-tutor-model', {
    language_id: languageId,
    model,
    all_languages: allLanguages,
  })
}

export interface TutorUsageRow {
  language_id: string | null
  language_name: string | null
  model: string | null
  /** Open on purpose: kinds are added as features are (speak, reader,
   * gym_gen, …) and an old row keeps whatever kind it was written with. */
  kind: string
  /** Which surface spent it — the server maps kind → feature. */
  feature: string
  messages: number
  input_tokens: number
  output_tokens: number
  cache_write_tokens: number
  cache_read_tokens: number
  est_cost_usd: number
}

/** Speech spend, which is billed per character (TTS) and per audio second
 * (STT) rather than per token — so it lives in its own ledger. */
export interface SpeechUsageRow {
  language_code: string | null
  kind: 'tts' | 'stt'
  feature: string
  events: number
  chars: number
  audio_ms: number
  est_cost_usd: number
}

export interface TutorUsageSummary {
  days: number
  rows: TutorUsageRow[]
  speech_rows: SpeechUsageRow[]
  feature_totals: { feature: string; events: number; est_cost_usd: number }[]
  total_messages: number
  total_tts_chars: number
  total_stt_ms: number
  token_est_cost_usd: number
  speech_est_cost_usd: number
  total_est_cost_usd: number
  speech_free_tier: { tts_chars: number; stt_hours: number }
}

/** Admin-only rollup of AI spend — tokens and speech — at list rates. */
export async function getTutorUsage(days = 30): Promise<TutorUsageSummary> {
  const response = await apiClient.get('/api/contribute/tutor-usage', {
    params: { days },
  })
  return response.data
}

export interface Engagement {
  days: number
  total_users: number
  new_users: number
  active_users: { d1: number; d7: number; d30: number }
  reviews: number
  review_hours: number
  tutor_messages: number
  readings: number
  cards_started: number
  speak_sessions: number
  speak_turns: number
  feature_users: { review: number; tutor: number; reader: number; speak: number }
  top_languages: { code: string; name: string; learners: number; cards: number }[]
}

export interface EngagementUser {
  id: string
  email: string | null
  joined: string | null
  last_active: string | null
  reviews: number
  review_minutes: number
  tutor_messages: number
  readings: number
  cards_started: number
  cards_total: number
  speak_sessions: number
  languages: string[]
}

export async function getEngagementUsers(days = 30): Promise<EngagementUser[]> {
  const response = await apiClient.get<{ users: EngagementUser[] }>(
    '/api/contribute/engagement/users',
    { params: { days } },
  )
  return response.data.users
}

export interface AnalyticsDay {
  date: string
  active_users: number
  reviews: number
  minutes: number
  new_users: number
}

export async function getAnalyticsTimeseries(days = 30): Promise<AnalyticsDay[]> {
  const response = await apiClient.get<{ days: number; series: AnalyticsDay[] }>(
    '/api/contribute/analytics/timeseries',
    { params: { days } },
  )
  return response.data.series
}

export interface RetentionCohort {
  cohort_week: string
  size: number
  /** returned[n] = members active in week n after signup (week 0 = signup week) */
  returned: number[]
}

export async function getAnalyticsCohorts(): Promise<RetentionCohort[]> {
  const response = await apiClient.get<{ cohorts: RetentionCohort[] }>(
    '/api/contribute/analytics/cohorts',
  )
  return response.data.cohorts
}

export interface FeaturePopularity {
  key: string
  label: string
  /** What one event IS ("messages", "conversations") — rendered next to the
   * count so the panel never says "1,204 events" about anything. */
  unit: string
  users: number
  events: number
}

export async function getFeaturePopularity(
  days = 30,
): Promise<FeaturePopularity[]> {
  const response = await apiClient.get<{
    days: number
    features: FeaturePopularity[]
  }>('/api/contribute/analytics/features', { params: { days } })
  return response.data.features
}

export interface EngagementUserLanguage {
  code: string
  name: string
  cards_total: number
  reviews: number
  review_minutes: number
  tutor_messages: number
  readings: number
  speak_sessions: number
  last_review: string | null
}

export async function getEngagementUserDetail(
  userId: string,
  days = 30,
): Promise<EngagementUserLanguage[]> {
  const response = await apiClient.get<{ languages: EngagementUserLanguage[] }>(
    `/api/contribute/engagement/users/${userId}`,
    { params: { days } },
  )
  return response.data.languages
}

export interface TranslationReview {
  id: string
  locale: string
  word: string
  proposed: string | null
  reason: string | null
  current_definition: string | null
  created_at: string | null
}

export async function getTranslationReviews(
  languageId?: string,
): Promise<TranslationReview[]> {
  const response = await apiClient.get<{ reviews: TranslationReview[] }>(
    '/api/contribute/translation-reviews',
    { params: languageId ? { language_id: languageId } : {} },
  )
  return response.data.reviews
}

export async function approveTranslationReview(id: string): Promise<void> {
  await apiClient.post(`/api/contribute/translation-reviews/${id}/approve`)
}

export async function rejectTranslationReview(id: string): Promise<void> {
  await apiClient.post(`/api/contribute/translation-reviews/${id}/reject`)
}

export async function getEngagement(days = 30): Promise<Engagement> {
  const response = await apiClient.get('/api/contribute/engagement', {
    params: { days },
  })
  return response.data
}

export type GrantableRole =
  | 'contributor'
  | 'trial_reviewer'
  | 'reviewer'
  | 'ambassador'
  | 'admin'

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
  policy: PublishPolicy,
): Promise<void> {
  await apiClient.post('/api/contribute/language-policy', {
    language_id: languageId,
    policy,
  })
}

/** Show/hide a language in learner-facing pickers (admin-only). */
export async function setLanguageVisibility(
  languageId: string,
  isVisible: boolean,
): Promise<void> {
  await apiClient.post('/api/contribute/language-visibility', {
    language_id: languageId,
    is_visible: isVisible,
  })
}

/** Switch demand-driven support-locale translation for a course (admin-only).
 * The loop only spends on (course, locale) pairs live accounts use. */
export interface TranslationStatus {
  provider_ready: boolean
  budget_per_cycle: number
  sweep_seconds: number
  /** The settings flag. Everything else here describes work the sweep WOULD
   * do; none of it happens if the loop was never switched on. */
  loop_enabled: boolean
  /** What the sweep has actually done in the serving process. Distinguishes
   * "enabled but never started" from "running and finding nothing". */
  loop: {
    started: boolean
    last_cycle_at: string | null
    cycles: number
    last_error: string | null
    last_stats: Record<string, number> | null
  }
  migrations: Record<string, boolean>
  switched_off: { language: string; code: string; locale: string; learners: number }[]
  pairs: {
    language: string
    code: string
    locale: string
    learners: number
    pending: Record<string, number>
    filled: Record<string, number>
  }[]
}

/** Admin diagnostic: why automatic translation is or isn't running. */
export async function getTranslationStatus(): Promise<TranslationStatus> {
  const { data } = await apiClient.get('/api/contribute/translation-status')
  return data
}

export async function setLanguageAutoTranslate(
  languageId: string,
  enabled: boolean,
): Promise<void> {
  await apiClient.post('/api/contribute/language-auto-translate', {
    language_id: languageId,
    enabled,
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

/** Run the advisory AI semantic review on a vocab word. */
export async function runVocabAiCheck(
  vocabularyId: string,
): Promise<{ status: 'pass' | 'concerns'; notes: string }> {
  const response = await apiClient.post(`/api/contribute/vocab/${vocabularyId}/ai-check`)
  return response.data
}

export interface Drill {
  id: string
  sentence: string
  answer: string
  translation: string | null
  hint: string | null
  display_order: number
  // Provenance: where it came from and whether we've edited it since.
  source?: string
  is_modified?: boolean
  // Quality-audit flag (--recheck): set when the judge rejected this drill.
  flagged?: boolean
  flag_reason?: string | null
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

export type TutorAccess = 'default' | 'blocked' | 'enabled'

export interface AdminAccount {
  id: string
  email: string
  created_at: string | null
  last_sign_in_at: string | null
  plan_scope: 'single' | 'all' | null
  plan_language: string | null
  tutor_access: TutorAccess
  tutor_daily_cap: number | null
  /** Admin-set monthly charge in cents; null = standard plan pricing. */
  monthly_cents: number | null
  price_currency: string | null
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

export async function setTutorAccess(
  userId: string,
  access: TutorAccess,
  dailyCap: number | null,
): Promise<void> {
  await apiClient.put(`/api/contribute/users/${userId}/tutor`, {
    access,
    daily_cap: dailyCap,
  })
}

export interface TrialRequestRow {
  id: string
  email: string
  name: string | null
  note: string | null
  status: 'pending' | 'approved' | 'rejected'
  requested_at: string
  decided_at: string | null
}

export async function listTrialRequests(): Promise<{
  requests: TrialRequestRow[]
  available: boolean
}> {
  const response = await apiClient.get<{
    requests: TrialRequestRow[]
    available: boolean
  }>('/api/contribute/trial-requests')
  return response.data
}

/** Approve: mints the account with a temp password (forced reset on first
 * sign-in) and emails the applicant. The password comes back for the panel
 * to show once — email is log-only until Resend is configured. */
export async function approveTrialRequest(requestId: string): Promise<{
  email: string
  temp_password: string
  emailed: boolean
}> {
  const response = await apiClient.post<{
    email: string
    temp_password: string
    emailed: boolean
  }>(`/api/contribute/trial-requests/${requestId}/approve`)
  return response.data
}

export async function rejectTrialRequest(requestId: string): Promise<void> {
  await apiClient.post(`/api/contribute/trial-requests/${requestId}/reject`)
}

/** Set (or with null, clear) the account's monthly charge in cents.
 * Checkout charges this amount via Stripe price_data; 0 = free. */
export async function setAccountPrice(
  userId: string,
  monthlyCents: number | null,
): Promise<void> {
  await apiClient.put(`/api/contribute/users/${userId}/price`, {
    monthly_cents: monthlyCents,
  })
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

// ── Content suggestions (contributor-proposed card edits) ────────────────
export type SuggestEntity = 'vocabulary' | 'grammar'

export interface SuggestionFields {
  definition?: string
  part_of_speech?: string
  usage_note?: string
  function_note?: string
  explanation?: string
  culture_note?: string
}

export type SuggestionSource = 'contributor' | 'extraction'

export interface Suggestion {
  id: string
  entity_type: SuggestEntity
  entity_id: string
  card_title: string | null
  current: SuggestionFields
  proposed: SuggestionFields
  note: string | null
  status: string
  source: SuggestionSource
  origin: string | null
  created_at: string | null
}

/** Acceptance stats for doc-sourced (extraction) AI vocab recommendations. */
export interface SuggestionMetrics {
  total: number
  pending: number
  approved: number
  rejected: number
  resolved: number
  acceptance_rate: number | null
}

export async function submitSuggestion(input: {
  entity_type: SuggestEntity
  entity_id: string
  proposed: SuggestionFields
  note?: string
}): Promise<{ id: string }> {
  const res = await apiClient.post('/api/contribute/suggestions', input)
  return res.data
}

export async function getSuggestions(
  languageId: string,
  source?: SuggestionSource,
): Promise<Suggestion[]> {
  const res = await apiClient.get('/api/contribute/suggestions', {
    params: { language_id: languageId, ...(source ? { source } : {}) },
  })
  return res.data.suggestions
}

/** Admin: acceptance rate of doc-sourced AI recommendations (optionally scoped
 * to one language). They cost real model spend, so admin tracks how often they
 * land. */
export async function getSuggestionMetrics(
  languageId?: string,
): Promise<SuggestionMetrics> {
  const res = await apiClient.get('/api/contribute/admin/suggestions/metrics', {
    params: languageId ? { language_id: languageId } : {},
  })
  return res.data
}

export async function approveSuggestion(id: string): Promise<void> {
  await apiClient.post(`/api/contribute/suggestions/${id}/approve`)
}

export async function rejectSuggestion(id: string, reviewNote?: string): Promise<void> {
  await apiClient.post(`/api/contribute/suggestions/${id}/reject`, {
    review_note: reviewNote ?? null,
  })
}

// ── Card change requests (votable staff suggestions) ───────────────────────

export interface ChangeRequest {
  id: string
  target_type: string
  target_id: string | null
  target_label: string | null
  field: string
  issue: string
  suggestion: string | null
  status: string
  /** Review Mode: the exact span the reviewer selected. */
  quote?: string | null
  quote_context?: {
    source?: string
    start?: number
    end?: number
    source_text?: string
  }
  author_email: string | null
  score: number
  upvotes: number
  downvotes: number
  my_vote: number
  created_at: string
  /** Raised by someone whose only standing for this language is tester:
   * their request is advisory — it can be read and prioritised, never
   * resolved by them. */
  is_advisory?: boolean
}

export interface NewChangeRequest {
  language_id: string
  target_type?: string
  target_id?: string | null
  target_label?: string | null
  field: string
  issue: string
  suggestion?: string | null
  quote?: string | null
  quote_context?: Record<string, unknown>
}

export async function createChangeRequest(body: NewChangeRequest): Promise<{ id: string }> {
  const response = await apiClient.post('/api/contribute/change-requests', body)
  return response.data
}

export async function getChangeRequests(
  languageId: string,
  status = 'open',
): Promise<{
  requests: ChangeRequest[]
  can_resolve: boolean
  /** Voting is a judgement on someone else's judgement, so it stays with
   * the roles that publish. Testers read and raise; the server 403s their
   * vote, so the buttons are hidden rather than left to fail. */
  can_vote?: boolean
}> {
  const response = await apiClient.get('/api/contribute/change-requests', {
    params: { language_id: languageId, status },
  })
  return response.data
}

export async function voteChangeRequest(requestId: string, vote: number): Promise<void> {
  await apiClient.post(`/api/contribute/change-requests/${requestId}/vote`, { vote })
}

export async function resolveChangeRequest(
  requestId: string,
  status: 'accepted' | 'rejected',
): Promise<void> {
  await apiClient.post(`/api/contribute/change-requests/${requestId}/resolve`, { status })
}

/** Client mirror of the change-request raise gate: admin anywhere, or a
 * contributor/reviewer/trial reviewer for this language (null language =
 * all).
 *
 * Trial reviewers belong here (WP31 gap G2). They were excluded, which hid
 * both the Review Mode toggle and "Suggest a change" from the very people
 * recruited to review — their reports silently degraded into learner-grade
 * card feedback while the admin watched an empty change-request board. The
 * server now accepts their raise (advisory: they may not vote or resolve),
 * so the client must offer it. */
const SUGGEST_ROLES = new Set(['contributor', 'reviewer', 'trial_reviewer'])

export function canSuggestForLanguage(
  roles: ContributorRole[],
  languageId: string | null,
): boolean {
  return roles.some(
    (r) =>
      r.role === 'admin' ||
      (SUGGEST_ROLES.has(r.role) &&
        (r.language_id === null || r.language_id === languageId)),
  )
}

// ── Admin content generation panel (WP42) ──────────────────────────────────

export interface GenerationCoverageRow {
  language_id: string
  language_code: string
  language_name: string
  vocab_total: number
  vocab_no_examples: number
  grammar_total: number
  grammar_no_drills: number
  ai_examples: number
  pending_examples: number
  ai_drills: number
  low_resource: boolean
  sentence_model: string
  grammar_model: string
  unfilled: number
}

export interface GenerationCoverage {
  available: boolean
  coverage: GenerationCoverageRow[]
  recommended_next: {
    language_id: string
    language_code: string
    language_name: string
    unfilled: number
    low_resource: boolean
  }[]
  limits: { max_items: number; max_per_item: number }
}

export interface GenerationDryRun {
  dry_run: true
  kind: string
  model: string
  target_per_item: number
  items_to_process: number
  sentences_to_attempt: number
  est_cost_usd: number
}

export interface GenerationResult {
  dry_run: false
  kind: string
  language_code: string
  language_name: string
  model: string
  target_per_item: number
  items_processed: number
  sentences_attempted: number
  sentences_accepted: number
  sentences_persisted: number
  duplicates_skipped: number
  est_cost_usd: number
}

export async function getGenerationCoverage(): Promise<GenerationCoverage> {
  const response = await apiClient.get<GenerationCoverage>(
    '/api/contribute/admin/generation/coverage',
  )
  return response.data
}

export async function runGeneration(params: {
  languageId: string
  languageCode: string
  kind: 'vocab' | 'grammar'
  targetPerItem: number
  maxItems: number
  dryRun: boolean
}): Promise<GenerationDryRun | GenerationResult> {
  const response = await apiClient.post('/api/contribute/admin/generation/run', {
    language_id: params.languageId,
    language_code: params.languageCode,
    kind: params.kind,
    target_per_item: params.targetPerItem,
    max_items: params.maxItems,
    dry_run: params.dryRun,
  })
  return response.data
}

/** Recheck (quality-audit) of EXISTING content — vocab examples or grammar
 * drills. Shape is normalized across both corpora. */
export interface RecheckDryRun {
  dry_run: true
  kind: string
  model: string
  items_to_audit: number
  units_to_audit: number
  est_cost_usd: number
}

export interface RecheckResult {
  dry_run: false
  kind: string
  model: string
  items_audited: number
  flagged: number
  alternatives_generated: number
  est_cost_usd: number
}

/** Audit existing example sentences (vocab) or drills (grammar): flag the bad
 * ones for review and top each item back up to target with alternatives. */
export async function runRecheck(params: {
  languageId: string
  languageCode: string
  kind: 'vocab' | 'grammar'
  targetPerItem: number
  maxItems: number
  dryRun: boolean
}): Promise<RecheckDryRun | RecheckResult> {
  const response = await apiClient.post('/api/contribute/admin/generation/recheck', {
    language_id: params.languageId,
    language_code: params.languageCode,
    kind: params.kind,
    target_per_item: params.targetPerItem,
    max_items: params.maxItems,
    dry_run: params.dryRun,
  })
  return response.data
}

// ── Grammar-point overlap audit ────────────────────────────────────────────

export interface OverlapPoint {
  id: string
  title: string
  level: string | null
}

export interface OverlapPair {
  id: string
  verdict: 'duplicate' | 'subsumes' | 'partial'
  reason: string | null
  status: string
  created_at: string
  point_a: OverlapPoint
  point_b: OverlapPoint
}

/** Scan the grammar syllabus for overlapping points (admin). Dry-run gives
 * the work-list size and cost estimate without calling the model. */
export async function runOverlapAudit(params: {
  languageId: string
  languageCode: string
  dryRun: boolean
}): Promise<{
  dry_run: boolean
  model: string
  points_to_audit?: number
  judge_calls?: number
  points_audited?: number
  pairs_reported?: number
  pairs_flagged?: number
  est_cost_usd: number
}> {
  const response = await apiClient.post(
    '/api/contribute/admin/generation/overlap',
    {
      language_id: params.languageId,
      language_code: params.languageCode,
      dry_run: params.dryRun,
    },
  )
  return response.data
}

/** Backfill Gym reference charts (admin, WP45): for every drill answer the
 * Gym's chart lookup cannot resolve, generate the word's paradigm chart —
 * verified by requiring the drill's own answer to appear in it. Dry-run
 * gives the work-list size and cost estimate without calling the model. */
export async function runChartForms(params: {
  languageId: string
  languageCode: string
  maxItems: number
  dryRun: boolean
}): Promise<{
  dry_run: boolean
  model: string
  answers_scanned: number
  charts_to_attempt?: number
  charts_attempted?: number
  charts_rejected?: number
  words_created?: number
  words_updated?: number
  already_charted_skipped?: number
  est_cost_usd: number
}> {
  const response = await apiClient.post(
    '/api/contribute/admin/generation/forms',
    {
      language_id: params.languageId,
      language_code: params.languageCode,
      max_items: params.maxItems,
      dry_run: params.dryRun,
    },
  )
  return response.data
}

/** Open overlap pairs awaiting a reviewer's verdict. */
export async function getOverlaps(languageId: string): Promise<OverlapPair[]> {
  const response = await apiClient.get<{ overlaps: OverlapPair[] }>(
    '/api/contribute/review/overlaps',
    { params: { language_id: languageId } },
  )
  return response.data.overlaps
}

/** Reviewer verdict on an overlap pair. */
export async function resolveOverlap(
  overlapId: string,
  status: 'merged' | 'distinct' | 'dismissed',
): Promise<{ resolved: boolean }> {
  const response = await apiClient.post(
    `/api/contribute/review/overlaps/${overlapId}/resolve`,
    { status },
  )
  return response.data
}

export interface PendingExample {
  id: string
  sentence: string
  translation: string | null
  origin_detail: string | null
  word: string
  vocabulary_id: string
  /** Tester verdicts on this row. Approving DELETES the pending row and the
   * note with it, so it has to be readable here or it is never read at all.
   * null = nobody has judged it. */
  recommendations?: RecoTally | null
}

/** Generated example sentences awaiting review for a language — hidden from
 * learners until approved (WP42 gate). */
export async function getPendingExamples(
  languageId: string,
  limit = 50,
): Promise<PendingExample[]> {
  const response = await apiClient.get<{ pending: PendingExample[] }>(
    '/api/contribute/admin/generation/pending',
    { params: { language_id: languageId, limit } },
  )
  return response.data.pending
}

/** Approve (→ served to learners) or reject (→ deleted) a pending example. */
export async function reviewExample(
  exampleId: string,
  approve: boolean,
): Promise<void> {
  await apiClient.post(
    `/api/contribute/admin/generation/examples/${exampleId}/review`,
    { approve },
  )
}

/** Approve or reject EVERY pending generated example for a language at once.
 * When approving, flagged sentences are skipped by default. Returns the count. */
export async function reviewExamplesBulk(
  languageId: string,
  approve: boolean,
  onlyUnflagged = true,
): Promise<number> {
  const response = await apiClient.post<{ approved: boolean; changed: number }>(
    '/api/contribute/admin/generation/examples/bulk-review',
    { language_id: languageId, approve, only_unflagged: onlyUnflagged },
  )
  return response.data.changed
}

// ── Generated-drill review gate (Contributor › Review) ─────────────────────

/** Advisory-recommendation tally left by trial reviewers on a pending item. */
export interface RecoTally {
  approve: number
  reject: number
  notes: string[]
}

export interface PendingDrill {
  id: string
  sentence: string
  answer: string
  translation: string | null
  hint: string | null
  cell: string | null
  origin_detail: string | null
  flagged?: boolean
  flag_reason?: string | null
  point_title: string
  point_id: string
  recommendations?: RecoTally | null
}

export interface PendingDrillsResult {
  pending: PendingDrill[]
  /** True for full reviewers/admins (can publish); false for trial reviewers. */
  can_publish: boolean
}

/** The dashboard forced-feedback nudge for trial reviewers: one real pending
 * item to judge. */
export interface ReviewPrompt {
  target_type: 'drill' | 'example'
  target_id: string
  language_id: string
  context: string
  sentence: string
  answer: string | null
  translation: string | null
  word: string | null
  question: string
}

/** Returns a nudge when one is due for a trial reviewer, else {due:false}. */
export async function getReviewPrompt(): Promise<{ due: boolean; prompt?: ReviewPrompt }> {
  const response = await apiClient.get('/api/contribute/review/prompt')
  return response.data
}

/** Record the trial reviewer's answer: approve/reject (an advisory vote) or
 * skip ("can't tell"). Returns when they'll next be nudged — real feedback
 * pushes it further out; a skip brings it back sooner. */
export async function answerReviewPrompt(body: {
  targetType: 'drill' | 'example'
  targetId: string
  languageId: string
  recommendation: 'approve' | 'reject' | 'skip'
  note?: string
}): Promise<{ next_prompt_at: string }> {
  const response = await apiClient.post('/api/contribute/review/prompt/answer', {
    target_type: body.targetType,
    target_id: body.targetId,
    language_id: body.languageId,
    recommendation: body.recommendation,
    note: body.note ?? '',
  })
  return response.data
}

/** One roll-up of everything awaiting review action for a language. Each key
 * is a queue an existing panel already acts on. */
export interface ReviewInboxCounts {
  grammar_pending: number
  pending_drills: number
  flagged_drills: number
  pending_examples: number
  flagged_examples: number
  translation_suggestions: number
  ai_levels: number
  /** Provisional Topic Lens buckets (topic_source='ai') awaiting a
   * reviewer's confirm — the semantic sorting the classifier produced. */
  ai_topics: number
  change_requests: number
  suggestions: number
  notes: number
  feedback: number
  overlaps: number
  ai_translations: number
  /** Advisory approve/reject votes from testers on items still pending —
   * the testers' main deliverable, previously counted nowhere. */
  tester_recommendations: number
  /** Open general app feedback filed against this language — the home-page
   * button's reports. Admin-only tile; reports naming no language surface
   * in the bell's own bucket instead. */
  app_feedback: number
}

/** One other language with work waiting on a reviewer. The whole point of
 * the strip: a submission carries the language the TESTER was studying, not
 * the one the admin's selector happens to sit on. */
export interface OtherLanguageWork {
  id: string
  code: string
  name: string
  /** Sum of every queue below; the server only sends languages where > 0. */
  total: number
  counts: ReviewInboxCounts
}

export interface ReviewInbox {
  counts: ReviewInboxCounts
  /** Sorted by total desc, current language excluded, zeroes excluded.
   * Degrades to [] if the roll-up query fails — an empty strip is not proof
   * that nothing is waiting elsewhere. */
  other_languages?: OtherLanguageWork[]
  can_publish: boolean
  /** The AI-translations queue is admin-only to open, so its tile is
   * admin-only to show. */
  is_admin?: boolean
}

/** The unified Review Inbox counts for a language. */
export async function getReviewInbox(languageId: string): Promise<ReviewInbox> {
  const response = await apiClient.get<ReviewInbox>(
    '/api/contribute/review/inbox',
    { params: { language_id: languageId } },
  )
  return response.data
}

/** Generated grammar drills awaiting review for a language — hidden from
 * learners until approved. */
export async function getPendingDrills(
  languageId: string,
): Promise<PendingDrillsResult> {
  const response = await apiClient.get<PendingDrillsResult>(
    '/api/contribute/review/generated-drills',
    { params: { language_id: languageId } },
  )
  return response.data
}

/** Approve (→ permanent corpus) or reject (→ deleted) a pending generated drill. */
export async function reviewDrill(drillId: string, approve: boolean): Promise<void> {
  await apiClient.post(
    `/api/contribute/review/generated-drills/${drillId}/review`,
    { approve },
  )
}

/** Trial reviewer's advisory approve/reject on a pending drill or example. */
export async function recommend(
  targetType: 'drill' | 'example',
  targetId: string,
  recommendation: 'approve' | 'reject',
  note = '',
): Promise<void> {
  await apiClient.post('/api/contribute/review/recommend', {
    target_type: targetType,
    target_id: targetId,
    recommendation,
    note,
  })
}

/** A tester's advisory judgement on one still-pending item, with the note
 * they wrote — the durable surface for the channel that used to exist only
 * as a hover tooltip on a row that approval would delete. */
export interface TesterRecommendation {
  id: string
  target_type: 'drill' | 'example'
  target_id: string
  recommendation: 'approve' | 'reject'
  /** Always a string; '' when the tester left no note. */
  note: string
  recommender_email: string | null
  /** The sentence being judged. */
  target_label: string | null
  target_translation: string | null
  /** Grammar-point title (drills) or the word (examples). */
  context: string | null
  created_at: string
}

/** Tester recommendations on items still awaiting review, rejections first
 * then newest first. Same still-pending filter as the inbox count, so the
 * tile and this panel always agree. */
export async function getTesterRecommendations(
  languageId: string,
  limit = 200,
): Promise<{
  recommendations: TesterRecommendation[]
  /** The clamped limit the server actually applied. */
  limit: number
  can_publish: boolean
}> {
  const response = await apiClient.get('/api/contribute/review/recommendations', {
    params: { language_id: languageId, limit },
  })
  return response.data
}

export interface TrialReviewer {
  user_id: string
  email: string
  recommendations: number
  edits: number
  last_active: string | null
}

/** Trial reviewers for a language + their activity (admin). */
export async function getTrialReviewers(
  languageId: string,
): Promise<TrialReviewer[]> {
  const response = await apiClient.get<{ reviewers: TrialReviewer[] }>(
    '/api/contribute/review/trial-reviewers',
    { params: { language_id: languageId } },
  )
  return response.data.reviewers
}

export interface VocabExample {
  id: string
  sentence: string
  translation: string | null
  source: string
  reviewed: boolean
  is_modified: boolean
  flagged?: boolean
  flag_reason?: string | null
  suggested_translation?: string | null
  suggestion_reason?: string | null
  recommendations?: RecoTally | null
}

export interface VocabExamplesResult {
  examples: VocabExample[]
  can_publish: boolean
}

/** Every example sentence for a word — for the reviewer's inline editor. */
export async function getVocabExamples(
  vocabularyId: string,
): Promise<VocabExamplesResult> {
  const response = await apiClient.get<VocabExamplesResult>(
    `/api/contribute/review/vocab/${vocabularyId}/examples`,
  )
  return response.data
}

/** Reviewer edit of an example sentence's text/translation. */
export async function editExampleSentence(
  exampleId: string,
  sentence: string,
  translation: string | null,
): Promise<void> {
  await apiClient.put(`/api/contribute/review/examples/${exampleId}`, {
    sentence,
    translation,
  })
}

/** Reviewer delete of an example sentence. */
export async function deleteExampleSentence(exampleId: string): Promise<void> {
  await apiClient.delete(`/api/contribute/review/examples/${exampleId}`)
}

// ── Content audit log + rollback ───────────────────────────────────────────

export interface ContentChange {
  id: string
  entity_type: string
  entity_id: string
  action: string
  field: string | null
  before: Record<string, unknown> | null
  after: Record<string, unknown> | null
  note: string | null
  actor_id: string | null
  actor_email: string | null
  created_at: string | null
  revertible: boolean
}

export interface ContentHistory {
  changes: ContentChange[]
  can_revert: boolean
}

/** The change timeline for one card (who did what, when, before/after). */
export async function getContentHistory(
  entityType: string,
  entityId: string,
): Promise<ContentHistory> {
  const response = await apiClient.get<ContentHistory>(
    `/api/contribute/review/history/${entityType}/${entityId}`,
  )
  return response.data
}

/** Roll a logged change back to its prior value (full reviewer/admin). */
export async function revertContentChange(logId: string): Promise<void> {
  await apiClient.post(`/api/contribute/review/revert/${logId}`)
}

/** Apply the recheck's suggested translation to the live one (full reviewer). */
export async function acceptExampleTranslation(exampleId: string): Promise<void> {
  await apiClient.post(
    `/api/contribute/review/examples/${exampleId}/translation/accept`,
  )
}

/** Discard the recheck's suggested translation, keeping the current one. */
export async function dismissExampleTranslation(exampleId: string): Promise<void> {
  await apiClient.post(
    `/api/contribute/review/examples/${exampleId}/translation/dismiss`,
  )
}

export interface AiLeveledWord {
  id: string
  word: string
  level: string | null
  part_of_speech: string | null
  definition: string | null
}

export interface AiLevelsResult {
  words: AiLeveledWord[]
  can_publish: boolean
}

/** Words carrying a provisional AI-estimated CEFR level, for a reviewer to
 * confirm or adjust. */
export async function getAiLevels(languageId: string): Promise<AiLevelsResult> {
  const response = await apiClient.get<AiLevelsResult>(
    '/api/contribute/review/ai-levels',
    { params: { language_id: languageId } },
  )
  return response.data
}

/** Confirm or adjust a word's CEFR level → marks it curated (also its deck). */
export async function confirmVocabLevel(
  vocabularyId: string,
  level: string,
): Promise<void> {
  await apiClient.post(`/api/contribute/review/vocab/${vocabularyId}/level`, {
    level,
  })
}

// ── Plan message allotments (admin) ────────────────────────────────────────
// The monthly message cap for each account type. Stored in the database, so
// an admin can change one without a redeploy; every tier is always present in
// the response (a Settings/env default fills in where no override is stored).

export type PlanTier = 'free' | 'single' | 'all' | 'plus'

export const PLAN_TIER_LABELS: Record<PlanTier, string> = {
  free: 'Free',
  single: 'Single language (no AI included)',
  all: 'All languages',
  plus: 'AI add-on (added to the plan base)',
}

// ── Monetization master switch (admin) ─────────────────────────────────────
// OFF (the default) hides every money surface in the app — prices, upgrade
// buttons, top-ups, the tip jar — and closes the checkout endpoints. The
// owner flips it here once cleared to charge.

export async function getMonetization(): Promise<boolean> {
  const response = await apiClient.get('/api/contribute/monetization')
  return response.data.enabled
}

export async function setMonetization(enabled: boolean): Promise<boolean> {
  const response = await apiClient.put('/api/contribute/monetization', {
    enabled,
  })
  return response.data.enabled
}

export async function getPlanLimits(): Promise<Record<PlanTier, number>> {
  const response = await apiClient.get('/api/contribute/plan-limits')
  return response.data.limits
}

export async function setPlanLimit(
  plan: PlanTier,
  monthlyMessages: number,
): Promise<Record<PlanTier, number>> {
  const response = await apiClient.put(`/api/contribute/plan-limits/${plan}`, {
    monthly_messages: monthlyMessages,
  })
  return response.data.limits
}

// ── Contributor recordings (human audio for voiceless languages) ───────────
// Jamaican Patois has no neural voice, so audio comes from people: a
// contributor records a clip for one exact text, a reviewer approves it,
// and the audio endpoint serves it where TTS would have been.

export interface RecordingRow {
  id: string
  text: string
  mime: string
  status: 'pending' | 'approved' | 'rejected'
  created_at: string
  contributor_email?: string
}

export async function submitRecording(
  languageId: string,
  text: string,
  audioB64: string,
  mime: string,
): Promise<void> {
  await apiClient.post('/api/contribute/recordings', {
    language_id: languageId,
    text,
    audio_b64: audioB64,
    mime,
  })
}

export async function getMyRecordings(languageId: string): Promise<RecordingRow[]> {
  const response = await apiClient.get('/api/contribute/recordings/mine', {
    params: { language_id: languageId },
  })
  return response.data.recordings
}

export async function getRecordingsQueue(
  languageId: string,
): Promise<RecordingRow[]> {
  const response = await apiClient.get('/api/contribute/recordings', {
    params: { language_id: languageId, status_filter: 'pending' },
  })
  return response.data.recordings
}

export async function getRecordingAudio(
  recordingId: string,
): Promise<{ audio_b64: string; mime: string }> {
  const response = await apiClient.get(
    `/api/contribute/recordings/${recordingId}/audio`,
  )
  return response.data
}

export async function reviewRecording(
  recordingId: string,
  approve: boolean,
): Promise<void> {
  await apiClient.post(`/api/contribute/recordings/${recordingId}/review`, {
    approve,
  })
}

/** One batch of the bulk AI check (admin). Call repeatedly until
 *  `remaining` is 0 — each call takes the next still-unchecked points. */
export async function runAiCheckBatch(
  languageId: string,
): Promise<{ checked: number; passed: number; concerns: number; remaining: number }> {
  const response = await apiClient.post('/api/contribute/admin/ai-check-run', {
    language_id: languageId,
  })
  return response.data
}

/** One rollout — a change some accounts are getting and others aren't. */
export interface ExperimentVariant {
  key: string
  label: string
}

export interface ExperimentAssignedUser {
  user_id: string
  email: string | null
  variant: string
  source: 'admin' | 'self' | 'rollout'
  note: string | null
  assigned_at: string
}

export interface Experiment {
  key: string
  name: string
  description: string | null
  variants: ExperimentVariant[]
  default_variant: string
  /** {variant: percent} — of everyone WITHOUT an explicit assignment. */
  rollout: Record<string, number>
  enabled: boolean
  learner_choice: boolean
  counts?: { variant: string; source: string; count: number }[]
  assigned?: ExperimentAssignedUser[]
}

export async function getExperiments(): Promise<Experiment[]> {
  const response = await apiClient.get('/api/contribute/experiments')
  return response.data.experiments
}

export async function updateExperiment(patch: {
  key: string
  enabled?: boolean
  default_variant?: string
  rollout?: Record<string, number>
  learner_choice?: boolean
}): Promise<Experiment> {
  const response = await apiClient.post('/api/contribute/experiment', patch)
  return response.data.experiment
}

/** Pin one named account to one variant, or (variant: null) release it back
 *  to whatever the rollout says. */
export async function assignExperiment(body: {
  key: string
  email: string
  variant: string | null
  note?: string
}): Promise<{ user_id: string; variant: string | null }> {
  const response = await apiClient.post('/api/contribute/experiment-assign', body)
  return response.data
}

/** What is waiting for this reviewer, per language, in one call. */
export interface ReviewNotificationLanguage {
  id: string
  code: string
  name: string
  is_visible: boolean
  total: number
  counts: Record<string, number>
}

export interface FeedbackNotification {
  /** Null for feedback about the app as a whole, which belongs to no course. */
  language_id: string | null
  language_name: string | null
  count: number
}

export interface ReviewNotifications {
  languages: ReviewNotificationLanguage[]
  review_total: number
  feedback: FeedbackNotification[]
  feedback_total: number
  /** Strangers waiting on an access decision (admins only). Carried in the
   *  bell because the announcement email needs ADMIN_NOTIFY_EMAIL plus a
   *  working Resend sender — three ways to go quiet without anyone knowing.
   *  Absent on an older server, which reads as none. */
  trial_pending?: number
  is_admin: boolean
  /** False for ordinary learners — the endpoint answers them with an empty
   *  set rather than a 403, so the bell can ask on every page load. */
  is_staff: boolean
}

export async function getReviewNotifications(): Promise<ReviewNotifications> {
  const response = await apiClient.get<ReviewNotifications>(
    '/api/contribute/notifications',
  )
  return response.data
}
