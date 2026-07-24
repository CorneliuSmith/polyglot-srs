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
  can_trial_review?: boolean
  can_contribute: boolean
  review_policy: string
  tutor_model?: string | null
}> {
  const response = await apiClient.get('/api/contribute/grammar', {
    params: { language_id: languageId },
  })
  return response.data
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
  ai_check_status: 'pass' | 'concerns' | null
  ai_check_notes: string | null
}

export async function getVocabForLanguage(
  languageId: string,
): Promise<{
  items: VocabItemEdit[]
  is_admin: boolean
  can_review: boolean
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
  feature_users: { review: number; tutor: number; reader: number }
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

export interface EngagementUserLanguage {
  code: string
  name: string
  cards_total: number
  reviews: number
  review_minutes: number
  tutor_messages: number
  readings: number
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

export async function getTranslationReviews(): Promise<TranslationReview[]> {
  const response = await apiClient.get<{ reviews: TranslationReview[] }>(
    '/api/contribute/translation-reviews',
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

export interface Suggestion {
  id: string
  entity_type: SuggestEntity
  entity_id: string
  card_title: string | null
  current: SuggestionFields
  proposed: SuggestionFields
  note: string | null
  status: string
  created_at: string | null
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

export async function getSuggestions(languageId: string): Promise<Suggestion[]> {
  const res = await apiClient.get('/api/contribute/suggestions', {
    params: { language_id: languageId },
  })
  return res.data.suggestions
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
  author_email: string | null
  score: number
  upvotes: number
  downvotes: number
  my_vote: number
  created_at: string
}

export interface NewChangeRequest {
  language_id: string
  target_type?: string
  target_id?: string | null
  target_label?: string | null
  field: string
  issue: string
  suggestion?: string | null
}

export async function createChangeRequest(body: NewChangeRequest): Promise<{ id: string }> {
  const response = await apiClient.post('/api/contribute/change-requests', body)
  return response.data
}

export async function getChangeRequests(
  languageId: string,
  status = 'open',
): Promise<{ requests: ChangeRequest[]; can_resolve: boolean }> {
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

/** Client mirror of backend can_contribute: admin anywhere, or a
 * contributor/reviewer for this language (null language = all). */
export function canSuggestForLanguage(
  roles: ContributorRole[],
  languageId: string | null,
): boolean {
  return roles.some(
    (r) =>
      r.role === 'admin' ||
      ((r.role === 'contributor' || r.role === 'reviewer') &&
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

export interface PendingExample {
  id: string
  sentence: string
  translation: string | null
  origin_detail: string | null
  word: string
  vocabulary_id: string
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
  change_requests: number
  suggestions: number
  notes: number
  feedback: number
}

export interface ReviewInbox {
  counts: ReviewInboxCounts
  can_publish: boolean
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
