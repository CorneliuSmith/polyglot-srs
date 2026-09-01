import { useState, useEffect, useRef, useCallback } from 'react'
import { Trans, useTranslation } from 'react-i18next'
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  confirmLearnSession,
  getSessionReadiness,
  markCardKnown,
  refreshLessons,
  startLearnSession,
  validateAnswer,
} from '../../api/review'
import { effectiveSupportLocale, getLanguages, getProfile } from '../../api/profile'
import { usePrefsStore } from '../../stores/prefsStore'
import { languageDisplayName } from '../../lib/languages'
import LanguageWrapper from '../../components/LanguageWrapper'
import InfoDot from '../../components/InfoDot'
import FormsPanel from '../../components/FormsPanel'
import ExplanationView from '../../components/ExplanationView'
import SpeakButton from '../../components/SpeakButton'
import DrillCard from './DrillCard'
import TrailblazerWait from './TrailblazerWait'
import SuggestChange from '../contribute/SuggestChange'
import Annotatable from '../contribute/Annotatable'
import { prefetchTTSMany } from '../../api/audio'
import OnScreenKeyboard, { hasKeyboardLayout } from '../keyboards/OnScreenKeyboard'
import type { KeyboardLanguage } from '../keyboards/OnScreenKeyboard'
import { composeScript, deleteLastUnit, finalizeInput } from '../keyboards/translit'
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
  // Watched at the profile, not just at this page's own picker: the globe in
  // the header changes the same setting, and a walkthrough already holding
  // its lessons in state kept showing the old language until the page was
  // left and re-entered. See the same guard in ReviewSessionPage.
  const { data: localeProfile } = useQuery({
    queryKey: ['profile'],
    queryFn: getProfile,
  })
  // The EFFECTIVE locale — explicit choice or, automatically, the
  // interface language — so a globe tap moves this too, not only an edit
  // in Settings. Watching the raw column missed the automatic case.
  const supportLocale = localeProfile
    ? effectiveSupportLocale(localeProfile)
    : null
  const seenLocale = useRef<string | null>(null)
  useEffect(() => {
    if (supportLocale == null) return
    if (seenLocale.current !== null && seenLocale.current !== supportLocale) {
      setEpoch((e) => e + 1)
    }
    seenLocale.current = supportLocale
  }, [supportLocale])
  // Both halves of the identity in the key, exactly like ReviewSessionPage:
  // the locale epoch alone left a course switch that arrives WITHOUT a
  // remount — the profile→prefs sync, a second tab's persisted store — still
  // showing the old course's lessons, because the batch key is a
  // mount-scoped random and never refetches on its own.
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)
  return <LearnInner key={`${activeLanguageId ?? 'none'}:${epoch}`} />
}

