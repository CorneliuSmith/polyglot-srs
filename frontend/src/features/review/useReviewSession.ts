import { useState, useRef, useCallback } from 'react'
import type { DueCard, ValidateAnswerResponse } from '../../api/types'

export type ReviewPhase = 'answering' | 'feedback' | 'rating' | 'summary'

export interface SessionResult {
  cardId: string
  answerResult: string
  timeTakenMs: number
}

export interface ReviewSessionState {
  currentCard: DueCard | null
  currentIndex: number
  phase: ReviewPhase
  validationResult: ValidateAnswerResponse | null
  results: SessionResult[]
  isComplete: boolean
  accuracy: number
  totalTimeMs: number
  cardsReviewed: number
  setValidationResult: (result: ValidateAnswerResponse) => void
  rate: (answerResult: string) => void
  advance: () => void
  elapsedMs: () => number
}

export function useReviewSession(cards: DueCard[]): ReviewSessionState {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [phase, setPhase] = useState<ReviewPhase>('answering')
  const [validationResult, setValidationResultState] =
    useState<ValidateAnswerResponse | null>(null)
  const [results, setResults] = useState<SessionResult[]>([])
  // Missed cards are appended here and re-drilled before the session ends,
  // so a session only completes once everything has been produced correctly.
  const [requeued, setRequeued] = useState<DueCard[]>([])
  const cardStartTime = useRef<number>(Date.now())

  const deck = [...cards, ...requeued]
  const currentCard = deck[currentIndex] ?? null
  const isComplete = currentIndex >= deck.length

  const accuracy =
    results.length === 0
      ? 0
      : results.filter(
          (r) => r.answerResult === 'correct' || r.answerResult === 'correct_sloppy',
        ).length / results.length

  const totalTimeMs = results.reduce((sum, r) => sum + r.timeTakenMs, 0)
  // Unique cards, so re-drilled misses don't inflate the summary.
  const cardsReviewed = new Set(results.map((r) => r.cardId)).size

  const setValidationResult = useCallback((result: ValidateAnswerResponse) => {
    setValidationResultState(result)
    setPhase('feedback')
  }, [])

  const rate = useCallback(
    (answerResult: string) => {
      const timeTakenMs = Date.now() - cardStartTime.current
      const missed = answerResult === 'wrong' || answerResult === 'wrong_form'
      if (currentCard) {
        setResults((prev) => [
          ...prev,
          { cardId: currentCard.id, answerResult, timeTakenMs },
        ])
        if (missed) {
          setRequeued((prev) => [...prev, currentCard])
        }
      }
      const nextIndex = currentIndex + 1
      const deckLength = deck.length + (missed && currentCard ? 1 : 0)
      if (nextIndex >= deckLength) {
        setPhase('summary')
        setCurrentIndex(nextIndex)
      } else {
        setCurrentIndex(nextIndex)
        setPhase('answering')
        setValidationResultState(null)
        cardStartTime.current = Date.now()
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [currentCard, currentIndex, deck.length],
  )

  const advance = useCallback(() => {
    setCurrentIndex((i) => i + 1)
    setPhase('answering')
    setValidationResultState(null)
    cardStartTime.current = Date.now()
  }, [])

  const elapsedMs = useCallback(() => {
    return Date.now() - cardStartTime.current
  }, [])

  return {
    currentCard,
    currentIndex,
    phase,
    validationResult,
    results,
    isComplete,
    accuracy,
    totalTimeMs,
    cardsReviewed,
    setValidationResult,
    rate,
    advance,
    elapsedMs,
  }
}
