import apiClient from './client'

/** The five buckets on the send form. Kept short on purpose: a long taxonomy
 *  makes people stop and choose instead of typing, and triage only needs
 *  enough to route. */
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
}): Promise<{ feedback: FeedbackItem[]; open_count: number }> {
  const response = await apiClient.get('/api/feedback', {
    params: {
      status_filter: params?.status,
      language_id: params?.languageId ?? undefined,
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
