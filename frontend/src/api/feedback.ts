import apiClient from './client'

/** The five buckets on the send form. Kept short on purpose: a long taxonomy
 *  makes people stop and choose instead of typing, and triage only needs
 *  enough to route.
 *
 *  `value` is the stable category ID stored with each report — never rename
 *  one. Learner-facing components do NOT show `label`: they resolve the
 *  display text via i18n at render time (`feedback.categories.<value>`).
 *  `label` remains only as the English triage label for the staff feedback
 *  queue, which is deliberately not localized. */
export const FEEDBACK_CATEGORIES = [
  { value: 'bug', label: 'Something is broken' },
  { value: 'confusing', label: 'Something is confusing' },
  { value: 'content', label: 'A word or sentence is wrong' },
  { value: 'idea', label: 'I have an idea' },
  { value: 'other', label: 'Something else' },
] as const

export type FeedbackCategory = (typeof FEEDBACK_CATEGORIES)[number]['value']
export type FeedbackStatus = 'open' | 'triaged' | 'closed'

export interface MyFeedback {
  id: string
  category: FeedbackCategory
  message: string
  page: string | null
  status: FeedbackStatus
  admin_note: string | null
  created_at: string
}

export interface FeedbackItem extends MyFeedback {
  user_id: string
  email: string | null
  language_id: string | null
  language_name: string | null
}

export async function sendFeedback(input: {
  category: FeedbackCategory
  message: string
  languageId?: string | null
  page?: string
}): Promise<string> {
  const response = await apiClient.post<{ id: string }>('/api/feedback', {
    category: input.category,
    message: input.message,
    language_id: input.languageId ?? null,
    page: input.page ?? null,
  })
  return response.data.id
}

export async function getMyFeedback(): Promise<MyFeedback[]> {
  const response = await apiClient.get<{ feedback: MyFeedback[] }>(
    '/api/feedback/mine',
  )
  return response.data.feedback ?? []
}

export async function getFeedbackQueue(params?: {
  status?: FeedbackStatus
  languageId?: string | null
  /** Only the reports that name no language — "the app is broken" is not
   * about the course the sender happened to have open. */
  unassigned?: boolean
}): Promise<{ feedback: FeedbackItem[]; open_count: number }> {
  const response = await apiClient.get('/api/feedback', {
    params: {
      status_filter: params?.status,
      language_id: params?.languageId ?? undefined,
      unassigned: params?.unassigned || undefined,
    },
  })
  return {
    feedback: response.data.feedback ?? [],
    open_count: response.data.open_count ?? 0,
  }
}

export async function triageFeedback(
  id: string,
  status: FeedbackStatus,
  adminNote?: string,
): Promise<void> {
  await apiClient.put(`/api/feedback/${id}`, {
    status,
    admin_note: adminNote?.trim() ? adminNote.trim() : null,
  })
}

export interface FeedbackSummary {
  open_count: number
  /** ISO timestamp of the newest item, or null when there is none. */
  latest_at: string | null
}

/**
 * The cheap "is anything waiting?" check the dashboard makes on load.
 * Deliberately not getFeedbackQueue: that pulls every row, and the home page
 * should not pay for a screen the learner may never open.
 */
export async function getFeedbackSummary(): Promise<FeedbackSummary> {
  const response = await apiClient.get<FeedbackSummary>('/api/feedback/summary')
  return {
    open_count: response.data.open_count ?? 0,
    latest_at: response.data.latest_at ?? null,
  }
}
