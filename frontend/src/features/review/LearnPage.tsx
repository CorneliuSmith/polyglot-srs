import { useState, useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { confirmLearnSession, startLearnSession, validateAnswer } from '../../api/review'
import { getLanguages, getProfile, updateProfile } from '../../api/profile'
import { usePrefsStore } from '../../stores/prefsStore'
import LanguageWrapper from '../../components/LanguageWrapper'
import FormsPanel from '../../components/FormsPanel'
import ExplanationView from '../../components/ExplanationView'
import SpeakButton from '../../components/SpeakButton'
import DrillCard from './DrillCard'
import OnScreenKeyboard, { hasKeyboardLayout } from '../keyboards/OnScreenKeyboard'
import type { KeyboardLanguage } from '../keyboards/OnScreenKeyboard'
import { finalizeInput } from '../keyboards/translit'
import type { Lesson, ValidateAnswerResponse } from '../../api/types'

/**
 * Teach-before-quiz: new items are PRESENTED here — meaning, explanation,
 * example sentences, references — before they ever appear as a review. The
 * learner pages through each new item, then starts the quiz.
 */
export default function LearnPage() {
  // Switching the translation language mid-walkthrough remounts the page
  // (key epoch): unconfirmed lessons are suspended by design and re-taught
  // by the fresh batch — now localized in the new language.
  const [epoch, setEpoch] = useState(0)
  return <LearnInner key={epoch} onLocaleChanged={() => setEpoch((e) => e + 1)} />
}

function LearnInner({ onLocaleChanged }: { onLocaleChanged: () => void }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [searchParams] = useSearchParams()
  const cardType = searchParams.get('type') === 'grammar' ? 'grammar' : 'vocabulary'
  // Deck-scoped learning: /learn?type=grammar&level=A1 draws only from that
  // deck (and queues it if it wasn't queued yet).
  const level = searchParams.get('level') ?? undefined
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)
  const qwertyTranslit = usePrefsStore((s) => s.qwertyTranslit)
  const [lessonIndex, setLessonIndex] = useState(0)

  const { data: languages = [] } = useQuery({ queryKey: ['languages'], queryFn: getLanguages })
  const language = languages.find((l) => l.id === activeLanguageId)

  // WP22: English lessons render definitions/hints/explanations in the
  // learner's support locale — switchable right here, like in reviews.
  const studyingEnglish = language?.code === 'en'
  const { data: profile } = useQuery({
    queryKey: ['profile'],
    queryFn: getProfile,
    enabled: studyingEnglish,
  })
  const localeMutation = useMutation({
    mutationFn: (support_locale: string) => updateProfile({ support_locale }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profile'] })
      onLocaleChanged()
    },
  })

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
  // Cards passed on the right word but with missing/wrong accents — shown
  // amber ("check the accents"), never a green ✓ (beta report: accentless
  // answers read as fully correct even with accents-optional OFF).
  const [sloppyCards, setSloppyCards] = useState<Set<string>>(new Set())
  // Cards answered WRONG at least once. A wrong answer unlocks "Next" too
  // (beta report: vocab lessons trapped you until you got it right, unlike
  // grammar reviews) — the card just stays unconfirmed, so it is re-taught
  // in the next Learn session instead of entering reviews.
  const [missedCards, setMissedCards] = useState<Set<string>>(new Set())
  const [quizInput, setQuizInput] = useState('')
  const [quizResult, setQuizResult] = useState<ValidateAnswerResponse | null>(null)
  // On-screen keyboard for non-Latin scripts (ru/ar/el/th) — same access the
  // review session has (beta report: alphabet languages had no keyboard while
  // learning). Types the target script straight into the answer.
  const inputRef = useRef<HTMLInputElement>(null)
  const [showKeyboard, setShowKeyboard] = useState(true)

  const typeIntoQuiz = (insert: string, replaceBackspace = false) => {
    setQuizResult(null)
    const input = inputRef.current
    if (!input) {
      setQuizInput((prev) =>
        replaceBackspace ? prev.slice(0, -1) : prev + insert,
      )
      return
    }
    const start = input.selectionStart ?? input.value.length
    const end = input.selectionEnd ?? input.value.length
    if (replaceBackspace) {
      const from = start === end ? Math.max(0, start - 1) : start
      setQuizInput(input.value.slice(0, from) + input.value.slice(end))
      requestAnimationFrame(() => {
        input.focus()
        input.setSelectionRange(from, from)
      })
      return
    }
    setQuizInput(input.value.slice(0, start) + insert + input.value.slice(end))
    requestAnimationFrame(() => {
      input.focus()
      input.setSelectionRange(start + insert.length, start + insert.length)
    })
  }

  const validateMutation = useMutation({ mutationFn: validateAnswer })
  const confirmMutation = useMutation({
    mutationFn: (cardIds: string[]) => confirmLearnSession(cardIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      queryClient.invalidateQueries({ queryKey: ['due-cards'] })
      queryClient.invalidateQueries({ queryKey: ['learn-decks'] })
    },
  })

  // Enter advances once the lesson's check is passed (or the lesson has no
  // check): the answer input is disabled at that point, so a document-level
  // listener keeps the keyboard flow going — answer with Enter, continue
  // with Enter. Mirrors ReviewSessionPage's post-grading listener. Sits
  // above the early returns because hooks must run on every render.
  useEffect(() => {
    const loadedLessons = learnQuery.data?.lessons ?? []
    const current = loadedLessons[lessonIndex]
    if (!current) return
    if (current.quiz && !passedCards.has(current.card_id)) return
    const last = lessonIndex >= loadedLessons.length - 1
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Enter' || e.isComposing) return
      e.preventDefault()
      if (last) {
        navigate('/review')
      } else {
        setLessonIndex(lessonIndex + 1)
        setQuizInput('')
        setQuizResult(null)
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [learnQuery.data, lessonIndex, passedCards])

  if (learnQuery.isError) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="text-center space-y-4">
          <p className="text-xl text-red-600">Failed to load new items.</p>
          <p className="text-sm text-gray-500">Please try again later.</p>
          <button
            type="button"
            onClick={() => navigate('/')}
            className="text-lang hover:underline text-sm"
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
            className="text-lang hover:underline text-sm"
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
  const currentSloppy = !!lesson?.quiz && sloppyCards.has(lesson.card_id)
  // Attempted-but-wrong also unlocks Next; the card stays unconfirmed.
  const currentAttempted =
    currentPassed || (!!lesson?.quiz && missedCards.has(lesson.card_id))

  const goToLesson = (i: number) => {
    setLessonIndex(i)
    setQuizInput('')
    setQuizResult(null)
  }

  const handleCheck = () => {
    if (!lesson?.quiz || !quizInput.trim() || validateMutation.isPending) return
    const finalInput = finalizeInput(languageCode, quizInput.trim(), qwertyTranslit)
    if (finalInput !== quizInput) setQuizInput(finalInput)
    validateMutation.mutate(
      {
        language_code: languageCode,
        user_input: finalInput,
        correct_answer: lesson.quiz.answer,
        card_context: {
          card_type: cardType,
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
            // Right word either way — the card enters the review queue.
            // But an accent-only miss ('correct_sloppy' survives the
            // accents-optional remap only when that pref is OFF) keeps its
            // amber "check the accents" treatment instead of a green ✓.
            if (res.answer_result === 'correct_sloppy') {
              setSloppyCards((prev) => new Set(prev).add(lesson.card_id))
            }
            setPassedCards((prev) => new Set(prev).add(lesson.card_id))
            confirmMutation.mutate([lesson.card_id])
          } else {
            setMissedCards((prev) => new Set(prev).add(lesson.card_id))
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
          <span className="flex items-center gap-3">
            {studyingEnglish && (
              <select
                value={profile?.support_locale ?? 'en'}
                onChange={(e) => localeMutation.mutate(e.target.value)}
                disabled={localeMutation.isPending}
                aria-label="Translations language"
                title="Show definitions and explanations in…"
                className="text-xs rounded-lg border border-gray-200 bg-white px-2 py-1 text-gray-600"
              >
                <option value="en">English</option>
                {languages
                  .filter((l) => l.code !== 'en')
                  .map((l) => (
                    <option key={l.code} value={l.code}>
                      {l.name}
                    </option>
                  ))}
              </select>
            )}
            <button
              type="button"
              onClick={() => navigate('/')}
              className="text-sm text-lang hover:underline"
            >
              ← Dashboard
            </button>
          </span>
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
                <ExplanationView text={lesson.explanation} />
              </div>
            )}

            {lesson.usage_note && (
              <p className="text-sm text-gray-600 whitespace-pre-wrap">{lesson.usage_note}</p>
            )}

            <FormsPanel morphology={lesson.morphology} languageCode={languageCode} />

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
              <div className="bg-lang-soft border border-lang/20 rounded-lg p-3">
                <span className="text-xs uppercase tracking-wide text-lang/70 block mb-1">
                  Culture note
                </span>
                <p className="text-sm text-lang-dark/80 whitespace-pre-wrap">
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
                        className="text-sm text-lang hover:underline"
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
                  key={lesson.card_id}
                  sentence={lesson.quiz.sentence}
                  value={quizInput}
                  onChange={(v) => {
                    setQuizInput(v)
                    if (quizResult) setQuizResult(null)
                  }}
                  onSubmit={handleCheck}
                  disabled={currentPassed || validateMutation.isPending}
                  languageCode={languageCode}
                  inputRef={inputRef}
                  result={
                    currentPassed
                      ? currentSloppy
                        ? 'correct_sloppy'
                        : 'correct'
                      : quizResult?.answer_result ?? null
                  }
                />
                {lesson.quiz.transliteration && (
                  <p className="text-sm italic text-gray-500 text-center mt-3">
                    {lesson.quiz.transliteration}
                  </p>
                )}
                {lesson.quiz.gloss && (
                  <p className="text-xs text-gray-400 text-center mt-1">
                    {lesson.quiz.gloss}
                  </p>
                )}
                {lesson.quiz.translation && (
                  <p className="text-xs text-gray-400 text-center mt-1">
                    {lesson.quiz.translation}
                  </p>
                )}
                {!currentPassed && (
                  <button
                    type="button"
                    onClick={handleCheck}
                    disabled={!quizInput.trim() || validateMutation.isPending}
                    className="mt-3 w-full bg-white hover:bg-gray-50 disabled:opacity-40 text-gray-500 hover:text-lang rounded-2xl border-2 border-gray-300 px-6 py-2 text-2xl leading-none transition-colors"
                    aria-label="Check answer"
                    style={{ minHeight: '44px' }}
                  >
                    {validateMutation.isPending ? '…' : '→'}
                  </button>
                )}

                {/* On-screen keyboard for non-Latin scripts, during answering */}
                {!currentPassed && hasKeyboardLayout(languageCode) && (
                  <div className="mt-3 space-y-2">
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
                        languageCode={languageCode as KeyboardLanguage}
                        onKeyPress={(key) => typeIntoQuiz(key)}
                        onEnter={handleCheck}
                        onBackspace={() => typeIntoQuiz('', true)}
                        inputRef={inputRef}
                      />
                    )}
                  </div>
                )}
                {currentPassed && lesson.quiz && !currentSloppy && (
                  <p className="mt-3 text-sm text-green-700 text-center" role="status">
                    ✓ Correct — added to your reviews
                  </p>
                )}
                {currentPassed && lesson.quiz && currentSloppy && (
                  <p className="mt-3 text-sm text-amber-700 text-center" role="status">
                    Almost — check the accents: <b>{lesson.quiz.answer}</b>.
                    Added to your reviews.
                  </p>
                )}
                {!currentPassed &&
                  quizResult &&
                  quizResult.answer_result !== 'correct' &&
                  quizResult.answer_result !== 'correct_sloppy' && (
                    <p className="mt-3 text-sm text-red-600 text-center" role="alert">
                      Not quite — the answer is <b>{lesson.quiz.answer}</b>.
                      Try again, or move on and this one will be re-taught
                      next time.
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
              disabled={!currentAttempted}
              title={currentAttempted ? undefined : 'Try the sentence above first'}
              className="flex-1 bg-lang hover:bg-lang-dark disabled:opacity-50 text-lang-on font-semibold rounded-xl px-6 py-3 text-sm"
              style={{ minHeight: '44px' }}
            >
              Start Reviewing
            </button>
          ) : (
            <button
              type="button"
              onClick={() => goToLesson(lessonIndex + 1)}
              disabled={!currentAttempted}
              title={currentAttempted ? undefined : 'Try the sentence above first'}
              className="flex-1 bg-lang hover:bg-lang-dark disabled:opacity-50 text-lang-on font-semibold rounded-xl px-6 py-3 text-sm"
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
