import { describe, it, expect } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useReviewSession } from '../features/review/useReviewSession'
import type { DueCard } from '../api/types'

function makeCard(overrides: Partial<DueCard> = {}): DueCard {
  return {
    id: 'card-1',
    card_type: 'grammar',
    card_id: 'grammar-1',
    sentence: 'I {{answer}} to school.',
    correct_answer: 'go',
    language_code: 'en',
    morphology: {},
    alternatives: [],
    ease_factor: 2.5,
    interval: 1,
    repetitions: 0,
    streak: 0,
    lapses: 0,
    next_review: '2026-03-15T00:00:00Z',
    ...overrides,
  }
}

const card1 = makeCard({ id: 'card-1', sentence: 'I {{answer}} to school.', correct_answer: 'go' })
const card2 = makeCard({ id: 'card-2', sentence: 'She {{answer}} home.', correct_answer: 'runs' })

describe('useReviewSession', () => {
  describe('initial state', () => {
    it('starts in answering phase', () => {
      const { result } = renderHook(() => useReviewSession([card1]))
      expect(result.current.phase).toBe('answering')
    })

    it('currentCard is the first card', () => {
      const { result } = renderHook(() => useReviewSession([card1, card2]))
      expect(result.current.currentCard?.id).toBe('card-1')
    })

    it('currentIndex starts at 0', () => {
      const { result } = renderHook(() => useReviewSession([card1]))
      expect(result.current.currentIndex).toBe(0)
    })

    it('isComplete is false when there are cards', () => {
      const { result } = renderHook(() => useReviewSession([card1]))
      expect(result.current.isComplete).toBe(false)
    })

    it('isComplete is true when cards array is empty', () => {
      const { result } = renderHook(() => useReviewSession([]))
      expect(result.current.isComplete).toBe(true)
    })
  })

  describe('phase transitions', () => {
    it('transitions from answering to feedback on setValidationResult', () => {
      const { result } = renderHook(() => useReviewSession([card1]))
      act(() => {
        result.current.setValidationResult({ answer_result: 'correct', feedback: null })
      })
      expect(result.current.phase).toBe('feedback')
    })

    it('stores validation result', () => {
      const { result } = renderHook(() => useReviewSession([card1]))
      const validation = { answer_result: 'correct' as const, feedback: 'Great job!' }
      act(() => {
        result.current.setValidationResult(validation)
      })
      expect(result.current.validationResult).toEqual(validation)
    })

    it('rate() advances to next card in answering phase', () => {
      const { result } = renderHook(() => useReviewSession([card1, card2]))
      act(() => {
        result.current.setValidationResult({ answer_result: 'correct', feedback: null })
      })
      act(() => {
        result.current.rate('correct')
      })
      expect(result.current.phase).toBe('answering')
      expect(result.current.currentIndex).toBe(1)
      expect(result.current.currentCard?.id).toBe('card-2')
    })

    it('rate() transitions to summary when all cards are done', () => {
      const { result } = renderHook(() => useReviewSession([card1]))
      act(() => {
        result.current.setValidationResult({ answer_result: 'correct', feedback: null })
      })
      act(() => {
        result.current.rate('correct')
      })
      expect(result.current.phase).toBe('summary')
      expect(result.current.isComplete).toBe(true)
    })

    it('rate() clears validation result on advance', () => {
      const { result } = renderHook(() => useReviewSession([card1, card2]))
      act(() => {
        result.current.setValidationResult({ answer_result: 'correct', feedback: null })
      })
      act(() => {
        result.current.rate('correct')
      })
      expect(result.current.validationResult).toBeNull()
    })
  })

  describe('results accumulation', () => {
    it('accumulates results after rating', () => {
      const { result } = renderHook(() => useReviewSession([card1, card2]))
      act(() => {
        result.current.setValidationResult({ answer_result: 'correct', feedback: null })
      })
      act(() => {
        result.current.rate('correct')
      })
      expect(result.current.results).toHaveLength(1)
      expect(result.current.results[0].cardId).toBe('card-1')
      expect(result.current.results[0].answerResult).toBe('correct')
    })

    it('cardsReviewed equals number of completed ratings', () => {
      const { result } = renderHook(() => useReviewSession([card1, card2]))
      act(() => {
        result.current.setValidationResult({ answer_result: 'correct', feedback: null })
      })
      act(() => {
        result.current.rate('correct')
      })
      act(() => {
        result.current.setValidationResult({ answer_result: 'wrong', feedback: null })
      })
      act(() => {
        result.current.rate('wrong')
      })
      expect(result.current.cardsReviewed).toBe(2)
    })
  })

  describe('accuracy computation', () => {
    it('accuracy is 0 with no results', () => {
      const { result } = renderHook(() => useReviewSession([card1]))
      expect(result.current.accuracy).toBe(0)
    })

    it('accuracy is 1.0 when all answers are correct', () => {
      const { result } = renderHook(() => useReviewSession([card1]))
      act(() => {
        result.current.setValidationResult({ answer_result: 'correct', feedback: null })
      })
      act(() => {
        result.current.rate('correct')
      })
      expect(result.current.accuracy).toBe(1.0)
    })

    it('accuracy includes correct_sloppy as correct', () => {
      const { result } = renderHook(() => useReviewSession([card1, card2]))
      act(() => {
        result.current.setValidationResult({ answer_result: 'correct', feedback: null })
      })
      act(() => {
        result.current.rate('correct_sloppy')
      })
      act(() => {
        result.current.setValidationResult({ answer_result: 'wrong', feedback: null })
      })
      act(() => {
        result.current.rate('wrong')
      })
      expect(result.current.accuracy).toBe(0.5)
    })

    it('accuracy is 0 when all answers are wrong', () => {
      const { result } = renderHook(() => useReviewSession([card1]))
      act(() => {
        result.current.setValidationResult({ answer_result: 'wrong', feedback: null })
      })
      act(() => {
        result.current.rate('wrong')
      })
      expect(result.current.accuracy).toBe(0)
    })
  })

  describe('missed cards are re-drilled before the session ends', () => {
    it('a wrong answer requeues the card at the end of the deck', () => {
      const { result } = renderHook(() => useReviewSession([card1, card2]))
      act(() => {
        result.current.rate('wrong')
      })
      act(() => {
        result.current.rate('correct')
      })
      // Both originals done, but the missed card comes back.
      expect(result.current.isComplete).toBe(false)
      expect(result.current.currentCard?.id).toBe('card-1')
      act(() => {
        result.current.rate('correct')
      })
      expect(result.current.isComplete).toBe(true)
    })

    it('wrong_form also requeues; correct does not', () => {
      const { result } = renderHook(() => useReviewSession([card1]))
      act(() => {
        result.current.rate('wrong_form')
      })
      expect(result.current.isComplete).toBe(false)
      expect(result.current.currentCard?.id).toBe('card-1')
      act(() => {
        result.current.rate('correct_sloppy')
      })
      expect(result.current.isComplete).toBe(true)
    })

    it('cardsReviewed counts unique cards, not retry attempts', () => {
      const { result } = renderHook(() => useReviewSession([card1]))
      act(() => {
        result.current.rate('wrong')
      })
      act(() => {
        result.current.rate('correct')
      })
      expect(result.current.results).toHaveLength(2) // both attempts recorded
      expect(result.current.cardsReviewed).toBe(1)   // one card studied
    })
  })

  describe('retry (typo re-entry)', () => {
    it('returns to answering on the same card without recording a result', () => {
      const { result } = renderHook(() => useReviewSession([card1, card2]))
      act(() => {
        result.current.setValidationResult({ answer_result: 'wrong', feedback: null })
      })
      expect(result.current.phase).toBe('feedback')
      act(() => {
        result.current.retry()
      })
      expect(result.current.phase).toBe('answering')
      expect(result.current.currentCard?.id).toBe('card-1') // same card
      expect(result.current.results).toHaveLength(0)        // nothing recorded
      expect(result.current.validationResult).toBeNull()
    })
  })

  describe('elapsedMs', () => {
    it('returns a non-negative number', () => {
      const { result } = renderHook(() => useReviewSession([card1]))
      const elapsed = result.current.elapsedMs()
      expect(elapsed).toBeGreaterThanOrEqual(0)
    })
  })
})
