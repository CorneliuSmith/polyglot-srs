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
  const cardStartTime = useRef<number>(Date.now())

  const currentCard = cards[currentIndex] ?? null
  const isComplete = currentIndex >= cards.length

  const accuracy =
    results.length === 0
      ? 0
      : results.filter(
          (r) => r.answerResult === 'correct' || r.answerResult === 'correct_sloppy',
        ).length / results.length

  const totalTimeMs = results.reduce((sum, r) => sum + r.timeTakenMs, 0)
  const cardsReviewed = results.length

  const setValidationResult = useCallback((result: ValidateAnswerResponse) => {
    setValidationResultState(result)
    setPhase('feedback')
  }, [])

  const rate = useCallback(
    (answerResult: string) => {
      const timeTakenMs = Date.now() - cardStartTime.current
      if (currentCard) {
        setResults((prev) => [
          ...prev,
          { cardId: currentCard.id, answerResult, timeTakenMs },
        ])
      }
      const nextIndex = currentIndex + 1
      if (nextIndex >= cards.length) {
        setPhase('summary')
        setCurrentIndex(nextIndex)
      } else {
        setCurrentIndex(nextIndex)
        setPhase('answering')
        setValidationResultState(null)
        cardStartTime.current = Date.now()
      }
    },
    [currentCard, currentIndex, cards.length],
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
