import { useState, useRef, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getCramCards, getDueCards, validateAnswer, submitReview } from '../../api/review'
import { getLanguages, getProfile, updateProfile } from '../../api/profile'
import type { DueCard } from '../../api/types'
import { usePrefsStore } from '../../stores/prefsStore'
import { useReviewSession } from './useReviewSession'
import DrillCard from './DrillCard'
import FeedbackPanel from './FeedbackPanel'
import ReviewDetail from './ReviewDetail'
import CardFeedback from './CardFeedback'
import SessionSummary from './SessionSummary'
import OnScreenKeyboard from '../keyboards/OnScreenKeyboard'
import { finalizeInput } from '../keyboards/translit'
import { hintLayersFor } from './hintLayers'
import SpeakButton from '../../components/SpeakButton'
import { TTS_LANGUAGES } from '../../api/audio'
import { hasKeyboardLayout } from '../keyboards/OnScreenKeyboard'
import type { KeyboardLanguage } from '../keyboards/OnScreenKeyboard'

/**
 * The review session — and, with `cram`, its ungraded twin (WP13f):
 * Quick-Cram drills a chosen set of grammar points (an item + its Related
 * set, `?points=id,id`) with the exact same answering flow, but nothing is
 * ever submitted — no FSRS update, no review log, no ghosts.
 */
export default function ReviewSessionPage({ cram = false }: { cram?: boolean }) {
  // Changing the translation language — or the ACTIVE language (beta bug:
  // a session started in English kept serving English cards under a
  // "Swahili" label) — restarts the session with fresh cards. The key
  // remount resets every piece of session state (index, results, requeue)
  // in one move.
  const [epoch, setEpoch] = useState(0)
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)
  return (
    <ReviewSessionInner
      key={`${activeLanguageId ?? 'none'}:${epoch}`}
      cram={cram}
      onLocaleChanged={() => setEpoch((e) => e + 1)}
    />
  )
}

