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
