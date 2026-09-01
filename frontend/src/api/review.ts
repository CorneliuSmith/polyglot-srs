import apiClient from './client'
import { usePrefsStore } from '../stores/prefsStore'
import type {
  CardDetail,
  DueCard,
  ValidateAnswerRequest,
  ValidateAnswerResponse,
  SubmitReviewRequest,
  SubmitReviewResponse,
  LearnDeck,
  LearnResponse,
  Lesson,
  SessionReadiness,
} from './types'

export async function getCardDetail(cardId: string): Promise<CardDetail> {
  const response = await apiClient.get<CardDetail>(
    `/api/review/card/${cardId}/detail`,
  )
  return response.data
}

export async function getDueCards(
  languageId: string,
  limit?: number,
  cardType?: 'vocabulary' | 'grammar',
): Promise<DueCard[]> {
  const response = await apiClient.get<DueCard[]>('/api/review/due', {
    params: {
      language_id: languageId,
      ...(limit ? { limit } : {}),
      ...(cardType ? { card_type: cardType } : {}),
    },
  })
  return response.data
}

export interface DeckPreview {
  id: string
  title: string
  list_type: 'vocabulary' | 'grammar'
  level: string | null
  items: { item: string; detail: string | null }[]
}

/** Peek inside a deck (its first items) before adding it to the queue. */
export async function getDeckPreview(listId: string): Promise<DeckPreview> {
  const response = await apiClient.get<DeckPreview>(
    `/api/review/decks/${listId}/preview`,
  )
  return response.data
}

/** Add or remove a deck from the learn queue (removal never loses progress). */
export async function setDeckSubscription(
  listId: string,
  subscribed: boolean,
): Promise<void> {
  await apiClient.post(`/api/review/decks/${listId}/subscription`, { subscribed })
}

/** Quick-Cram (WP13f): ungraded practice cards for a set of grammar points.
 * Nothing here touches SRS state — cram sessions never call submitReview. */
export async function getCramCards(
  pointIds: string[],
  count?: number,
): Promise<DueCard[]> {
  const response = await apiClient.get<DueCard[]>('/api/review/cram', {
    params: { point_ids: pointIds.join(','), ...(count ? { count } : {}) },
  })
  return response.data
}

export async function validateAnswer(
  req: ValidateAnswerRequest,
): Promise<ValidateAnswerResponse> {
  const response = await apiClient.post<ValidateAnswerResponse>(
    '/api/review/validate-answer',
    req,
  )
  const data = response.data
  // Accents optional (beta request): a diacritic-only miss is graded
  // 'correct_sloppy' with an "Almost — check the accents" note. When the
  // learner has turned accents off, promote it to a full 'correct' and drop
  // the note, so it reads and scores green everywhere downstream.
  if (
    data.answer_result === 'correct_sloppy' &&
    usePrefsStore.getState().accentsOptional
  ) {
    return { ...data, answer_result: 'correct', feedback: null }
  }
  return data
}

export async function submitReview(
  req: SubmitReviewRequest,
): Promise<SubmitReviewResponse> {
  const response = await apiClient.post<SubmitReviewResponse>(
    '/api/review/submit',
    req,
  )
  return response.data
}

export async function submitCardFeedback(
  cardId: string,
  message: string,
): Promise<void> {
  await apiClient.post(`/api/review/card/${cardId}/feedback`, { message })
}

/** Retire a card the learner already knows: it stops appearing in reviews
 * (suspended with history intact — reversible via Settings → reset). */
export async function markCardKnown(cardId: string): Promise<void> {
  await apiClient.post(`/api/review/card/${cardId}/known`)
}

/** Reset ONE card's progress — the individual-card sibling of
 * resetDeckProgress/resetProgress. Deletes its whole history; the card is a
 * brand-new Learn candidate again immediately. Also how a mistaken "I
 * already know this" gets undone. */
export async function resetCardProgress(cardId: string): Promise<void> {
  await apiClient.delete(`/api/review/card/${cardId}/progress`)
}

export async function getSessionReadiness(
  languageId: string,
  limit?: number,
): Promise<SessionReadiness> {
  const response = await apiClient.get<SessionReadiness>('/api/review/readiness', {
    params: { language_id: languageId, ...(limit ? { limit } : {}) },
  })
  return response.data
}

/** Re-serve lesson payloads mid-session — the live swap. Whatever the
 * translation loop has landed since the session started comes back in the
 * learner's language. */
export async function refreshLessons(cardIds: string[]): Promise<Lesson[]> {
  const response = await apiClient.post<{ lessons: Lesson[] }>(
    '/api/review/lessons/refresh',
    { card_ids: cardIds },
  )
  return response.data.lessons
}

/** The review side of the live swap: re-serve due cards already in a
 * session, by user_card id. A returning learner starts at once, so their
 * deck can open with sentences still in English; this brings back whatever
 * has been translated since. Cards not returned are kept as they were. */
