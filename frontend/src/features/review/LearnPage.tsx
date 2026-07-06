import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { confirmLearnSession, startLearnSession, validateAnswer } from '../../api/review'
import { getLanguages } from '../../api/profile'
import { usePrefsStore } from '../../stores/prefsStore'
import LanguageWrapper from '../../components/LanguageWrapper'
import SpeakButton from '../../components/SpeakButton'
import DrillCard from './DrillCard'
import type { Lesson, ValidateAnswerResponse } from '../../api/types'

/**
 * Teach-before-quiz: new items are PRESENTED here — meaning, explanation,
 * example sentences, references — before they ever appear as a review. The
 * learner pages through each new item, then starts the quiz.
 */
export default function LearnPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [searchParams] = useSearchParams()
  const cardType = searchParams.get('type') === 'grammar' ? 'grammar' : 'vocabulary'
  // Deck-scoped learning: /learn?type=grammar&level=A1 draws only from that
  // deck (and queues it if it wasn't queued yet).
  const level = searchParams.get('level') ?? undefined
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)
  const [lessonIndex, setLessonIndex] = useState(0)

  const { data: languages = [] } = useQuery({ queryKey: ['languages'], queryFn: getLanguages })
  const language = languages.find((l) => l.id === activeLanguageId)

  // The lesson batch is fetched as a one-shot QUERY, not a mutation fired
  // from an effect: the query cache dedupes StrictMode's double mount (one
  // request) and, unlike a mutation owned by a torn-down hook instance, the
  // result can't be lost — the page can no longer hang on the loading
  // screen while the request actually succeeded. The per-mount key means a
  // fresh visit fetches a fresh batch; Infinity stale/gc keeps this batch
  // stable for the lifetime of the walkthrough.
  const [sessionKey] = useState(() => `${Date.now()}-${Math.random()}`)
  const learnQuery = useQuery({
    queryKey: ['learn-session', sessionKey],
    queryFn: () => startLearnSession(activeLanguageId!, cardType, level),
    enabled: !!activeLanguageId,
    staleTime: Infinity,
    gcTime: Infinity,
    retry: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  })

  // Teach → check → queue: each lesson ends with a drill sentence, and only
  // a correct answer confirms THAT card into the review queue. Items never
  // checked stay suspended and are re-taught next time.
  const [passedCards, setPassedCards] = useState<Set<string>>(new Set())
  const [quizInput, setQuizInput] = useState('')
  const [quizResult, setQuizResult] = useState<ValidateAnswerResponse | null>(null)

  const validateMutation = useMutation({ mutationFn: validateAnswer })
  const confirmMutation = useMutation({
    mutationFn: (cardIds: string[]) => confirmLearnSession(cardIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['due-cards'] })
      queryClient.invalidateQueries({ queryKey: ['learn-decks'] })
    },
  })

  if (learnQuery.isError) {
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

  if (!learnQuery.isSuccess) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-500">Preparing your new items…</p>
      </div>
    )
  }

  const { added, lessons } = learnQuery.data

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
  // Advancing requires passing this lesson's check (when it has one).
  const currentPassed = !lesson?.quiz || passedCards.has(lesson.card_id)

  const goToLesson = (i: number) => {
    setLessonIndex(i)
    setQuizInput('')
    setQuizResult(null)
  }

  const handleCheck = () => {
    if (!lesson?.quiz || !quizInput.trim() || validateMutation.isPending) return
    validateMutation.mutate(
      {
        language_code: languageCode,
        user_input: quizInput.trim(),
        correct_answer: lesson.quiz.answer,
        card_context: {
          morphology: lesson.quiz.morphology ?? {},
          alternatives: lesson.quiz.alternatives ?? [],
        },
      },
      {
        onSuccess: (res) => {
          setQuizResult(res)
          if (
            res.answer_result === 'correct' ||
            res.answer_result === 'correct_sloppy'
          ) {
            setPassedCards((prev) => new Set(prev).add(lesson.card_id))
            // Correct first check — the card enters the review queue.
            confirmMutation.mutate([lesson.card_id])
          }
        },
      },
    )
  }

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

            {/* First check: answer one drill correctly to queue this item */}
            {lesson.quiz && (
              <div className="border-t border-gray-100 pt-4">
                <span className="text-xs uppercase tracking-wide text-gray-400 block mb-3">
                  Your turn
                </span>
                <DrillCard
                  sentence={lesson.quiz.sentence}
                  value={quizInput}
                  onChange={setQuizInput}
                  onSubmit={handleCheck}
                  disabled={currentPassed || validateMutation.isPending}
                  languageCode={languageCode}
                />
                {lesson.quiz.translation && (
                  <p className="text-xs text-gray-400 text-center mt-3">
                    {lesson.quiz.translation}
                  </p>
                )}
                {!currentPassed && (
                  <button
                    type="button"
                    onClick={handleCheck}
                    disabled={!quizInput.trim() || validateMutation.isPending}
                    className="mt-3 w-full bg-white hover:bg-gray-50 disabled:opacity-40 text-gray-500 hover:text-indigo-600 rounded-2xl border-2 border-gray-300 px-6 py-2 text-2xl leading-none transition-colors"
                    aria-label="Check answer"
                    style={{ minHeight: '44px' }}
                  >
                    {validateMutation.isPending ? '…' : '→'}
                  </button>
                )}
                {currentPassed && lesson.quiz && (
                  <p className="mt-3 text-sm text-green-700 text-center" role="status">
                    ✓ Correct — added to your reviews
                  </p>
                )}
                {!currentPassed &&
                  quizResult &&
                  quizResult.answer_result !== 'correct' &&
                  quizResult.answer_result !== 'correct_sloppy' && (
                    <p className="mt-3 text-sm text-red-600 text-center" role="alert">
                      Not quite — the material above has everything you need.
                      Try again!
                    </p>
                  )}
              </div>
            )}
          </div>
        )}

        <div className="flex items-center gap-3">
          {lessonIndex > 0 && (
            <button
              type="button"
              onClick={() => goToLesson(lessonIndex - 1)}
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
              disabled={!currentPassed}
              title={currentPassed ? undefined : 'Answer the sentence above first'}
              className="flex-1 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold rounded-xl px-6 py-3 text-sm"
              style={{ minHeight: '44px' }}
            >
              Start Reviewing
            </button>
          ) : (
            <button
              type="button"
              onClick={() => goToLesson(lessonIndex + 1)}
              disabled={!currentPassed}
              title={currentPassed ? undefined : 'Answer the sentence above first'}
              className="flex-1 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold rounded-xl px-6 py-3 text-sm"
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
