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
): Promise<{ points: GrammarPointEdit[]; is_admin: boolean }> {
  const response = await apiClient.get('/api/contribute/grammar', {
    params: { language_id: languageId },
  })
  return response.data
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

export async function deleteDrill(pointId: string, drillId: string): Promise<void> {
  await apiClient.delete(`/api/contribute/grammar/${pointId}/drills/${drillId}`)
}