export async function refreshDueCards(
  languageId: string,
  ids: string[],
): Promise<DueCard[]> {
  const response = await apiClient.post<{ cards: DueCard[] }>(
    '/api/review/due/refresh',
    { language_id: languageId, ids },
  )
  return response.data.cards
}

export async function startLearnSession(
  languageId: string,
  cardType: 'vocabulary' | 'grammar' | 'both' = 'vocabulary',
  level?: string,
  /** Topic Lens: scope the batch to one semantic bucket (vocabulary only).
   * The server treats an unknown slug as unscoped, so a stale link still
   * learns rather than erroring. */
  topic?: string,
): Promise<LearnResponse> {
  const response = await apiClient.post<LearnResponse>('/api/review/learn', {
    language_id: languageId,
    card_type: cardType,
    ...(level ? { level } : {}),
    ...(topic ? { topic } : {}),
  })
  return response.data
}

export interface TopicDeck {
  topic: string
  /** Learnable words inside the caller's SUBSCRIBED level lists. */
  total: number
  /** Started words — counted regardless of subscription (progress shows
   * even after unsubscribing a level), so it can exceed total; cap the
   * display. */
  learned: number
}

/** The Topic Lens deck rows. Empty until the language's classification has
 * run (and, under strict review policy, been confirmed) — the By-topic
 * toggle only renders when this has rows. */
export async function getTopicSummary(languageId: string): Promise<TopicDeck[]> {
  const response = await apiClient.get<{ topics: TopicDeck[] }>(
    '/api/review/topics',
    { params: { language_id: languageId } },
  )
  return response.data.topics
}

export async function confirmLearnSession(
  cardIds: string[],
): Promise<{ confirmed: number }> {
  const response = await apiClient.post<{ confirmed: number }>(
    '/api/review/learn/confirm',
    { card_ids: cardIds },
  )
  return response.data
}

export async function getLearnDecks(languageId: string): Promise<LearnDeck[]> {
  const response = await apiClient.get<{ decks: LearnDeck[] | null }>(
    '/api/review/decks',
    { params: { language_id: languageId } },
  )
  // Coerce a null body/field to an empty list: a React Query `= []` default
  // only catches `undefined`, so returning null here would crash callers
  // that immediately `.filter`/`.find` on the result (the Decks page hitting
  // the route error boundary on load).
  return response.data?.decks ?? []
}

export async function resetDeckProgress(
  listId: string,
): Promise<{ cards_deleted: number }> {
  const response = await apiClient.delete<{ cards_deleted: number }>(
    `/api/review/decks/${listId}/progress`,
  )
  return response.data
}

export async function resetProgress(
  languageId?: string,
): Promise<{ cards_deleted: number }> {
  const response = await apiClient.delete<{ cards_deleted: number }>(
    '/api/review/progress',
    { params: languageId ? { language_id: languageId } : {} },
  )
  return response.data
}

/** The caller's own progress on this item: 'new' (never learned), 'learning'
 * (taught, awaiting the Learn first-check), 'known' (retired — marked
 * already-known, either from Learn or Review), 'active' (in normal review
 * rotation). */
export type CardStatus = 'new' | 'learning' | 'known' | 'active'

export interface DeckItem {
  id: string
  kind: 'grammar' | 'vocabulary'
  item: string
  detail: string | null
  level: string | null
  reviewed: boolean
  status: CardStatus
  user_card_id: string | null
}

export interface DeckListing {
  id: string
  title: string
  list_type: 'grammar' | 'vocabulary'
  level: string | null
  items: DeckItem[]
}

export async function getDeckItems(listId: string): Promise<DeckListing> {
  const response = await apiClient.get<DeckListing>(
    `/api/review/decks/${listId}/items`,
  )
  return response.data
}

export interface VocabItemDetail {
  id: string
  word: string
  reading: string | null
  part_of_speech: string | null
  usage_note: string | null
  definition: string | null
  level: string | null
  language_code: string
  morphology: Record<string, unknown> | string | null
  examples: { sentence: string; translation: string | null }[]
}

export async function getVocabItem(vocabId: string): Promise<VocabItemDetail> {
  const response = await apiClient.get<VocabItemDetail>(
    `/api/review/vocab/${vocabId}`,
  )
  return response.data
}

export interface TriviaQuestion {
  id: string
  question: string
  options: string[]
  answer_index: number
  fact: string
}

/** Language trivia in the learner's support language. Shared bank, so it
 * works even when nothing in their own session has been translated yet. */
export async function getTrivia(limit = 6): Promise<TriviaQuestion[]> {
  const { data } = await apiClient.get<{ questions: TriviaQuestion[] }>(
    '/api/review/trivia',
    { params: { limit } },
  )
  return data.questions ?? []
}

/** Record what was asked, so the bank rotates instead of repeating. */
export async function markTriviaSeen(triviaIds: string[]): Promise<void> {
  if (!triviaIds.length) return
  await apiClient.post('/api/review/trivia/seen', { trivia_ids: triviaIds })
}
