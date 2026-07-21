import apiClient from './client'

export interface PersonalDeck {
  id: string
  name: string
  card_count: number
}

export interface PersonalCard {
  id: string
  answer: string
  sentence: string
  translation: string | null
  deck_id: string | null
}

export async function getPersonalDecks(languageId: string): Promise<PersonalDeck[]> {
  const { data } = await apiClient.get('/personal-decks', {
    params: { language_id: languageId },
  })
  return data
}

export async function createPersonalDeck(languageId: string, name: string): Promise<{ id: string }> {
  const { data } = await apiClient.post('/personal-decks', {
    language_id: languageId,
    name,
  })
  return data
}

export async function renamePersonalDeck(deckId: string, name: string): Promise<void> {
  await apiClient.patch(`/personal-decks/${deckId}`, { name })
}

export async function deletePersonalDeck(deckId: string): Promise<void> {
  await apiClient.delete(`/personal-decks/${deckId}`)
}

export async function getPersonalCards(languageId: string): Promise<PersonalCard[]> {
  const { data } = await apiClient.get('/personal-decks/cards', {
    params: { language_id: languageId },
  })
  return data
}

export async function filePersonalCard(cardId: string, deckId: string | null): Promise<void> {
  await apiClient.patch(`/personal-decks/cards/${cardId}`, { deck_id: deckId })
}