function ReviewSessionInner({
  cram,
  onLocaleChanged,
}: {
  cram: boolean
  onLocaleChanged: () => void
}) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [searchParams] = useSearchParams()
  const cramPoints = cram ? (searchParams.get('points') ?? '') : ''
  // Grammar Only / Vocab Only sessions (dashboard Review tile expansion).
  const typeParam = searchParams.get('type')
  const reviewType =
    typeParam === 'grammar' || typeParam === 'vocabulary' ? typeParam : undefined
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)
  const [userInput, setUserInput] = useState('')
  const [lastInput, setLastInput] = useState('')
  const [showKeyboard, setShowKeyboard] = useState(true)
  const [saveErrorCount, setSaveErrorCount] = useState(0)
  // Graduated hint disclosure (Bunpro-style dots): 0 = nothing revealed.
  // Persisted in prefs — the level chosen last time stays chosen, across
  // cards and across sessions, until the learner changes it.
  const hintLevel = usePrefsStore((s) => s.hintLevel)
  const setHintLevel = usePrefsStore((s) => s.setHintLevel)
  const listeningMode = usePrefsStore((s) => s.listeningMode)
  const setListeningMode = usePrefsStore((s) => s.setListeningMode)
  const inputRef = useRef<HTMLInputElement>(null)

  const sessionSize = usePrefsStore((s) => s.sessionSize)
  // Fetched unconditionally (cheap, usually pre-cached) so the support
  // locale is part of the due-cards key BEFORE cards load — changing the
  // "learning English from" language then genuinely re-keys and refetches
  // the localized cards, instead of racing an invalidate + remount.
  const { data: profile } = useQuery({ queryKey: ['profile'], queryFn: getProfile })
  const supportLocale = profile?.support_locale ?? 'en'
  const { data: fetched, isLoading } = useQuery(
    cram
      ? {
          queryKey: ['cram-cards', cramPoints],
          queryFn: () => getCramCards(cramPoints.split(',')),
          enabled: cramPoints.length > 0,
          staleTime: Infinity, // one fetch per cram session — no mid-session reshuffle
          gcTime: 0,
          refetchOnWindowFocus: false,
        }
      : {
          queryKey: ['due-cards', activeLanguageId, sessionSize, reviewType ?? 'all', supportLocale],
          queryFn: () => getDueCards(activeLanguageId!, sessionSize, reviewType),
          enabled: !!activeLanguageId,
          // A live session must never see its deck change under it, and a
          // NEW session must never flash the previous one's cached cards:
          // fetch fresh on mount, then freeze.
          gcTime: 0,
          staleTime: Infinity,
          refetchOnWindowFocus: false,
        },
  )

  // Snapshot the deck at session start — refetches and cache invalidations
  // (tab focus, summary cleanup) can't make cards appear/disappear mid-run.
  const [cards, setCards] = useState<DueCard[] | null>(null)
  useEffect(() => {
    if (fetched && cards === null) setCards(fetched)
  }, [fetched, cards])

  const session = useReviewSession(cards ?? [])

  const qwertyTranslit = usePrefsStore((s) => s.qwertyTranslit)

  // English cards render definitions/translations in the learner's support
  // locale — let them switch it right here instead of trekking to Settings.
  // Saving restarts the session (key remount) with re-localized cards.
  const studyingEnglish = (cards?.[0]?.language_code ?? '') === 'en'
  const { data: languages = [] } = useQuery({
    queryKey: ['languages'],
    queryFn: getLanguages,
    enabled: studyingEnglish,
  })
  const localeMutation = useMutation({
    mutationFn: (support_locale: string) => updateProfile({ support_locale }),
    onSuccess: async () => {
      // Await the profile refetch so the new supportLocale is in place, then
      // remount — the remounted session re-keys the due-cards query on the
      // fresh locale and pulls re-localized cards.
      await queryClient.invalidateQueries({ queryKey: ['profile'] })
      onLocaleChanged()
    },
  })

  const validateMutation = useMutation({
    mutationFn: validateAnswer,
    onSuccess: (result, variables) => {
      setLastInput(variables.user_input)
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

    // Resolve anything the QWERTY transliteration left pending (e.g. an
    // Arabic trailing vowel) before grading.
    const finalInput = finalizeInput(
      card.language_code, userInput.trim(), qwertyTranslit,
    )
    if (finalInput !== userInput) setUserInput(finalInput)

    validateMutation.mutate({
      language_code: card.language_code,
      user_input: finalInput,
      correct_answer: card.correct_answer,
      card_context: {
        card_type: card.card_type,
        morphology: card.morphology ?? {},
        alternatives: card.alternatives ?? [],
      },
    })
  }

  const handleRate = (answerResult: string) => {
    const card = session.currentCard
    if (!card || submitMutation.isPending) return

    // Cram is practice, not review: nothing is submitted, so the FSRS
    // schedule and review log stay exactly as they were.
    if (!cram) {
      submitMutation.mutate({
        card_id: card.id,
        answer_result: answerResult,
        time_taken_ms: session.elapsedMs(),
        // sentences change per appearance — log which one was actually shown
        prompt_sentence: card.sentence,
      })
    }

    // The hint level intentionally carries over to the next card (persisted
    // preference) — no reset here.
    session.rate(answerResult)
  }

  // Enter advances after grading: the input is disabled during feedback, so
  // a document-level listener carries the keyboard flow forward — answer with
  // Enter, continue with Enter, never touch the mouse.
  useEffect(() => {
    if (session.phase !== 'feedback' && session.phase !== 'rating') return
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Enter' || submitMutation.isPending) return
      const result = session.validationResult?.answer_result
      if (result) {
        e.preventDefault()
        handleRate(result)
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session.phase, session.validationResult, submitMutation.isPending])

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

  const handleKeyboardBackspace = () => {
    const input = inputRef.current
    if (!input) {
      setUserInput((prev) => prev.slice(0, -1))
      return
    }
    const start = input.selectionStart ?? input.value.length
    const end = input.selectionEnd ?? input.value.length
    // Delete the selection, or the character before the caret.
    const from = start === end ? Math.max(0, start - 1) : start
    setUserInput(input.value.slice(0, from) + input.value.slice(end))
    requestAnimationFrame(() => {
      input.focus()
      input.setSelectionRange(from, from)
    })
  }

  if (isLoading || cards === null) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-500">Loading cards…</p>
      </div>
    )
  }

  if (cards.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="text-center space-y-4">
          <p className="text-xl text-gray-700">
            {cram
              ? 'Nothing to cram here yet — these points have no drills.'
              : 'No cards due! Come back later.'}
          </p>
          <button
            type="button"
            onClick={() => navigate('/')}
            className="text-lang hover:underline text-sm touch-manipulation"
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
          note={cram ? 'Practice only — nothing was recorded.' : undefined}
          onFinish={() => {
            if (!cram) {
              // The session changed due counts and deck progress — drop the
              // cached dashboard state so it's fresh on arrival, not after a
              // manual reload.
              queryClient.invalidateQueries({ queryKey: ['dashboard'] })
              queryClient.invalidateQueries({ queryKey: ['due-cards'] })
              queryClient.invalidateQueries({ queryKey: ['learn-decks'] })
            }
            navigate('/')
          }}
        />
      </div>
    )
  }

  const card = session.currentCard
  if (!card) return null

  // Language-aware hint layers (see hintLayers.ts): romanization first for
  // non-Latin scripts, word-by-word gloss first for unfamiliar-syntax
  // languages, translation before the morphology recipe everywhere — the
  // recipe stays last because it all but spells out the answer.
  const layers = hintLayersFor(card.language_code, card)
  const maxHint = layers.length
  const revealedLayers =
    session.phase !== 'answering' ? layers : layers.slice(0, Math.min(hintLevel, maxHint))
  const topHint = revealedLayers.find((l) => l.field === 'hint')
  const answering = session.phase === 'answering'
  const result = session.validationResult?.answer_result
  const resultStyles =
    result === 'correct'
      ? 'border-green-400 text-green-700'
      : result === 'correct_sloppy'
        ? 'border-amber-400 text-amber-700'
        : 'border-red-400 text-red-600'
  const completedSentence = card.sentence.includes('{{answer}}')
    ? card.sentence.replace('{{answer}}', card.correct_answer)
    : card.correct_answer

  // Listening mode (WP19a): only for cloze cards in languages with a real
  // neural voice — hearing the full sentence and typing the missing word.
  const canListen =
    card.sentence.includes('{{answer}}') && TTS_LANGUAGES.has(card.language_code)
  const listening = listeningMode && canListen

  // Listening mode (beta feedback, round 2): the answering-phase audio
  // speaks the sentence with the blank as a PAUSE — never the answer — so
  // the ear hears exactly where the missing word goes (before, users heard
  // the full sentence and couldn't tell which word to type). The full
  // sentence still plays after grading. The drill's authored hint stays
  // revealed as the cue; transliteration/gloss layers would spell the whole
  // sentence out, so those stay hidden until grading.
  const gappedSentence = card.sentence.split('{{answer}}').join('…')
  const listeningCue =
    listening && answering ? layers.find((l) => l.field === 'hint') : undefined
  const shownTopHint = topHint ?? listeningCue
  const belowLayers = revealedLayers.filter(
    (l) =>
      l.field !== 'hint' &&
      !(listening && answering &&
        (l.field === 'transliteration' || l.field === 'gloss')),
  )

  // Non-Latin scripts and Latin languages with accents/diacritics get an
  // on-screen helper. (Xhosa/English omitted: plain ASCII.)
  // Single source of truth with the component's layout map — pt/ro/el were
  // missing here AND from the layouts, so Portuguese learners either had no
  // accent row or (via the old fallback) a Russian keyboard.
  const needsKeyboard = hasKeyboardLayout(card.language_code)

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
        {/* Session utility bar (Bunpro-style: exit, path, tutor, settings) */}
        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={() => navigate('/')}
            aria-label="Exit session"
            className="text-xl leading-none text-gray-400 hover:text-lang"
          >
            ←
          </button>
          <div className="flex items-center gap-4 text-sm text-gray-400">
            <button type="button" onClick={() => navigate('/grammar')} className="hover:text-lang">
              Path
            </button>
            <button type="button" onClick={() => navigate('/tutor')} className="hover:text-lang">
              Tutor
            </button>
            <button type="button" onClick={() => navigate('/account')} aria-label="Account" className="hover:text-lang">
              ⚙
            </button>
          </div>
        </div>

        {/* Progress */}
        <div className="flex items-center justify-between text-sm text-gray-500">
          <span>
            Card {session.currentIndex + 1} of {cards.length}
          </span>
          {cram ? (
            <span className="text-xs rounded-full px-2 py-0.5 bg-lang-soft text-lang font-semibold">
              Quick Cram · not recorded
            </span>
          ) : (
            <span className="flex items-center gap-2">
              {studyingEnglish && (
                <select
                  value={profile?.support_locale ?? 'en'}
                  onChange={(e) => localeMutation.mutate(e.target.value)}
                  disabled={localeMutation.isPending}
                  aria-label="Translations language"
                  title="Show definitions and translations in…"
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
              <span className="capitalize">{card.card_type}</span>
            </span>
          )}
        </div>

        {/* Progress bar */}
        <div className="w-full bg-gray-200 rounded-full h-1.5">
          <div
            className="bg-lang h-1.5 rounded-full transition-all"
            style={{ width: `${((session.currentIndex) / cards.length) * 100}%` }}
          />
        </div>

        {/* Card area */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 md:p-8">
          {shownTopHint && (
            <p className="text-sm text-gray-400 text-center mb-4">
              {shownTopHint.text}
            </p>
          )}

          {listening && session.phase === 'answering' && (
            <div
              className="flex justify-center mb-4"
              data-testid="listening-player"
            >
              <SpeakButton
                text={gappedSentence}
                languageCode={card.language_code}
                label="Play the sentence"
                className="inline-flex items-center justify-center rounded-full border-2 border-lang/40 text-lang hover:bg-lang-soft p-4"
              />
            </div>
          )}

          <DrillCard
            key={card.id}
            sentence={card.sentence}
            value={session.phase === 'answering' ? userInput : lastInput}
            onChange={setUserInput}
            onSubmit={handleSubmitAnswer}
            disabled={session.phase !== 'answering' || validateMutation.isPending}
            languageCode={card.language_code}
            inputRef={inputRef}
            result={session.phase !== 'answering' ? result : null}
            hideSentence={listening && session.phase === 'answering'}
          />

          {belowLayers.length > 0 && (
            <div className="mt-4 space-y-1 text-center">
              {belowLayers.map((l) => (
                <p
                  key={l.field}
                  className={
                    l.field === 'transliteration'
                      ? 'text-sm italic text-gray-500'
                      : 'text-xs text-gray-400'
                  }
                >
                  <span className="text-[10px] uppercase tracking-wide text-gray-300 mr-2">
                    {l.label}
                  </span>
                  {l.text}
                </p>
              ))}
            </div>
          )}
        </div>

        {/* Answer bar (answering phase): just the arrow, Bunpro-style */}
        {session.phase === 'answering' && (
          <div className="space-y-2">
            <button
              type="button"
              aria-label="Submit answer"
              onClick={handleSubmitAnswer}
              disabled={!userInput.trim() || validateMutation.isPending}
              className="w-full bg-white hover:bg-gray-50 disabled:opacity-40 text-gray-500 hover:text-lang rounded-2xl border-2 border-gray-300 px-6 py-2 text-2xl leading-none transition-colors touch-manipulation"
              style={{ minHeight: '44px' }}
            >
              {validateMutation.isPending ? '…' : '→'}
            </button>
            {maxHint > 0 && (
              <button
                type="button"
                aria-label="Show a hint"
                onClick={() => setHintLevel(hintLevel >= maxHint ? 0 : hintLevel + 1)}
                className="flex items-center gap-2 text-sm text-gray-400 hover:text-lang"
              >
                Hint
                {Array.from({ length: maxHint }).map((_, i) => (
                  <span
                    key={i}
                    className={`inline-block w-2 h-2 rounded-full ${
                      i < hintLevel ? 'bg-lang' : 'bg-gray-300'
                    }`}
                  />
                ))}
              </button>
            )}
            {canListen && (
              <button
                type="button"
                aria-pressed={listening}
                onClick={() => setListeningMode(!listeningMode)}
                title="Hide the sentence and fill the blank by ear"
                className={`ml-auto text-sm rounded-full px-3 py-1 border transition ${
                  listening
                    ? 'border-lang/40 bg-lang-soft text-lang'
                    : 'border-gray-200 text-gray-400 hover:text-lang'
                }`}
              >
                🎧 Listening {listening ? 'on' : 'off'}
              </button>
            )}
          </div>
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
                onEnter={handleSubmitAnswer}
                onBackspace={handleKeyboardBackspace}
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
              {/* Cram cards have no user_card behind them — no detail page,
                  no per-card feedback, nothing to record. */}
              {!cram && (
                <ReviewDetail
                  cardId={card.id}
                  cardType={card.card_type}
                  languageCode={card.language_code}
                  stats={{
                    repetitions: card.repetitions,
                    streak: card.streak,
                    lapses: card.lapses,
                    next_review: card.next_review,
                  }}
                />
              )}
              {/* The answer was already graded by the NLP check; auto-record
                  that grade (it drives FSRS scheduling + the tutor's weak-area
                  analysis) and just let the learner continue, with a manual
                  override for a lucky-correct answer. */}
              <div className="space-y-2">
                {/* Result pill: audio, the answer, and the arrow to continue.
                    The grade was already decided by the NLP check. */}
                <div
                  className={`flex items-center gap-2 bg-white rounded-2xl border-2 px-3 py-1.5 shadow-sm ${resultStyles}`}
                >
                  <SpeakButton text={completedSentence} languageCode={card.language_code} />
                  <span className="flex-1 text-center font-semibold">
                    {card.correct_answer}
                  </span>
                  <button
                    type="button"
                    aria-label="Continue"
                    onClick={() => handleRate(session.validationResult!.answer_result)}
                    disabled={submitMutation.isPending}
                    className="text-2xl leading-none px-2 text-gray-500 hover:text-lang disabled:opacity-50"
                    style={{ minHeight: '44px' }}
                  >
                    →
                  </button>
                </div>
                <div className="flex items-center justify-center gap-6">
                  {/* Bunpro-style undo: retype without recording a grade. */}
                  <button
                    type="button"
                    onClick={() => {
                      setUserInput(lastInput)
                      session.retry()
                    }}
                    className="text-xs text-gray-400 hover:text-lang"
                  >
                    ↺ Undo
                  </button>
                  {(session.validationResult.answer_result === 'correct' ||
                    session.validationResult.answer_result === 'correct_sloppy') && (
                    <button
                      type="button"
                      onClick={() => handleRate('wrong')}
                      disabled={submitMutation.isPending}
                      className="text-xs text-gray-400 hover:text-red-500"
                    >
                      I actually got it wrong
                    </button>
                  )}
                </div>
              </div>
              {!cram && (
                <div className="text-center">
                  <CardFeedback cardId={card.id} />
                </div>
              )}
            </div>
          )}
      </div>
    </div>
  )
}
