import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { getDueCards, validateAnswer, submitReview } from '../../api/review'
import { usePrefsStore } from '../../stores/prefsStore'
import { useReviewSession } from './useReviewSession'
import DrillCard from './DrillCard'
import FeedbackPanel from './FeedbackPanel'
import RatingButtons from './RatingButtons'
import SessionSummary from './SessionSummary'

export default function ReviewSessionPage() {
  const navigate = useNavigate()
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)
  const [userInput, setUserInput] = useState('')
  const [lastInput, setLastInput] = useState('')

  const { data: cards = [], isLoading } = useQuery({
    queryKey: ['due-cards', activeLanguageId],
    queryFn: () => getDueCards(activeLanguageId!),
    enabled: !!activeLanguageId,
  })

  const session = useReviewSession(cards)

  const validateMutation = useMutation({
    mutationFn: validateAnswer,
    onSuccess: (result) => {
      setLastInput(userInput)
      session.setValidationResult(result)
      setUserInput('')
    },
  })

  const submitMutation = useMutation({
    mutationFn: submitReview,
    onSuccess: () => {
      // card already advanced in rate()
    },
  })

  const handleSubmitAnswer = () => {
    const card = session.currentCard
    if (!card || !userInput.trim() || validateMutation.isPending) return

    validateMutation.mutate({
      language_code: card.language_code,
      user_input: userInput.trim(),
      correct_answer: card.correct_answer,
      card_context: {
        morphology: card.morphology,
        alternatives: card.alternatives,
      },
    })
  }

  const handleRate = (answerResult: string) => {
    const card = session.currentCard
    if (!card || submitMutation.isPending) return

    submitMutation.mutate({
      card_id: card.id,
      answer_result: answerResult,
      time_taken_ms: session.elapsedMs(),
    })

    session.rate(answerResult)
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-500">Loading cards…</p>
      </div>
    )
  }

  if (!isLoading && cards.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="text-center space-y-4">
          <p className="text-xl text-gray-700">No cards due! Come back later.</p>
          <button
            type="button"
            onClick={() => navigate('/')}
            className="text-indigo-600 hover:underline text-sm"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    )
  }

  if (session.phase === 'summary' || session.isComplete) {
    return (
      <SessionSummary
        accuracy={session.accuracy}
        totalTimeMs={session.totalTimeMs}
        cardsReviewed={session.cardsReviewed}
        onFinish={() => navigate('/')}
      />
    )
  }

  const card = session.currentCard
  if (!card) return null

  const dir = card.language_code === 'ar' ? 'rtl' : 'ltr'

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
        {/* Progress */}
        <div className="flex items-center justify-between text-sm text-gray-500">
          <span>
            Card {session.currentIndex + 1} of {cards.length}
          </span>
          <span className="capitalize">{card.card_type}</span>
        </div>

        {/* Progress bar */}
        <div className="w-full bg-gray-200 rounded-full h-1.5">
          <div
            className="bg-indigo-500 h-1.5 rounded-full transition-all"
            style={{ width: `${((session.currentIndex) / cards.length) * 100}%` }}
          />
        </div>

        {/* Card area */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
          {card.hint && (
            <p className="text-sm text-gray-400 text-center mb-4">{card.hint}</p>
          )}

          <DrillCard
            sentence={card.sentence}
            value={userInput}
            onChange={setUserInput}
            onSubmit={handleSubmitAnswer}
            disabled={session.phase !== 'answering' || validateMutation.isPending}
            dir={dir}
          />

          {card.translation && session.phase === 'answering' && (
            <p className="text-xs text-gray-400 text-center mt-4">{card.translation}</p>
          )}

          {session.phase !== 'answering' && (
            <button
              type="button"
              onClick={handleSubmitAnswer}
              disabled={validateMutation.isPending || session.phase !== 'answering'}
              className="hidden"
            />
          )}
        </div>

        {/* Submit button (answering phase) */}
        {session.phase === 'answering' && (
          <button
            type="button"
            onClick={handleSubmitAnswer}
            disabled={!userInput.trim() || validateMutation.isPending}
            className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold rounded-xl px-6 py-3 text-sm transition-colors"
            style={{ minHeight: '44px' }}
          >
            {validateMutation.isPending ? 'Checking…' : 'Submit Answer'}
          </button>
        )}

        {/* Feedback phase */}
        {(session.phase === 'feedback' || session.phase === 'rating') &&
          session.validationResult && (
            <div className="space-y-4">
              <FeedbackPanel
                answerResult={session.validationResult.answer_result}
                feedback={session.validationResult.feedback}
                correctAnswer={card.correct_answer}
                userInput={lastInput}
              />
              <RatingButtons
                onRate={handleRate}
                nlpResult={session.validationResult.answer_result}
              />
            </div>
          )}
      </div>
    </div>
  )
}
