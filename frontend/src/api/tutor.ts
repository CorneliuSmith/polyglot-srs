import apiClient from './client'

export interface TutorMessage {
  role: 'user' | 'assistant'
  content: string
}

/**
 * The message allowance for the caller's tier. Pricing is flat — the cap is
 * fair-use cost protection, shown openly, never a billing meter.
 */
export interface TutorAllowance {
  tier: 'free' | 'plus' | 'unlimited'
  unlimited: boolean
  entitled: boolean
  limit: number | null
  used: number | null
  remaining: number | null
  resets_at: string | null
}

export interface TutorStatus {
  available: boolean
  entitled: boolean
  allowance: TutorAllowance | null
}

export async function getTutorStatus(
  languageId: string,
  languageCode: string,
): Promise<TutorStatus> {
  const response = await apiClient.get<TutorStatus>('/api/tutor/status', {
    params: { language_id: languageId, language_code: languageCode },
  })
  return response.data
}

export async function sendTutorMessage(
  languageId: string,
  languageCode: string,
  messages: TutorMessage[],
): Promise<{ reply: string; allowance: TutorAllowance | null }> {
  const response = await apiClient.post<{
    reply: string
    allowance?: TutorAllowance
  }>('/api/tutor/chat', {
    language_id: languageId,
    language_code: languageCode,
    messages,
  })
  return { reply: response.data.reply, allowance: response.data.allowance ?? null }
}

/**
 * Tell the backend a session is over so it can summarize the conversation
 * into the learner's durable memory. Best-effort — callers ignore failures.
 */
export async function endTutorSession(
  languageId: string,
  languageCode: string,
  messages: TutorMessage[],
): Promise<void> {
  await apiClient.post('/api/tutor/session/end', {
    language_id: languageId,
    language_code: languageCode,
    messages,
  })
}
