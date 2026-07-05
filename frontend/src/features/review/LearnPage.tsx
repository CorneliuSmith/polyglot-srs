import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { startLearnSession } from '../../api/review'
import { getLanguages } from '../../api/profile'
import { usePrefsStore } from '../../stores/prefsStore'
import LanguageWrapper from '../../components/LanguageWrapper'
import SpeakButton from '../../components/SpeakButton'
import type { Lesson } from '../../api/types'

/**
 * Teach-before-quiz: new items are PRESENTED here — meaning, explanation,
 * example sentences, references — before they ever appear as a review. The
 * learner pages through each new item, then starts the quiz.
 */
export default function LearnPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const cardType = searchParams.get('type') === 'grammar' ? 'grammar' : 'vocabulary'
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)
  const [lessonIndex, setLessonIndex] = useState(0)

  const { data: languages = [] } = useQuery({ queryKey: ['languages'], queryFn: getLanguages })
  const language = languages.find((l) => l.id === activeLanguageId)

  const learnMutation = useMutation({
    mutationFn: () => startLearnSession(activeLanguageId!, cardType),
  })

  // Guard against firing twice (React 18 StrictMode remounts effects in dev) —
  // a duplicate call would learn a second batch of items.
  const started = useRef(false)
  useEffect(() => {
    if (activeLanguageId && !started.current) {
      started.current = true
      learnMutation.mutate()
    }
    // Run once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (learnMutation.isError) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="text-center space-y-4">
          <p className="text-xl text-red-600">Failed to load new items.</p>
          <p className="text-sm text-gray-500">Please try again later.</p>
          <button
            type="button"
            onClick={() => navigate('/')}
            className="text-indigo-600 hover:underline text-sm"
          >
            ← Back to Dashboard
          </button>
        </div>
      </div>
    )
  }

  if (!learnMutation.isSuccess) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-500">Preparing your new items…</p>
      </div>
    )
  }

  const { added, lessons } = learnMutation.data

  if (added === 0) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="text-center space-y-4">
          <p className="text-xl text-gray-700">Nothing new to learn right now.</p>
          <p className="text-sm text-gray-500">
            You've started everything available at your level — review what's due,
            or raise your level in Settings.
          </p>
          <button
            type="button"
            onClick={() => navigate('/')}
            className="text-indigo-600 hover:underline text-sm"
          >
            ← Back to Dashboard
          </button>
        </div>
      </div>
    )
  }

  const lesson: Lesson | undefined = lessons[lessonIndex]
  const isLast = lessonIndex >= lessons.length - 1
  const languageCode = language?.code ?? 'en'

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-xl mx-auto px-4 py-8 space-y-4">
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-500">
            New {cardType === 'grammar' ? 'grammar' : 'vocabulary'} ·{' '}
            {lessonIndex + 1} of {lessons.length}
          </p>
          <button
            type="button"
            onClick={() => navigate('/')}
            className="text-sm text-indigo-600 hover:underline"
          >
            ← Dashboard
          </button>
        </div>

        {lesson && (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 space-y-4">
            <div className="flex items-start justify-between gap-2">
              <div>
                <LanguageWrapper languageCode={languageCode}>
                  <h1 className="text-2xl font-bold text-gray-900">{lesson.title}</h1>
                </LanguageWrapper>
                {lesson.reading && (
                  <p className="text-sm text-gray-500 mt-0.5">{lesson.reading}</p>
                )}
                {lesson.part_of_speech && (
                  <p className="text-xs text-gray-400 mt-0.5">{lesson.part_of_speech}</p>
                )}
              </div>
              {lesson.title && (
                <SpeakButton text={lesson.title} languageCode={languageCode} />
              )}
            </div>

            {lesson.definition && (
              <p className="text-gray-800">
                <span className="text-xs uppercase tracking-wide text-gray-400 block">
                  Meaning
                </span>
                {lesson.definition}
              </p>
            )}

            {lesson.explanation && (
              <div>
                <span className="text-xs uppercase tracking-wide text-gray-400 block mb-1">
                  How it works
                </span>
                <p className="text-gray-800 whitespace-pre-wrap">{lesson.explanation}</p>
              </div>
            )}

            {lesson.usage_note && (
              <p className="text-sm text-gray-600 whitespace-pre-wrap">{lesson.usage_note}</p>
            )}

            {lesson.examples.length > 0 && (
              <div>
                <span className="text-xs uppercase tracking-wide text-gray-400 block mb-1">
                  In context
                </span>
                <ul className="space-y-2">
                  {lesson.examples.map((ex, i) => (
                    <li key={i}>
                      <span className="flex items-start gap-1">
                        <LanguageWrapper languageCode={languageCode}>
                          <span className="text-gray-900">{ex.sentence}</span>
                        </LanguageWrapper>
                        <SpeakButton text={ex.sentence} languageCode={languageCode} />
                      </span>
                      {ex.translation && (
                        <span className="block text-sm text-gray-500">{ex.translation}</span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {lesson.culture_note && (
              <div className="bg-indigo-50 border border-indigo-100 rounded-lg p-3">
                <span className="text-xs uppercase tracking-wide text-indigo-400 block mb-1">
                  Culture note
                </span>
                <p className="text-sm text-indigo-900/80 whitespace-pre-wrap">
                  {lesson.culture_note}
                </p>
              </div>
            )}

            {lesson.references.length > 0 && (
              <div>
                <span className="text-xs uppercase tracking-wide text-gray-400 block mb-1">
                  Sources
                </span>
                <ul className="space-y-1">
                  {lesson.references.map((ref, i) => (
                    <li key={i}>
                      <a
                        href={ref.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-indigo-600 hover:underline"
                      >
                        {ref.title}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        <div className="flex items-center gap-3">
          {lessonIndex > 0 && (
            <button
              type="button"
              onClick={() => setLessonIndex((i) => i - 1)}
              className="rounded-xl border border-gray-300 bg-white px-5 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
              style={{ minHeight: '44px' }}
            >
              ← Previous
            </button>
          )}
          {isLast ? (
            <button
              type="button"
              onClick={() => navigate('/review')}
              className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl px-6 py-3 text-sm"
              style={{ minHeight: '44px' }}
            >
              Start Reviewing
            </button>
          ) : (
            <button
              type="button"
              onClick={() => setLessonIndex((i) => i + 1)}
              className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl px-6 py-3 text-sm"
              style={{ minHeight: '44px' }}
            >
              Next →
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