function LearnInner() {
  // The account's gloss setting (user_profiles.show_glosses). Absent reads
  // as ON, same as everywhere else: the layer is the default and the
  // toggle is the escape, so a deploy ahead of migration 20261012 keeps
  // showing what learners have today.
  const { data: glossProfile } = useQuery({
    queryKey: ['profile'],
    queryFn: getProfile,
  })
  const showGlosses = glossProfile?.show_glosses ?? true
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()
  const queryClient = useQueryClient()
  const [searchParams] = useSearchParams()
  // 'both' interleaves grammar + vocabulary in one session; each lesson then
  // carries its OWN type (lesson.card_type) for the label and answer grading.
  const typeParam = searchParams.get('type')
  const cardType =
    typeParam === 'grammar' ? 'grammar' : typeParam === 'both' ? 'both' : 'vocabulary'
  // Deck-scoped learning: /learn?type=grammar&level=A1 draws only from that
  // deck (and queues it if it wasn't queued yet).
  const level = searchParams.get('level') ?? undefined
  // Topic Lens scope — the server treats an unknown slug as unscoped, so
  // a stale link still learns.
  const topic = searchParams.get('topic') ?? undefined
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)
  const qwertyTranslit = usePrefsStore((s) => s.qwertyTranslit)
  const showTashkeel = usePrefsStore((s) => s.showTashkeel)
  const [lessonIndex, setLessonIndex] = useState(0)

  // Start each lesson at the top (owner: "when a user goes to the next
  // lesson card it should start at the top of the page so they can read
  // the lesson easily").
  //
  // Keyed on the INDEX rather than hung off the Next button, because there
  // are two ways forward — the button and the document-level Enter handler
  // — and a third would forget. Instant, not smooth: this is a page turn,
  // and animating a scroll from the bottom of a long grammar explanation
  // is a second of nothing happening.
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' as ScrollBehavior })
  }, [lessonIndex])

  const { data: languages = [] } = useQuery({ queryKey: ['languages'], queryFn: getLanguages })
  const language = languages.find((l) => l.id === activeLanguageId)

  // EVERY course renders definitions/hints/explanations in the learner's
  // support locale (cards.py _effective_locale), so the switch belongs on
  // every course too. It used to be gated on `language?.code === 'en'`,
  // which left an English speaker studying Spanish looking at Arabic
  // translations with the only off-switch hidden — and this query disabled,
  // so the options never loaded either.

  // The lesson batch is fetched as a one-shot QUERY, not a mutation fired
  // from an effect: the query cache dedupes StrictMode's double mount (one
  // request) and, unlike a mutation owned by a torn-down hook instance, the
  // result can't be lost — the page can no longer hang on the loading
  // screen while the request actually succeeded. The per-mount key means a
  // fresh visit fetches a fresh batch; Infinity stale/gc keeps this batch
  // stable for the lifetime of the walkthrough.
  // Trailblazer gate: a session whose content hasn't been written in the
  // learner's language yet is worth waiting a moment for — but never
  // forced. Readiness is checked BEFORE the batch is drawn (the learn POST
  // creates cards), and checking is itself what primes the queue server
  // side. A failed check means "just start": the wait must never be what
  // blocks a session.
  const [startNow, setStartNow] = useState(false)
  const readinessQuery = useQuery({
    queryKey: ['session-readiness', activeLanguageId, 'learn', undefined],
    queryFn: () => getSessionReadiness(activeLanguageId!),
    enabled: !!activeLanguageId,
    retry: 1,
  })
  const readinessSettled = readinessQuery.isSuccess || readinessQuery.isError
  const underReady =
    readinessQuery.data != null && !readinessQuery.data.learn.ready_enough
  const gated = underReady && !startNow
  const handleStart = useCallback(() => setStartNow(true), [])

  const [sessionKey] = useState(() => `${Date.now()}-${Math.random()}`)
  const learnQuery = useQuery({
    queryKey: ['learn-session', sessionKey],
    queryFn: () => startLearnSession(activeLanguageId!, cardType, level, topic),
    enabled: !!activeLanguageId && readinessSettled && !gated,
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
  // "I already know this" (owner): retires the card via the same
  // mark-as-known endpoint Review uses, instead of forcing the drill.
  // mark_card_known floors repetitions at 1 while leaving is_suspended
  // true, which is exactly what exits it from the teach-gate bucket
  // (is_suspended AND repetitions = 0) without ever confirming it into
  // active reviews — a permanent skip, not a pass.
  const [knownCards, setKnownCards] = useState<Set<string>>(new Set())
  const [quizInput, setQuizInput] = useState('')
  const [quizResult, setQuizResult] = useState<ValidateAnswerResponse | null>(null)
  // First miss on a card: don't reveal the answer — everything needed to get
  // it right is in the examples ABOVE the quiz, so a fading nudge invites a
  // retry instead (owner, 2026-07-27). A second miss reveals as before, so
  // nobody is ever stuck. (Hooks live up here, before the early returns.)
  const [wrongTries, setWrongTries] = useState(0)
  const [retryToast, setRetryToast] = useState(false)
  const retryTimer = useRef<number | null>(null)
  useEffect(
    () => () => {
      if (retryTimer.current) window.clearTimeout(retryTimer.current)
    },
    [],
  )
  // On-screen keyboard for non-Latin scripts (ru/ar/el/th/hi/ko) — same access the
  // review session has (beta report: alphabet languages had no keyboard while
  // learning). Types the target script straight into the answer.
  const inputRef = useRef<HTMLInputElement>(null)
  const [showKeyboard, setShowKeyboard] = useState(true)

  // Warm this card's audio as soon as it appears: the word itself first,
  // then its examples, so the speaker plays instead of waiting on a synth
  // round trip. Placed with the other hooks and ABOVE the loading/error
  // early returns — a hook after a conditional return changes hook order
  // between renders and React tears the component down.
  const prefetchLesson = learnQuery.data?.lessons?.[lessonIndex]
  const prefetchCode = language?.code
  useEffect(() => {
    if (!prefetchLesson || !prefetchCode) return
    // `?? []`: a lesson with no examples is legitimate (a bare vocabulary
    // card), and prefetching must never be what takes the page down.
    return prefetchTTSMany(
      prefetchCode,
      [
        prefetchLesson.title,
        ...(prefetchLesson.examples ?? []).map((e) => e.sentence),
      ].filter((t): t is string => !!t),
    )
  }, [prefetchLesson, prefetchCode])

  // Live swap: re-serve the lesson payloads on every advance while ANY of
  // this session still reads in English, so content landing mid-session
  // renders without a restart. Keyed on "not fully localized" rather than
  // on the 60% start threshold — a session can clear that bar with its
  // glosses done and every example sentence still English, and those are
  // most of what a vocabulary card actually shows. Best-effort: a failed
  // refresh just leaves the English already on screen.
  const notFullyLocalized =
    readinessQuery.data != null && readinessQuery.data.learn.pct < 1
  const [swapped, setSwapped] = useState<Record<string, Lesson>>({})
  const sessionItems = learnQuery.data?.items
  useEffect(() => {
    if (!notFullyLocalized || !sessionItems?.length) return
    let cancelled = false
    refreshLessons(sessionItems)
      .then((fresh) => {
        if (cancelled) return
        setSwapped(Object.fromEntries(fresh.map((l) => [l.card_id, l])))
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [notFullyLocalized, sessionItems, lessonIndex])

  const typeIntoQuiz = (insert: string, replaceBackspace = false) => {
    setQuizResult(null)
    const input = inputRef.current
    if (!input) {
      setQuizInput((prev) =>
        replaceBackspace
          ? deleteLastUnit(languageCode, prev)
          : composeScript(languageCode, prev + insert),
      )
      return
    }
    const start = input.selectionStart ?? input.value.length
    const end = input.selectionEnd ?? input.value.length
    if (replaceBackspace) {
      // Delete the selection, or one UNIT before the caret — Hangul peels a
      // jamo off the syllable (한 → 하) rather than losing the whole block.
      const head =
        start === end
          ? deleteLastUnit(languageCode, input.value.slice(0, start))
          : input.value.slice(0, start)
      setQuizInput(head + input.value.slice(end))
      const caret = head.length
      requestAnimationFrame(() => {
        input.focus()
        input.setSelectionRange(caret, caret)
      })
      return
    }
    // Hangul jamo must fuse into syllable blocks; other scripts pass through.
    const composed = composeScript(languageCode, input.value.slice(0, start) + insert)
    setQuizInput(composed + input.value.slice(end))
    const caret = composed.length
    requestAnimationFrame(() => {
      input.focus()
      input.setSelectionRange(caret, caret)
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
  const knownMutation = useMutation({
    mutationFn: (cardId: string) => markCardKnown(cardId),
    onSuccess: (_data, cardId) => {
      setKnownCards((prev) => new Set(prev).add(cardId))
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
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
    if (
      current.quiz &&
      !passedCards.has(current.card_id) &&
      !knownCards.has(current.card_id)
    )
      return
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
  }, [learnQuery.data, lessonIndex, passedCards, knownCards])

  if (gated && activeLanguageId) {
    return (
      <TrailblazerWait
        languageId={activeLanguageId}
        kind="learn"
        onStart={handleStart}
        onExit={() => navigate('/')}
        localeName={(() => {
          // The DB name is English ("Spanish"), which read as a foreign word
          // dropped into a Spanish sentence. Intl gives the endonym.
          const code = readinessQuery.data?.locale
          const row = languages.find((l) => l.code === code)
          return code && row
            ? languageDisplayName(code, row.name, i18n.language)
            : undefined
        })()}
      />
    )
  }

  if (learnQuery.isError) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="text-center space-y-4">
          <p className="text-xl text-red-600">{t('learnSession.loadFailed')}</p>
          <p className="text-sm text-gray-500">{t('learnSession.tryAgainLater')}</p>
          <button
            type="button"
            onClick={() => navigate('/')}
            className="text-lang hover:underline text-sm"
          >
            {t('common.backToDashboardLong')}
          </button>
        </div>
      </div>
    )
  }

  // No active language means no query will ever run: every hook above is
  // `enabled: !!activeLanguageId`, so without the redirect this page sits
  // on "preparing…" forever with nothing to press. Reached by a direct
  // /learn link or restored tab after prefs were cleared.
  if (!activeLanguageId) {
    return <Navigate to="/" replace />
  }

  if (!learnQuery.isSuccess) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-500">{t('learnSession.preparing')}</p>
      </div>
    )
  }

  const { added, lessons: servedLessons } = learnQuery.data
  const lessons = servedLessons.map((l) => swapped[l.card_id] ?? l)

  if (added === 0) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="text-center space-y-4">
          <p className="text-xl text-gray-700">{t('learnSession.nothingNew')}</p>
          <p className="text-sm text-gray-500">
            {t('learnSession.nothingNewDetail')}
          </p>
          <button
            type="button"
            onClick={() => navigate('/')}
            className="text-lang hover:underline text-sm"
          >
            {t('common.backToDashboardLong')}
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
  // "I already know this": a permanent skip, distinct from passing — the
  // card is retired (mark_card_known), not queued for review.
  const currentKnown = !!lesson?.quiz && knownCards.has(lesson.card_id)
  // Attempted-but-wrong also unlocks Next; the card stays unconfirmed.
  const currentAttempted =
    currentPassed ||
    currentKnown ||
    (!!lesson?.quiz && missedCards.has(lesson.card_id))

  const goToLesson = (i: number) => {
    setLessonIndex(i)
    setQuizInput('')
    setQuizResult(null)
    setWrongTries(0)
    setRetryToast(false)
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
          // Per-lesson type: a grammar card in a mixed session must be
          // graded as grammar, not the session's default.
          card_type: lesson.card_type === 'grammar' ? 'grammar' : 'vocabulary',
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
            const tries = wrongTries + 1
            setWrongTries(tries)
            if (tries === 1) {
              setRetryToast(true)
              if (retryTimer.current) window.clearTimeout(retryTimer.current)
              retryTimer.current = window.setTimeout(
                () => setRetryToast(false),
                3500,
              )
            }
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
            {lesson.card_type === 'grammar'
              ? t('learnSession.newGrammarCounter', {
                  current: lessonIndex + 1,
                  total: lessons.length,
                })
              : t('learnSession.newVocabCounter', {
                  current: lessonIndex + 1,
                  total: lessons.length,
                })}
          </p>
          {/* No language control mid-session — not the globe, and not the
              translations picker that used to sit here. Both change the
              card language under a walkthrough already in progress, which
              means re-fetching the lesson the learner is halfway through.
              It lives in Settings, where changing it costs nothing because
              nothing is running. */}
          <span className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => navigate('/')}
              className="text-sm text-lang hover:underline"
            >
              {t('common.backToDashboard')}
            </button>
          </span>
        </div>

        {lesson && (
          /* Review Mode wraps the WHOLE card, not each field: a reviewer can
             then select any span — the word, a clause of the example, the
             definition — and flag exactly that, instead of picking a field
             name from a list and describing which part they meant. */
          <Annotatable
            languageId={activeLanguageId}
            targetType={lesson.card_type === 'grammar' ? 'drill' : 'vocabulary'}
            targetId={lesson.card_id}
            targetLabel={lesson.title}
            source="learn"
            className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 space-y-4"
          >
            <div className="flex items-start justify-between gap-2">
              <div>
                <LanguageWrapper languageCode={languageCode}>
                  <h1 className="text-2xl font-bold text-gray-900">{lesson.title}</h1>
                </LanguageWrapper>
                {/* Arabic readings are the tashkeel-vocalized form — the
                    account-level short-vowels toggle hides them. Letter cards
                    are the exception: their reading is the Latin typing key
                    ("H", "3"), not tashkeel, and hiding it left the alphabet
                    deck with no clue what to type. */}
                {lesson.reading &&
                  (languageCode !== 'ar' ||
                    showTashkeel ||
                    lesson.part_of_speech === 'letter') && (
                  <p className="text-sm text-gray-500 mt-0.5">{lesson.reading}</p>
                )}
                {lesson.part_of_speech && (
                  <p className="text-xs text-gray-500 mt-0.5">{lesson.part_of_speech}</p>
                )}
              </div>
              {lesson.title && (
                <SpeakButton text={lesson.title} languageCode={languageCode} />
              )}
            </div>

            {lesson.definition && (
              <p className="text-gray-800">
                <span className="text-xs uppercase tracking-wide text-lang-label/80 block">
                  {t('learnSession.meaning')}
                </span>
                {lesson.definition}
              </p>
            )}

            {lesson.explanation && (
              <div>
                <span className="text-xs uppercase tracking-wide text-lang-label/80 block mb-1">
                  {t('learnSession.howItWorks')}
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
                <span className="text-xs uppercase tracking-wide text-lang-label/80 block mb-1">
                  {t('learnSession.inContext')}
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
                  {t('learnSession.cultureNote')}
                </span>
                <p className="text-sm text-lang-dark/80 whitespace-pre-wrap">
                  {lesson.culture_note}
                </p>
              </div>
            )}

            {lesson.references.length > 0 && (
              <div>
                <span className="text-xs uppercase tracking-wide text-lang-label/80 block mb-1">
                  {t('learnSession.sources')}
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
                <span className="text-xs uppercase tracking-wide text-lang-label/80 block mb-3">
                  {t('learnSession.yourTurn')}
                </span>
                <DrillCard
                  key={lesson.card_id}
                  // The lesson above is what the learner opened this card
                  // for. Stealing focus down here scrolls past it.
                  autoFocus={false}
                  sentence={lesson.quiz.sentence}
                  value={quizInput}
                  onChange={(v) => {
                    setQuizInput(v)
                    if (quizResult) setQuizResult(null)
                  }}
                  onSubmit={handleCheck}
                  disabled={currentPassed || currentKnown || validateMutation.isPending}
                  languageCode={languageCode}
                  inputRef={inputRef}
                  result={
                    currentPassed
                      ? currentSloppy
                        ? 'correct_sloppy'
                        : 'correct'
                      : currentKnown
                        ? null
                        : quizResult?.answer_result ?? null
                  }
                />
                {lesson.quiz.transliteration && (
                  <p className="text-sm italic text-gray-500 text-center mt-3">
                    {lesson.quiz.transliteration}
                  </p>
                )}
                {/* The gloss used to render as a bare line of `bark.3SG`
                    with nothing naming it — the same notation the review
                    session at least labels. Name it, and let it explain
                    itself. The translation directly below is what it
                    means; the two belong together. */}
                {showGlosses && lesson.quiz.gloss && (
                  <p className="text-xs text-gray-500 text-center mt-1">
                    <span className="text-[10px] uppercase tracking-wide text-lang-label/70 me-2">
                      {t('review.layerGloss')}
                      <InfoDot
                        label={t('review.glossHelpTitle')}
                        title={t('review.glossHelpTitle')}
                        testId="gloss-help"
                      >
                        {t('review.glossHelpBody')}
                      </InfoDot>
                    </span>
                    {lesson.quiz.gloss}
                  </p>
                )}
                {lesson.quiz.translation && (
                  <p className="text-xs text-gray-500 text-center mt-1">
                    {lesson.quiz.translation}
                  </p>
                )}
                {!currentPassed && !currentKnown && (
                  <button
                    type="button"
                    onClick={handleCheck}
                    disabled={!quizInput.trim() || validateMutation.isPending}
                    className="mt-3 w-full bg-white hover:bg-gray-50 disabled:opacity-40 text-gray-500 hover:text-lang rounded-2xl border-2 border-gray-300 px-6 py-2 text-2xl leading-none transition-colors"
                    aria-label={t('learnSession.checkAnswer')}
                    style={{ minHeight: '44px' }}
                  >
                    {validateMutation.isPending ? '…' : '→'}
                  </button>
                )}

                {/* Escape hatch: already know it, skip the drill entirely.
                    Retires the card (mark_card_known) instead of forcing an
                    answer — owner: "the ability to skip... mark it as done." */}
                {!currentPassed && !currentKnown && (
                  <p className="mt-2 text-center">
                    <button
                      type="button"
                      onClick={() => {
                        if (
                          window.confirm(
                            t('learnSession.alreadyKnowConfirm'),
                          )
                        )
                          knownMutation.mutate(lesson.card_id)
                      }}
                      disabled={knownMutation.isPending}
                      className="text-xs text-gray-500 hover:text-lang disabled:opacity-50"
                      title={t('learnSession.skipDrillTitle')}
                    >
                      {t('learnSession.alreadyKnowButton')}
                    </button>
                  </p>
                )}

                {/* On-screen keyboard for non-Latin scripts, during answering */}
                {!currentPassed && !currentKnown && hasKeyboardLayout(languageCode) && (
                  <div className="mt-3 space-y-2">
                    <div className="flex justify-end">
                      <button
                        type="button"
                        onClick={() => setShowKeyboard((v) => !v)}
                        className="text-xs text-gray-500 hover:text-gray-700 border border-gray-200 rounded-lg px-3 py-1.5 touch-manipulation"
                        style={{ minHeight: '44px' }}
                      >
                        {showKeyboard ? t('review.hideKeyboard') : t('review.showKeyboard')}
                      </button>
                    </div>
                    {showKeyboard && (
                      <OnScreenKeyboard
                        languageCode={languageCode as KeyboardLanguage}
                        onKeyPress={(key) => typeIntoQuiz(key)}
                        onEnter={handleCheck}
                        onBackspace={() => typeIntoQuiz('', true)}
                      />
                    )}
                  </div>
                )}
                {currentPassed && lesson.quiz && !currentSloppy && (
                  <p className="mt-3 text-sm text-green-700 text-center" role="status">
                    {t('learnSession.correctAdded')}
                  </p>
                )}
                {currentPassed && lesson.quiz && currentSloppy && (
                  <p className="mt-3 text-sm text-amber-700 text-center" role="status">
                    <Trans
                      i18nKey="learnSession.almostAccents"
                      values={{ answer: lesson.quiz.answer }}
                      components={{ b: <b /> }}
                    />
                  </p>
                )}
                {currentKnown && (
                  <p className="mt-3 text-sm text-gray-500 text-center" role="status">
                    {t('learnSession.markedKnown')}
                  </p>
                )}
                {/* First miss: the fading toast below invites a retry with no
                    reveal — the examples above hold the answer. From the
                    second miss on, reveal so nobody is stuck. */}
                {!currentPassed &&
                  quizResult &&
                  quizResult.answer_result !== 'correct' &&
                  quizResult.answer_result !== 'correct_sloppy' &&
                  wrongTries >= 2 && (
                    <p className="mt-3 text-sm text-red-600 text-center" role="alert">
                      <Trans
                        i18nKey="learnSession.notQuiteReveal"
                        values={{ answer: lesson.quiz.answer }}
                        components={{ b: <b /> }}
                      />
                    </p>
                  )}
                {retryToast && (
                  <div
                    className="pointer-events-none fixed inset-x-0 bottom-24 z-40 flex justify-center px-4"
                    data-testid="retry-toast"
                    role="status"
                  >
                    <div className="learn-retry-toast rounded-xl bg-gray-900/90 px-4 py-2.5 text-sm text-white shadow-lg">
                      {t('learnSession.retryToast')}
                    </div>
                  </div>
                )}
              </div>
            )}

            <SuggestChange
              languageId={activeLanguageId}
              targetType={lesson.card_type === 'grammar' ? 'drill' : 'vocabulary'}
              targetId={lesson.card_id}
              targetLabel={
                lesson.quiz
                  ? lesson.quiz.sentence.replace('{{answer}}', lesson.quiz.answer)
                  : lesson.title
              }
            />
          </Annotatable>
        )}

        <div className="flex items-center gap-3">
          {lessonIndex > 0 && (
            <button
              type="button"
              onClick={() => goToLesson(lessonIndex - 1)}
              className="rounded-xl border border-gray-300 bg-white px-5 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
              style={{ minHeight: '44px' }}
            >
              {t('learnSession.previous')}
            </button>
          )}
          {isLast ? (
            <button
              type="button"
              onClick={() => navigate('/review')}
              disabled={!currentAttempted}
              title={currentAttempted ? undefined : t('learnSession.tryFirst')}
              className="flex-1 bg-lang hover:bg-lang-dark disabled:opacity-50 text-lang-on font-semibold rounded-xl px-6 py-3 text-sm"
              style={{ minHeight: '44px' }}
            >
              {t('learnSession.startReviewing')}
            </button>
          ) : (
            <button
              type="button"
              onClick={() => goToLesson(lessonIndex + 1)}
              disabled={!currentAttempted}
              title={currentAttempted ? undefined : t('learnSession.tryFirst')}
              className="flex-1 bg-lang hover:bg-lang-dark disabled:opacity-50 text-lang-on font-semibold rounded-xl px-6 py-3 text-sm"
              style={{ minHeight: '44px' }}
            >
              {t('learnSession.next')}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
