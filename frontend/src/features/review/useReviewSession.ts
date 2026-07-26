import { useState, useRef, useCallback } from 'react'
import type { DueCard, ValidateAnswerResponse } from '../../api/types'

export type ReviewPhase = 'answering' | 'feedback' | 'rating' | 'summary'

export interface SessionResult {
  cardId: string
  answerResult: string
  timeTakenMs: number
}

/** Where to pick a parked session back up (the settings round-trip). */
export interface SessionResume {
  index: number
  results: SessionResult[]
  requeued: DueCard[]
}

export interface ReviewSessionState {
  currentCard: DueCard | null
  currentIndex: number
  phase: ReviewPhase
  validationResult: ValidateAnswerResponse | null
  results: SessionResult[]
  /** Missed cards queued for re-drill — exposed so a snapshot can park them. */
  requeued: DueCard[]
  isComplete: boolean
  accuracy: number
  totalTimeMs: number
  cardsReviewed: number
  setValidationResult: (result: ValidateAnswerResponse) => void
  rate: (answerResult: string) => void
  retry: () => void
  advance: () => void
  resume: () => void
  elapsedMs: () => number
}

export function useReviewSession(
  cards: DueCard[],
  restore?: SessionResume,
): ReviewSessionState {
  // A parked session (settings round-trip) restores its position, its recorded
  // results, and its re-drill queue — always back into 'answering' (mid-card
  // validation state is deliberately not parked).
  const [currentIndex, setCurrentIndex] = useState(restore?.index ?? 0)
  const [phase, setPhase] = useState<ReviewPhase>('answering')
  const [validationResult, setValidationResultState] =
    useState<ValidateAnswerResponse | null>(null)
  const [results, setResults] = useState<SessionResult[]>(restore?.results ?? [])
  // Missed cards are appended here and re-drilled before the session ends,
  // so a session only completes once everything has been produced correctly.
  const [requeued, setRequeued] = useState<DueCard[]>(restore?.requeued ?? [])
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

  // Bunpro-style "typo — let me re-enter": discard the judgement and return
  // to answering the SAME card. Nothing is recorded or submitted, and the
  // timer keeps running, so a retried answer still reports honest time-taken.
  const retry = useCallback(() => {
    setPhase('answering')
    setValidationResultState(null)
  }, [])

  // Move on without recording anything (Skip, or after retiring a card).
  // Skipping the last card ends the session like rating it would.
  const advance = useCallback(() => {
    const next = currentIndex + 1
    setCurrentIndex(next)
    if (next >= deck.length) {
      setPhase('summary')
    } else {
      setPhase('answering')
    }
    setValidationResultState(null)
    cardStartTime.current = Date.now()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentIndex, deck.length])

  // Cram only: cards can be appended after the deck was exhausted (background
  // generation lands more drills). currentIndex already points at the fresh
  // card, but the phase is stuck on 'summary' — drop back to answering so the
  // session flows straight into the new questions without a remount.
  const resume = useCallback(() => {
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
    requeued,
    isComplete,
    accuracy,
    totalTimeMs,
    cardsReviewed,
    setValidationResult,
    rate,
    retry,
    advance,
    resume,
    elapsedMs,
  }
}
