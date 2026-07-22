import apiClient from './client'

export interface PersonalDeck {
  id: string
  name: string
  card_count: number
}

export interface PersonalCard {
  id: string
  answer: string
  // Nullable in practice: cards minted without a cloze context (e.g. a bare
  // word added from the Reader) can arrive with no sentence.
  sentence: string | null
  translation: string | null
  deck_id: string | null
}

export async function getPersonalDecks(languageId: string): Promise<PersonalDeck[]> {
  const { data } = await apiClient.get('/api/personal-decks', {
    params: { language_id: languageId },
  })
  // null → [] : a React Query `= []` default only catches undefined, so a
  // null body would crash callers that map/length over the result on render.
  return data ?? []
}

export async function createPersonalDeck(languageId: string, name: string): Promise<{ id: string }> {
  const { data } = await apiClient.post('/api/personal-decks', {
    language_id: languageId,
    name,
  })
  return data
}

export async function renamePersonalDeck(deckId: string, name: string): Promise<void> {
  await apiClient.patch(`/api/personal-decks/${deckId}`, { name })
}

export async function deletePersonalDeck(deckId: string): Promise<void> {
  await apiClient.delete(`/api/personal-decks/${deckId}`)
}

export async function getPersonalCards(languageId: string): Promise<PersonalCard[]> {
  const { data } = await apiClient.get('/api/personal-decks/cards', {
    params: { language_id: languageId },
  })
  return data ?? []
}

export async function filePersonalCard(cardId: string, deckId: string | null): Promise<void> {
  await apiClient.patch(`/api/personal-decks/cards/${cardId}`, { deck_id: deckId })
}
