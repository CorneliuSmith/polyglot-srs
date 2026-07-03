import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { getDueCards, validateAnswer, submitReview } from '../../api/review'
import { usePrefsStore } from '../../stores/prefsStore'
import { useReviewSession } from './useReviewSession'
import DrillCard from './DrillCard'
import FeedbackPanel from './FeedbackPanel'
import ReviewDetail from './ReviewDetail'
import CardFeedback from './CardFeedback'
import SessionSummary from './SessionSummary'
import OnScreenKeyboard from '../keyboards/OnScreenKeyboard'
import type { KeyboardLanguage } from '../keyboards/OnScreenKeyboard'

export default function ReviewSessionPage() {
  const navigate = useNavigate()
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)
  const [userInput, setUserInput] = useState('')
  const [lastInput, setLastInput] = useState('')
  const [showKeyboard, setShowKeyboard] = useState(true)
  const [saveErrorCount, setSaveErrorCount] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

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

  // The session advances optimistically in rate(); if the backend save
  // fails, the review is lost server-side, so surface that to the user.
  const submitMutation = useMutation({
    mutationFn: submitReview,
    onError: () => {
      setSaveErrorCount((n) => n + 1)
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
        morphology: card.morphology ?? {},
        alternatives: card.alternatives ?? [],
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
      // sentences rotate per review — log which one was actually shown
      prompt_sentence: card.sentence,
    })

    session.rate(answerResult)
  }

  const handleKeyboardKeyPress = (key: string) => {
    const input = inputRef.current
    if (!input) {
      // If no ref available, just append
      setUserInput((prev) => prev + key)
      return
    }

    const start = input.selectionStart ?? input.value.length
    const end = input.selectionEnd ?? input.value.length
    const newValue = input.value.slice(0, start) + key + input.value.slice(end)
    setUserInput(newValue)

    // Restore cursor position after React re-render
    requestAnimationFrame(() => {
      input.focus()
      input.setSelectionRange(start + key.length, start + key.length)
    })
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
            className="text-indigo-600 hover:underline text-sm touch-manipulation"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    )
  }

  if (session.phase === 'summary' || session.isComplete) {
    return (
      <div>
        {saveErrorCount > 0 && (
          <div
            role="alert"
            className="max-w-2xl mx-auto mt-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl px-4 py-3"
          >
            {saveErrorCount === 1
              ? '1 review could not be saved and will reappear in a future session.'
              : `${saveErrorCount} reviews could not be saved and will reappear in a future session.`}
          </div>
        )}
        <SessionSummary
          accuracy={session.accuracy}
          totalTimeMs={session.totalTimeMs}
          cardsReviewed={session.cardsReviewed}
          onFinish={() => navigate('/')}
        />
      </div>
    )
  }

  const card = session.currentCard
  if (!card) return null

  // Non-Latin scripts and Latin languages with accents/diacritics get an
  // on-screen helper. (Xhosa/English omitted: plain ASCII.)
  const needsKeyboard = [
    'ru', 'ar', 'tr', 'yo', 'ha', 'es', 'it', 'fr', 'de', 'ca', 'mi',
  ].includes(card.language_code)

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
        {saveErrorCount > 0 && (
          <div
            role="alert"
            className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl px-4 py-3"
          >
            {saveErrorCount === 1
              ? 'Your last review could not be saved. Check your connection — it will reappear in a future session.'
              : `${saveErrorCount} reviews could not be saved. Check your connection — they will reappear in a future session.`}
          </div>
        )}
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
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 md:p-8">
          {card.hint && (
            <p className="text-sm text-gray-400 text-center mb-4">{card.hint}</p>
          )}

          <DrillCard
            sentence={card.sentence}
            value={userInput}
            onChange={setUserInput}
            onSubmit={handleSubmitAnswer}
            disabled={session.phase !== 'answering' || validateMutation.isPending}
            languageCode={card.language_code}
            inputRef={inputRef}
          />

          {card.translation && session.phase === 'answering' && (
            <p className="text-xs text-gray-400 text-center mt-4">{card.translation}</p>
          )}
        </div>

        {/* Submit button (answering phase) */}
        {session.phase === 'answering' && (
          <button
            type="button"
            onClick={handleSubmitAnswer}
            disabled={!userInput.trim() || validateMutation.isPending}
            className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold rounded-xl px-6 py-3 text-sm transition-colors touch-manipulation"
            style={{ minHeight: '44px' }}
          >
            {validateMutation.isPending ? 'Checking…' : 'Submit Answer'}
          </button>
        )}

        {/* On-screen keyboard for Russian and Arabic */}
        {needsKeyboard && session.phase === 'answering' && (
          <div className="space-y-2">
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setShowKeyboard((v) => !v)}
                className="text-xs text-gray-500 hover:text-gray-700 border border-gray-200 rounded-lg px-3 py-1.5 touch-manipulation"
                style={{ minHeight: '44px' }}
              >
                {showKeyboard ? 'Hide Keyboard' : 'Show Keyboard'}
              </button>
            </div>
            {showKeyboard && (
              <OnScreenKeyboard
                languageCode={card.language_code as KeyboardLanguage}
                onKeyPress={handleKeyboardKeyPress}
                inputRef={inputRef}
              />
            )}
          </div>
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
                languageCode={card.language_code}
              />
              <ReviewDetail
                cardId={card.id}
                cardType={card.card_type}
                languageCode={card.language_code}
              />
              {/* The answer was already graded by the NLP check; auto-record
                  that grade (it drives FSRS scheduling + the tutor's weak-area
                  analysis) and just let the learner continue, with a manual
                  override for a lucky-correct answer. */}
              <div className="space-y-2">
                <button
                  type="button"
                  onClick={() => handleRate(session.validationResult!.answer_result)}
                  disabled={submitMutation.isPending}
                  className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold rounded-xl px-6 py-3 text-sm transition-colors"
                  style={{ minHeight: '44px' }}
                >
                  Continue
                </button>
                {(session.validationResult.answer_result === 'correct' ||
                  session.validationResult.answer_result === 'correct_sloppy') ? (
                  <button
                    type="button"
                    onClick={() => handleRate('wrong')}
                    disabled={submitMutation.isPending}
                    className="block mx-auto text-xs text-gray-400 hover:text-red-500"
                  >
                    I actually got it wrong
                  </button>
                ) : (
                  /* Bunpro-style undo for slips: retype without recording a
                     grade — the retry still counts toward time-taken. */
                  <button
                    type="button"
                    onClick={() => {
                      setUserInput(lastInput)
                      session.retry()
                    }}
                    className="block mx-auto text-xs text-gray-400 hover:text-indigo-600"
                  >
                    Typo? Re-enter your answer
                  </button>
                )}
              </div>
              <div className="text-center">
                <CardFeedback cardId={card.id} />
              </div>
            </div>
          )}
      </div>
    </div>
  )
}
