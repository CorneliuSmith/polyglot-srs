import apiClient from './client'

export interface TutorMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface TutorStatus {
  available: boolean
  entitled: boolean
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
): Promise<string> {
  const response = await apiClient.post<{ reply: string }>('/api/tutor/chat', {
    language_id: languageId,
    language_code: languageCode,
    messages,
  })
  return response.data.reply
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
