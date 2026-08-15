import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { getTrivia, markTriviaSeen } from '../../api/review'

/**
 * Language and linguistics trivia, in the learner's own support language.
 *
 * The match game plays the words of the session being waited for, which
 * needs some of that session to exist. At 0% none of it does — and 0% is
 * exactly when someone is sitting on the wait screen. Trivia has no such
 * dependency: the bank is shared per locale, so it is stocked long before
 * this particular learner arrives.
 *
 * Renders nothing when the bank is empty. A game that can't be played is
 * worse than no game, and the caller falls back to plain progress.
 */
export default function TriviaGame({ onEmpty }: { onEmpty?: () => void }) {
  const { t } = useTranslation()
  const [index, setIndex] = useState(0)
  const [picked, setPicked] = useState<number | null>(null)
  const [score, setScore] = useState(0)

  const { data: questions = [], isSuccess } = useQuery({
    queryKey: ['trivia'],
    queryFn: () => getTrivia(8),
    staleTime: Infinity,
    retry: false,
  })

  useEffect(() => {
    if (isSuccess && questions.length === 0) onEmpty?.()
  }, [isSuccess, questions.length, onEmpty])

  // Mark as asked once, on arrival — not per answer, so a learner who
  // wanders off mid-round doesn't see the same questions next time.
  useEffect(() => {
    if (questions.length) markTriviaSeen(questions.map((q) => q.id)).catch(() => {})
  }, [questions])

  const q = questions[index]
  if (!q) return null

  const answered = picked !== null
  const correct = answered && picked === q.answer_index

  const next = () => {
    setPicked(null)
    setIndex((i) => (i + 1) % questions.length)
  }

  return (
    <div data-testid="trivia-game" className="w-full max-w-sm space-y-3 text-start">
      <p className="text-xs text-gray-500 text-center">
        {t('trailblazer.triviaHint')}
        {score > 0 && (
          <span className="ms-2 text-lang font-semibold">
            {t('trailblazer.triviaScore', { count: score })}
          </span>
        )}
      </p>
      <p className="text-sm font-semibold text-gray-900">{q.question}</p>
      <div className="space-y-2">
        {q.options.map((opt, i) => {
          const isAnswer = i === q.answer_index
          const chosen = picked === i
          return (
            <button
              key={i}
              type="button"
              disabled={answered}
              onClick={() => {
                setPicked(i)
                if (i === q.answer_index) setScore((n) => n + 1)
              }}
              className={`w-full rounded-lg border px-3 py-2 text-sm text-start transition-colors ${
                !answered
                  ? 'border-gray-200 bg-white text-gray-800 hover:border-lang/50'
                  : isAnswer
                    ? 'border-green-400 bg-green-50 text-green-800'
                    : chosen
                      ? 'border-red-300 bg-red-50 text-red-700'
                      : 'border-gray-200 bg-white text-gray-500'
              }`}
            >
              {opt}
            </button>
          )
        })}
      </div>
      {answered && (
        <div className="space-y-2" data-testid="trivia-fact">
          <p className="text-xs text-gray-600">
            <span className="font-semibold">
              {correct ? t('trailblazer.triviaRight') : t('trailblazer.triviaWrong')}
            </span>{' '}
            {q.fact}
          </p>
          <button
            type="button"
            onClick={next}
            className="text-sm text-lang hover:underline font-medium"
          >
            {t('trailblazer.triviaNext')}
          </button>
        </div>
      )}
    </div>
  )
}
