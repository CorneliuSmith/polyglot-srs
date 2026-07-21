import apiClient from './client'

export interface ExtractedWord {
  word: string
  normalized: string
  known: boolean
  definition: string | null
}

export interface ExtractedSentence {
  sentence: string
  words: ExtractedWord[]
}

export async function extractText(
  languageId: string,
  languageCode: string,
  text: string,
): Promise<ExtractedSentence[]> {
  const response = await apiClient.post<{ sentences: ExtractedSentence[] }>(
    '/api/notes/extract',
    { language_id: languageId, language_code: languageCode, text },
  )
  return response.data.sentences
}

export async function saveNote(
  languageId: string,
  content: string,
  title?: string,
): Promise<{ id: string }> {
  const response = await apiClient.post('/api/notes', {
    language_id: languageId,
    content,
    title,
  })
  return response.data
}

export async function createPersonalCard(input: {
  languageId: string
  languageCode: string
  sentence: string
  answer: string
  translation?: string
  noteId?: string
  // Fallback prompt when the word appears inflected in the sentence and a
  // cloze can't be built (backend makes a type-the-word card instead).
  gloss?: string
}): Promise<{ id: string; sentence: string }> {
  const response = await apiClient.post('/api/notes/cards', {
    language_id: input.languageId,
    language_code: input.languageCode,
    sentence: input.sentence,
    answer: input.answer,
    translation: input.translation ?? '',
    note_id: input.noteId ?? null,
    gloss: input.gloss ?? '',
  })
  return response.data
}
