import { useState, useRef, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { Headphones, Settings as SettingsIcon, Undo2 } from 'lucide-react'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getCramCards,
  getDueCards,
  getSessionReadiness,
  markCardKnown,
  submitReview,
  validateAnswer,
} from '../../api/review'
import { recordGymAttempt, generateGymDrills } from '../../api/gym'
import { effectiveSupportLocale, getLanguages, getProfile } from '../../api/profile'
import type { DueCard } from '../../api/types'
import { usePrefsStore } from '../../stores/prefsStore'
import { languageDisplayName } from '../../lib/languages'
import TrailblazerWait from './TrailblazerWait'
import { useReviewSession } from './useReviewSession'
import {
  clearSnapshot,
  readSnapshot,
  saveSnapshot,
  snapshotKey,
} from './sessionSnapshot'
import DrillCard from './DrillCard'
import FeedbackPanel from './FeedbackPanel'
import ReviewDetail from './ReviewDetail'
import SuggestChange from '../contribute/SuggestChange'
import CardFeedback from './CardFeedback'
import SessionSummary from './SessionSummary'
import OnScreenKeyboard from '../keyboards/OnScreenKeyboard'
import { composeScript, deleteLastUnit, finalizeInput } from '../keyboards/translit'
import { hintLayersFor, safePrompt } from './hintLayers'
import TranslateMyCards from './TranslateMyCards'
import SpeakButton from '../../components/SpeakButton'
import FormsPanel from '../../components/FormsPanel'
import { TTS_LANGUAGES, getTTSUrl, prefetchTTS } from '../../api/audio'
import LearningTip from '../tips/LearningTip'
import { hasKeyboardLayout } from '../keyboards/OnScreenKeyboard'
import type { KeyboardLanguage } from '../keyboards/OnScreenKeyboard'

/** UX dials for background Gym generation (owner, 2026-07-27).
 *
 * GEN_MAX_SHARE — at most this share of a session is SWAPPED for freshly
 * generated drills; the rest stays existing material. One number to shift
 * the mix if generated content should feature more or less. (Filling a
 * short deck up to the learner's requested count is exempt — reaching the
 * goal always beats the mix.)
 *
 * GEN_WAIT_MS — nobody stares at the end-of-deck wait longer than this. If
 * generation still hasn't landed, the session tops up with EXISTING
 * questions from the same forms (they still meet the goal) and moves on;
 * fresh drills that land later only ever swap upcoming, not-yet-seen slots.
 */
const GEN_MAX_SHARE = 0.5
const GEN_WAIT_MS = 8000

/** The one place a learner ever waits in the Gym: shown only if they out-run
 * background generation (a thin form + a fast learner). The fresh drills are
 * moments away — this is a brief hand-off, not a dead end. */
function CramTopUp({ label }: { label: string }) {
  const { t } = useTranslation()
  return (
    <div
      className="min-h-screen bg-gray-50 flex items-center justify-center px-4"
      data-testid="cram-topup"
    >
      <div className="text-center space-y-3">
        <div
          className="mx-auto h-6 w-6 animate-spin rounded-full border-2 border-lang border-t-transparent"
          aria-hidden
        />
        <p className="text-gray-700">{label}</p>
        <p className="text-xs text-gray-500">
          {t('review.cramTopupNote')}
        </p>
      </div>
    </div>
  )
}

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
  // Watching the PROFILE, not just this page's own locale picker. There are
  // two ways to change the language and only one used to restart the
  // session: the in-page picker called onLocaleChanged, while the globe in
  // the header wrote the profile and refetched — but a running session holds
  // its card list in state, so the refetched Spanish never reached the
  // screen. The chrome switched, the cards did not, and only leaving the
  // page and coming back fixed it. Keyed off the value itself, so any route
  // that changes it (either picker, or a sync from another device) restarts
  // the session.
  const { data: localeProfile } = useQuery({
    queryKey: ['profile'],
    queryFn: getProfile,
  })
  // Effective, not raw: in the automatic case the help language IS the
  // interface language, so a globe tap must restart this session the same
  // way an explicit Settings change does.
  const supportLocale = localeProfile
    ? effectiveSupportLocale(localeProfile)
    : null
  const seenLocale = useRef<string | null>(null)
  useEffect(() => {
    if (supportLocale == null) return
    // First load is not a change — remounting there would refetch the
    // session's cards twice on every entry.
    if (seenLocale.current !== null && seenLocale.current !== supportLocale) {
      setEpoch((e) => e + 1)
    }
    seenLocale.current = supportLocale
  }, [supportLocale])
  return (
    <ReviewSessionInner
      key={`${activeLanguageId ?? 'none'}:${epoch}`}
      cram={cram}
    />
  )
}

function ReviewSessionInner({
  cram,
}: {
  cram: boolean
}) {
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()
  const queryClient = useQueryClient()
  const [searchParams] = useSearchParams()
  const cramPoints = cram ? (searchParams.get('points') ?? '') : ''
  // The Gym passes mix=1: cards from the selected form categories are
  // shuffled together, so accusative singular and dative plural alternate
  // instead of arriving grouped per point (the mixed bag is the point).
  const cramMix = cram && searchParams.get('mix') === '1'
  // The Gym passes count=N: the session serves that many questions, drawn
  // round-robin across the chosen forms (not the old 3-per-form cap).
  const cramCountRaw = cram ? Number(searchParams.get('count')) : NaN
  const cramCount = Number.isFinite(cramCountRaw) && cramCountRaw > 0 ? cramCountRaw : undefined
  // The Gym passes gen=1 when the learner opted into fresh variations: the
  // session serves the seeded corpus immediately and drafts new drills in the
  // background, weaving them in as they land (no wait up front). The learner
  // only pauses on a "drafting…" screen if they out-run generation.
  const genRequested = cram && searchParams.get('gen') === '1'
  // Grammar Only / Vocab Only sessions (dashboard Review tile expansion).
  const typeParam = searchParams.get('type')
  const reviewType =
    typeParam === 'grammar' || typeParam === 'vocabulary' ? typeParam : undefined
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)
  const [userInput, setUserInput] = useState('')
  const [lastInput, setLastInput] = useState('')
  const [showKeyboard, setShowKeyboard] = useState(true)
  const [saveErrorCount, setSaveErrorCount] = useState(0)
  // Gym chart peek (WP25c): hidden on every card until opened. Cram is
  // ungraded practice, so looking the form up mid-question is a feature.
  const [chartOpen, setChartOpen] = useState(false)
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
  const profileQuery = useQuery({ queryKey: ['profile'], queryFn: getProfile })
  // Account setting (owner: "read the full sentence audio when users get
  // the answer correct. Accounts should be able to turn this off."), so it
  // behaves the same on every device the account is opened on. Absent —
  // older backend, migration 20261001 not applied — reads as ON: the
  // feature is the default, the toggle is the escape.
  const sentenceAudioOnCorrect =
    profileQuery.data?.sentence_audio_on_correct ?? true
  const profile = profileQuery.data
  // Resolved means settled, not succeeded: a failed profile fetch degrades
  // to the 'en' default rather than stranding the session behind the gate.
  const profileResolved = profileQuery.isSuccess || profileQuery.isError
  const supportLocale = effectiveSupportLocale(profile)
  // Trailblazer gate — reviews only. Cram draws from grammar points the
  // learner picked, not a locale-backed queue, so it never waits.
  const [startNow, setStartNow] = useState(false)
  const readinessQuery = useQuery({
    queryKey: ['session-readiness', activeLanguageId, 'review', sessionSize],
    queryFn: () => getSessionReadiness(activeLanguageId!, sessionSize),
    enabled: !!activeLanguageId && !cram,
    retry: 1,
  })
  const gated =
    !cram &&
    !startNow &&
    readinessQuery.data != null &&
    !readinessQuery.data.review.ready_enough
  // Bumped when the wait screen hands over — see handleStart, declared below
  // once `cards` exists.
  const [deckEpoch, setDeckEpoch] = useState(0)

  const { data: fetched, isLoading, isError } = useQuery(
    cram
      ? {
          queryKey: ['cram-cards', cramPoints, cramMix, cramCount],
          queryFn: async () => {
            const cards = await getCramCards(cramPoints.split(','), cramCount)
            if (!cramMix) return cards
            const mixed = [...cards]
            for (let i = mixed.length - 1; i > 0; i--) {
              const j = Math.floor(Math.random() * (i + 1))
              ;[mixed[i], mixed[j]] = [mixed[j], mixed[i]]
            }
            return mixed
          },
          enabled: cramPoints.length > 0,
          staleTime: Infinity, // one fetch per cram session — no mid-session reshuffle
          gcTime: 0,
          refetchOnWindowFocus: false,
        }
      : {
          queryKey: [
            'due-cards', activeLanguageId, sessionSize, reviewType ?? 'all',
            supportLocale, deckEpoch,
          ],
          queryFn: () => getDueCards(activeLanguageId!, sessionSize, reviewType),
          // Deliberately NOT gated on readiness. Due cards already exist —
          // fetching them is read-only and cheap, so the wait screen decides
          // what to SHOW, never whether to load. (Gating the fetch stalled a
          // mid-session language switch behind the new pair's readiness.)
          //
          // It IS gated on the profile having resolved. supportLocale in the
          // key defaults to 'en' while the profile is in flight, so an
          // ungated fetch could start under the placeholder key; the profile
          // then landed, the key corrected itself, a second fetch fired —
          // and the `cards === null` snapshot guard below DISCARDED it,
          // because the racing first fetch had already filled the deck.
          // Whichever deck won the race was the one the learner kept: the
          // "English flashes, then the right language" report, and a wasted
          // fetch besides. Waiting costs nothing warm (the dashboard already
          // cached the profile) and one round-trip cold — paid before
          // anything renders, which is the point.
          enabled: !!activeLanguageId && profileResolved,
          // A live session must never see its deck change under it, and a
          // NEW session must never flash the previous one's cached cards:
          // fetch fresh on mount, then freeze.
          gcTime: 0,
          staleTime: Infinity,
          refetchOnWindowFocus: false,
        },
  )

  // A settings round-trip parks the session in sessionStorage (keyed by this
  // exact URL); coming back restores deck + position instead of refetching —
  // including any background-generated Gym drills, which exist nowhere else.
  const location = useLocation()
  // Identity-keyed (see sessionSnapshot): a deck parked under Russian must
  // not resume a session opened under Latin. supportLocale can be the 'en'
  // placeholder for a beat while the profile loads — harmless here, because
  // the deck query below is gated on the profile too, and a snapshot saved
  // under the placeholder key never matches a real identity's park.
  const parkKey = snapshotKey(
    location.pathname,
    location.search,
    `${activeLanguageId ?? 'none'}:${supportLocale}`,
  )
  const [parked] = useState(() => readSnapshot(parkKey))

  // Snapshot the deck at session start — refetches and cache invalidations
  // (tab focus, summary cleanup) can't make cards appear/disappear mid-run.
  const [cards, setCards] = useState<DueCard[] | null>(parked?.cards ?? null)
  useEffect(() => {
    if (fetched && cards === null) setCards(fetched)
  }, [fetched, cards])

  // Leaving the Trailblazer wait re-pulls the deck.
  //
  // The deck is fetched on mount and then frozen — staleTime Infinity plus
  // the snapshot above — which is right for a running session and wrong for
  // one that started behind the wait. Those cards were pulled BEFORE the
  // fill landed, so the learner sat through the whole wait, played the
  // trivia game, and then met the very English they had been waiting to have
  // translated. Nothing refetched, because nothing had changed from
  // react-query's point of view.
  //
  // Changing the query key is what re-fetches. The alternatives don't work:
  // the deck deliberately isn't gated on readiness (gating it stalled a
  // mid-session language switch behind the new pair's fill), and staleTime
  // Infinity means it will never refetch on its own. Clearing the snapshot
  // in the same breath lets the effect above take the fresh deck; gcTime 0
  // means the new key has nothing cached to flash first.
  const handleStart = useCallback(() => {
    setCards(null)
    setDeckEpoch((n) => n + 1)
    setStartNow(true)
  }, [])

  const session = useReviewSession(
    cards ?? [],
    parked
      ? { index: parked.index, results: parked.results, requeued: parked.requeued }
      : undefined,
  )
  // The parking spot is single-use: consumed on restore, rewritten on the next
  // settings hop, and cleared for good once the session reaches its summary.
  useEffect(() => {
    if (parked) clearSnapshot(parkKey)
  }, [parked, parkKey])
  useEffect(() => {
    if (session.phase === 'summary') clearSnapshot(parkKey)
  }, [session.phase, parkKey])
  // Live current-index for the background-generation callback below (which runs
  // long after it was created): it must not weave fresh drills into slots the
  // learner has already passed.
  const currentIndexRef = useRef(0)
  currentIndexRef.current = session.currentIndex

  // Background generation (WP41): with gen=1 the Gym asked for fresh drills.
  // We kick off generation once, in the background, while the learner works
  // through the seeded set — then splice the new drills into the live deck as
  // they land. `genSettled` is true the moment generation can add nothing more
  // (produced its batch, or failed / was rejected), so the end-of-session
  // "drafting…" wait knows when to give up and show the real summary.
  const [genSettled, setGenSettled] = useState(!genRequested)
  const genStarted = useRef(false)
  const generateMutation = useMutation({
    mutationFn: () => generateGymDrills(cramPoints.split(',')),
    onSuccess: async (res) => {
      try {
        if (res.generated > 0) {
          // Re-draw the pool (now including the learner's fresh, unseen drills)
          // and weave in the ones not already in this session, capped to what
          // was just generated so we add roughly the fresh batch, not the corpus.
          const refreshed = await getCramCards(cramPoints.split(','), 100)
          setCards((prev) => {
            if (!prev) return prev
            const have = new Set(
              prev.map((c) => c.drill_id).filter(Boolean) as string[],
            )
            const target = cramCount ?? prev.length
            // Unseen drills from the re-draw: enough to fill a short deck to
            // the target AND deliver the fresh batch, never the whole corpus.
            const novel = refreshed
              .filter((c) => c.drill_id && !have.has(c.drill_id))
              .slice(0, Math.max(res.generated, target - prev.length))
            if (cramMix) {
              for (let i = novel.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1))
                ;[novel[i], novel[j]] = [novel[j], novel[i]]
              }
            }
            if (!novel.length) return prev
            // Keep the session at the count the learner asked for. If the seeded
            // set fell short, fill the gap up to the target first — reaching the
            // goal beats any mix preference. Then weave fresh drills in by
            // REPLACING upcoming (not-yet-seen) cards from the end — opting in
            // changes WHICH questions appear, not HOW MANY — with the swapped
            // share capped by the GEN_MAX_SHARE dial.
            const next = [...prev]
            let ni = 0
            while (next.length < target && ni < novel.length) {
              next.push(novel[ni++])
            }
            const swapCap = Math.max(
              0,
              Math.min(res.generated, Math.ceil(target * GEN_MAX_SHARE)) - ni,
            )
            let swapped = 0
            for (
              let i = next.length - 1;
              i > currentIndexRef.current && ni < novel.length && swapped < swapCap;
              i--
            ) {
              next[i] = novel[ni++]
              swapped++
            }
            return next
          })
        }
      } finally {
        setGenSettled(true)
      }
    },
    // Out of allowance / generation off / any failure: carry on with the
    // seeded set — the session must never hang on a background top-up.
    onError: () => setGenSettled(true),
  })
  // Start once the seeded snapshot is in place — the append reads `cards`, so
  // generation must not resolve before there's a deck to weave into.
  useEffect(() => {
    if (genRequested && !genStarted.current && cramPoints.length > 0 && cards !== null) {
      genStarted.current = true
      generateMutation.mutate()
    }
  }, [genRequested, cramPoints, cards, generateMutation])

  // The wait has a ceiling (owner): if the learner exhausts the deck and
  // generation still hasn't landed after GEN_WAIT_MS, stop waiting — top the
  // session up with EXISTING questions from the same forms (they still meet
  // the goal) and show the summary if even those run dry. Generation landing
  // later is still welcome: its weave only ever touches upcoming slots.
  const [genTimedOut, setGenTimedOut] = useState(false)
  const fallbackStarted = useRef(false)
  const waitingForGen = genRequested && !genSettled && !session.currentCard
  useEffect(() => {
    if (!waitingForGen || genTimedOut) return
    const t = window.setTimeout(() => setGenTimedOut(true), GEN_WAIT_MS)
    return () => window.clearTimeout(t)
  }, [waitingForGen, genTimedOut])
  useEffect(() => {
    if (!genTimedOut || fallbackStarted.current) return
    fallbackStarted.current = true
    ;(async () => {
      try {
        const refreshed = await getCramCards(cramPoints.split(','), 100)
        setCards((prev) => {
          if (!prev) return prev
          const have = new Set(
            prev.map((c) => c.drill_id).filter(Boolean) as string[],
          )
          const extra = refreshed.filter(
            (c) => c.drill_id && !have.has(c.drill_id),
          )
          const target = cramCount ?? prev.length
          if (prev.length >= target || !extra.length) return prev
          return [...prev, ...extra.slice(0, target - prev.length)]
        })
      } catch {
        // Nothing to add — the wait still ends.
      } finally {
        setGenSettled(true)
      }
    })()
  }, [genTimedOut, cramPoints, cramCount])

  // Fresh drills appended after the deck was exhausted leave the session stuck
  // on 'summary' with a valid current card — flow straight into them.
  useEffect(() => {
    if (session.phase === 'summary' && session.currentCard) session.resume()
  }, [session.phase, session.currentCard, session])

  // "Hidden initially" means hidden on EVERY card, not just the first.
  useEffect(() => setChartOpen(false), [session.currentIndex])

  // Warm the TTS cache for the current card so the feedback-screen audio (the
  // answer word and the full sentence) plays the instant it's clicked instead
  // of lagging on first synthesis. Prefetch only fetches — never plays — so
  // running it while the answer is still hidden can't leak it aloud.
  useEffect(() => {
    const c = session.currentCard
    if (!c) return
    const full = c.sentence.includes('{{answer}}')
      ? c.sentence.replace('{{answer}}', c.correct_answer)
      : c.correct_answer
    prefetchTTS(c.language_code, full)
    prefetchTTS(c.language_code, c.correct_answer)
  }, [session.currentCard])

  // Gym: after a MISS, open the full chart automatically — the moment a
  // learner gets a conjugation/declension wrong is exactly when they want to
  // see the whole paradigm they should have drawn from.
  const missed =
    session.validationResult?.answer_result === 'wrong' ||
    session.validationResult?.answer_result === 'wrong_form'
  useEffect(() => {
    if (cram && missed && (session.phase === 'feedback' || session.phase === 'rating')) {
      setChartOpen(true)
    }
  }, [cram, missed, session.phase])

  const qwertyTranslit = usePrefsStore((s) => s.qwertyTranslit)

  // English cards render definitions/translations in the learner's support
  // locale — let them switch it right here instead of trekking to Settings.
  // Saving restarts the session (key remount) with re-localized cards.
  // Not gated on the course being English: cards.py _effective_locale
  // applies support_locale to EVERY course, so a Spanish learner whose
  // locale drifted to Arabic needs this switch too — and needs the option
  // list to actually load, which `enabled: studyingEnglish` prevented.
  const { data: languages = [] } = useQuery({
    queryKey: ['languages'],
    queryFn: getLanguages,
  })

  const validateMutation = useMutation({
    mutationFn: validateAnswer,
    onSuccess: (result, variables) => {
      setLastInput(variables.user_input)
      session.setValidationResult(result)
      setUserInput('')
      // Read the whole sentence aloud once the learner got the word — the
      // one moment they can just listen, no longer hunting for it. The clip
      // was prefetched while they typed, so this is a cache hit; a browser
      // that refuses the autoplay stays quiet and the play button on the
      // feedback screen still works.
      //
      // Amber ('correct_sloppy') plays too. It used to be 'correct' only,
      // on the reasoning that an "almost" screen is a correction to read —
      // but amber IS the accent/diacritic miss, and hearing the word said
      // properly is the correction. Orange and red stay quiet: those are a
      // wrong form and a wrong answer, where the text is what teaches.
      const said = session.currentCard
      if (
        sentenceAudioOnCorrect &&
        (result.answer_result === 'correct' ||
          result.answer_result === 'correct_sloppy') &&
        said &&
        TTS_LANGUAGES.has(said.language_code)
      ) {
        const full = said.sentence.includes('{{answer}}')
          ? said.sentence.replace('{{answer}}', said.correct_answer)
          : said.correct_answer
        void getTTSUrl(said.language_code, full)
          .then((url) => {
            if (url) void new Audio(url).play().catch(() => {})
          })
          .catch(() => {})
      }
      // Gym only: fold this answer into the learner's per-drill history so
      // selection can adapt. Fire-and-forget; ungraded, never blocks the UI.
      // used_hint reflects whether optional help was on when they answered
      // (the baseline prompt is always free and never counts).
      const answered = session.currentCard
      if (cram && answered?.drill_id) {
        void recordGymAttempt(
          answered.drill_id,
          result.answer_result,
          hintLevel > 0,
        ).catch(() => {})
      }
    },
    // A failed check used to die silently — the arrow stayed white and
    // nothing explained why the answer wouldn't grade (beta report).
    onError: () => {},
  })
  const checkFailed = validateMutation.isError

  // The session advances optimistically in rate(); if the backend save
  // fails, the review is lost server-side, so surface that to the user.
  const submitMutation = useMutation({
    mutationFn: submitReview,
    onSuccess: () => {
      // Counts were only refreshed by the Finish button on the summary
      // screen. Leave a session any other way — back gesture, the tab, a
      // tap through to the dashboard — and the caches were still inside
      // their 60s staleTime with refetchOnWindowFocus off, so the due count
      // sat at its pre-session value with no event coming to correct it.
      //
      // refetchType 'none' marks them stale WITHOUT firing a request per
      // card: nothing refetches mid-session, and whatever the learner opens
      // next fetches fresh instead of showing a stale number.
      for (const key of [['dashboard'], ['due-cards'], ['learn-decks']]) {
        queryClient.invalidateQueries({ queryKey: key, refetchType: 'none' })
      }
    },
    onError: () => {
      setSaveErrorCount((n) => n + 1)
    },
  })

  // "I know this — retire": suspend the card server-side, then move on.
  // Dashboard/due counts refetch to reflect the smaller queue.
  const knownMutation = useMutation({
    mutationFn: (cardId: string) => markCardKnown(cardId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      session.advance()
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
    // Hangul keys are jamo that must fuse into syllable blocks; every other
    // script passes through composeScript untouched.
    const compose = (value: string) => composeScript(card.language_code, value)
    const input = inputRef.current
    if (!input) {
      // If no ref available, just append
      setUserInput((prev) => compose(prev + key))
      return
    }

    const start = input.selectionStart ?? input.value.length
    const end = input.selectionEnd ?? input.value.length
    const typed = input.value.slice(0, start) + key
    const composed = compose(typed)
    setUserInput(composed + input.value.slice(end))

    // Restore cursor position after React re-render. Composition can SHORTEN
    // the text (three jamo become one block), so the caret follows the
    // composed prefix rather than the raw keypress length.
    const caret = composed.length
    requestAnimationFrame(() => {
      input.focus()
      input.setSelectionRange(caret, caret)
    })
  }

  const handleKeyboardBackspace = () => {
    const code = card?.language_code ?? ''
    const input = inputRef.current
    if (!input) {
      setUserInput((prev) => deleteLastUnit(code, prev))
      return
    }
    const start = input.selectionStart ?? input.value.length
    const end = input.selectionEnd ?? input.value.length
    // Delete the selection, or one UNIT before the caret — for Hangul that
    // peels a jamo off the syllable (한 → 하) instead of the whole block.
    const head =
      start === end
        ? deleteLastUnit(code, input.value.slice(0, start))
        : input.value.slice(0, start)
    setUserInput(head + input.value.slice(end))
    const caret = head.length
    requestAnimationFrame(() => {
      input.focus()
      input.setSelectionRange(caret, caret)
    })
  }

  if (gated && activeLanguageId) {
    return (
      <TrailblazerWait
        languageId={activeLanguageId}
        kind="review"
        limit={sessionSize}
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

  // A failed fetch leaves `cards` null forever, and the loading branch below
  // caught that case too — so a 500 showed "Loading cards…" indefinitely with
  // no error, no retry and no way back. Say what happened instead.
  if (isError) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="text-center space-y-4">
          <p className="text-xl text-red-600">{t('review.loadFailed')}</p>
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

  if (isLoading || cards === null) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-500">{t('review.loadingCards')}</p>
      </div>
    )
  }

  if (cards.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="text-center space-y-4">
          <p className="text-xl text-gray-700">
            {cram
              ? t('review.noCram')
              : t('review.noDue')}
          </p>
          <button
            type="button"
            onClick={() => navigate('/')}
            className="text-lang hover:underline text-sm touch-manipulation"
          >
            {t('review.backToDashboard')}
          </button>
        </div>
      </div>
    )
  }

  // End of the current deck. If a background top-up is still in flight, the
  // learner out-ran generation — hold on a brief "drafting…" screen (the only
  // place they ever wait) rather than ending; the fresh drills are about to
  // land and resume() will flow straight into them. Otherwise it's a real finish.
  if (!session.currentCard) {
    if (genRequested && !genSettled) {
      return <CramTopUp label={t('review.draftingFresh')} />
    }
    return (
      <div>
        {saveErrorCount > 0 && (
          <div
            role="alert"
            className="max-w-2xl mx-auto mt-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl px-4 py-3"
          >
            {t('review.saveErrorEnd', { count: saveErrorCount })}
          </div>
        )}
        <SessionSummary
          accuracy={session.accuracy}
          totalTimeMs={session.totalTimeMs}
          cardsReviewed={session.cardsReviewed}
          note={cram ? t('review.cramNote') : undefined}
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

  // A top-up landed after we'd hit the end: resume() (an effect) flips us back
  // to answering next tick — show the hand-off, not a one-frame stray summary.
  if (session.phase === 'summary') {
    return <CramTopUp label={t('review.loadingFreshDrills')} />
  }

  const card = session.currentCard
  if (!card) return null

  // Language-aware hint layers (see hintLayers.ts): romanization first for
  // non-Latin scripts, word-by-word gloss first for unfamiliar-syntax
  // languages, translation before the morphology recipe everywhere — the
  // recipe stays last because it all but spells out the answer.
  // chart_word is the lemma the Gym drill exercises — expose it as the
  // leading "Base form" hint (see hintLayers.ts).
  const layers = hintLayersFor(card.language_code, { ...card, base: card.chart_word })
  // In the GYM the drill's authored hint IS the prompt — the base form + person
  // to produce ("preparar, tú"). It's present for every conjugation drill
  // (unlike chart_word, which needs an NLP backend), so it's shown ALWAYS in its
  // own slot and never counts as a hint. That leaves the OPTIONAL layers each
  // carrying distinct help — translation (meaning), reading (pronunciation),
  // word-by-word (structure) — behind the Hint button, which feeds the adaptive
  // "hint dependence" signal. The full chart stays the deepest reveal (on miss).
  // Graded review keeps the original layered behaviour.
  //
  // But the prompt must never GIVE the answer. Some authored hints spell it out
  // ("to watch — add -es" → watches) or are the base form itself ("to speak" →
  // speak). Strip a trailing spelling recipe, then blank the prompt entirely if
  // it still contains the answer as a whole word (a base-form drill) — the
  // learner recalls it from the sentence + the optional meaning hint instead.
  // Prefer the server-built standardized baseline ("word (form)"); legacy
  // cards without one fall back to the raw hint / chart word. Either way the
  // leak guard runs last — the prompt must never contain the answer.
  const baseText = cram
    ? safePrompt(card.baseline || card.hint || card.chart_word || '', card.correct_answer)
    : ''
  const baseLayer = baseText
    ? { field: 'base' as const, label: t('review.layerPrompt'), text: baseText }
    : undefined
  const optionalLayers = cram
    ? layers.filter((l) => l.field !== 'base' && l.field !== 'hint')
    : layers
  const maxHint = optionalLayers.length
  const revealedLayers =
    session.phase !== 'answering'
      ? optionalLayers
      : optionalLayers.slice(0, Math.min(hintLevel, maxHint))
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
  // In the Gym the hint is already the always-shown baseline below, so don't
  // also float it above as the listening cue (that would double it).
  const listeningCue =
    listening && answering && !baseLayer
      ? layers.find((l) => l.field === 'hint')
      : undefined
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
            {t('review.saveErrorLive', { count: saveErrorCount })}
          </div>
        )}
        {/* Session utility bar (Bunpro-style: exit, path, tutor, settings).
            session-quiet: under the "focus" skin (One Thing at a Time) this
            chrome recedes until pointed at — see index.css. Inert elsewhere. */}
        <div className="session-quiet flex items-center justify-between">
          <button
            type="button"
            onClick={() => {
              // A deliberate exit abandons the session — nothing to come back to.
              clearSnapshot(parkKey)
              navigate('/')
            }}
            aria-label={t('review.exitSession')}
            className="text-xl leading-none text-gray-500 hover:text-lang"
          >
            {t('review.exitArrow')}
          </button>
          {/* No globe in a running session: it changes the card language
              mid-review. It lives on every other page, and in Settings. */}
          <div className="flex items-center gap-4 text-sm text-gray-500">
            <button type="button" onClick={() => navigate('/grammar')} className="hover:text-lang">
              {t('review.path')}
            </button>
            <button type="button" onClick={() => navigate('/tutor')} className="hover:text-lang">
              {t('review.tutorLink')}
            </button>
            <button
              type="button"
              onClick={() => {
                // Park the live session so Settings' "Back to session" (or the
                // browser's back button) restores it exactly where it stands.
                if (cards && session.phase !== 'summary') {
                  saveSnapshot(parkKey, {
                    cards,
                    index: session.currentIndex,
                    results: session.results,
                    requeued: session.requeued,
                  })
                }
                navigate('/account', {
                  state: { from: location.pathname + location.search },
                })
              }}
              aria-label={t('nav.account')}
              className="hover:text-lang"
            >
              <SettingsIcon aria-hidden className="h-[18px] w-[18px]" />
            </button>
          </div>
        </div>

        {/* Progress (the BAR below stays at full strength under the focus
            skin — it is D's "single line" of progress; this counter row is
            the part that recedes) */}
        <div className="session-quiet flex items-center justify-between text-sm text-gray-500">
          {/* The count runs over the deck being WORKED, re-drills included —
              dividing by the original deck is what produced "Card 9 of 7"
              once two cards came back. A growing total needs a reason next
              to it, so the redo count is named rather than left to be
              inferred, and a card on its second appearance says so. */}
          <span className="flex items-center gap-2">
            <span>
              {t('review.cardOf', {
                current: session.currentIndex + 1,
                total: session.deckSize,
              })}
            </span>
            {session.isRepeat ? (
              <span
                data-testid="review-repeat-chip"
                className="text-xs rounded-full px-2 py-0.5 bg-amber-100 text-amber-900 font-semibold"
              >
                {t('review.repeatCard')}
              </span>
            ) : (
              session.requeued.length > 0 && (
                <span className="text-xs" data-testid="review-redo-count">
                  {t('review.toRedo', { count: session.requeued.length })}
                </span>
              )
            )}
          </span>
          {cram ? (
            <span className="text-xs rounded-full px-2 py-0.5 bg-lang-soft text-lang font-semibold">
              {t('review.quickCram')}
            </span>
          ) : (
            /* Same as Learn: no language control inside a running
               session. It belongs in Settings. */
            <span className="flex items-center gap-2">
              <span>{t(`review.cardType.${card.card_type}`)}</span>
            </span>
          )}
        </div>

        {/* Progress bar */}
        <div className="w-full bg-gray-200 rounded-full h-1.5">
          <div
            className="bg-lang h-1.5 rounded-full transition-all"
            style={{
              // Same denominator as the counter: a bar that fills before the
              // re-drills are done is the same lie in another shape.
              width: `${(session.currentIndex / Math.max(1, session.deckSize)) * 100}%`,
            }}
          />
        </div>

        {/* A learning tip at the very start of a session (throttled, off in
            Settings). Only on the first card so it never interrupts the flow. */}
        {session.currentIndex === 0 && (
          <LearningTip context="session" />
        )}

        {/* Card area */}
        <div className="bg-lang-tint rounded-2xl shadow-sm border border-lang-edge p-6 md:p-8">
          {shownTopHint && (
            <p className="text-sm text-gray-500 text-center mb-4">
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
                label={t('review.playSentence')}
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

          {/* Baseline PROMPT (Gym): the dictionary form + person you conjugate
              FROM — always shown in its own slot, never a "hint". */}
          {baseLayer && (
            <div className="mt-3 text-center" data-testid="baseline-prompt">
              <span className="inline-block rounded-full bg-lang-soft text-lang px-3 py-1 text-sm font-medium">
                {baseLayer.text}
              </span>
            </div>
          )}

          {belowLayers.length > 0 && (
            <div className="mt-4 space-y-1 text-center">
              {belowLayers.map((l) => (
                <p
                  key={l.field}
                  className={
                    l.field === 'transliteration'
                      ? 'text-sm italic text-gray-500'
                      : 'text-xs text-gray-500'
                  }
                >
                  <span className="text-[10px] uppercase tracking-wide text-lang-label/70 me-2">
                    {l.label}
                  </span>
                  {l.text}
                  {/* Naming the language it is in was only half the fix: the
                      learner still could not read it. Their own cards are
                      never swept by the background loop (they are private),
                      so this is the only place the fill can be asked for —
                      and asking has to happen where the gap is noticed, not
                      on a Decks page nobody visits mid-session. */}
                  {l.foreign && card.card_type === 'personal' && activeLanguageId && (
                    <TranslateMyCards languageId={activeLanguageId} />
                  )}
                </p>
              ))}
            </div>
          )}

          {cram && card.morphology != null && (
            <div className="mt-5 border-t border-gray-100 pt-3 text-center">
              <button
                type="button"
                onClick={() => setChartOpen((v) => !v)}
                aria-expanded={chartOpen}
                className="text-sm text-gray-500 hover:text-lang"
              >
                {chartOpen
                  ? t('review.hideChart')
                  : `${missed && !answering ? t('review.seeFullChart') : t('review.peekChart')}${
                      card.chart_word ? ` — ${card.chart_word}` : ''
                    }`}
              </button>
              {chartOpen && (
                <div className="mt-3 text-start" data-testid="gym-chart">
                  <FormsPanel
                    morphology={card.morphology}
                    languageCode={card.language_code}
                  />
                  {card.chart_usage_note && (
                    <p className="mt-2 text-xs text-gray-500">
                      {card.chart_usage_note}
                    </p>
                  )}
                  <p className="mt-2 text-[11px] text-gray-300">
                    {t('review.practiceModePeek')}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Answer bar (answering phase): just the arrow, Bunpro-style */}
        {session.phase === 'answering' && (
          <div className="space-y-2">
            <button
              type="button"
              aria-label={t('review.submitAnswer')}
              onClick={handleSubmitAnswer}
              disabled={!userInput.trim() || validateMutation.isPending}
              className="w-full bg-lang hover:bg-lang-dark text-lang-on disabled:opacity-40 rounded-2xl border-2 border-lang px-6 py-2 text-2xl leading-none transition-colors touch-manipulation"
              style={{ minHeight: '44px' }}
            >
              {validateMutation.isPending ? '…' : '→'}
            </button>
            {checkFailed && (
              <p className="text-sm text-red-600 text-center" role="alert">
                {t('review.checkFailed')}
              </p>
            )}
            {maxHint > 0 && (
              <button
                type="button"
                aria-label={t('review.showHint')}
                onClick={() => setHintLevel(hintLevel >= maxHint ? 0 : hintLevel + 1)}
                className="flex items-center gap-2 text-sm text-gray-500 hover:text-lang"
              >
                {t('review.hint')}
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
                title={t('review.listeningTitle')}
                className={`ms-auto text-sm rounded-full px-3 py-1 border transition ${
                  listening
                    ? 'border-lang/40 bg-lang-soft text-lang'
                    : 'border-lang-2-edge text-lang-2-label hover:bg-lang-2-tint'
                }`}
              >
                <Headphones aria-hidden className="me-1 inline h-3.5 w-3.5 align-[-2px]" />{listening ? t('review.listeningOn') : t('review.listeningOff')}
              </button>
            )}
            {/* Card escape hatches: defer without grading, or retire a card
                the learner genuinely already knows (graded reviews only —
                cram cards are synthetic and have nothing to retire). */}
            <div className="flex items-center justify-center gap-5 pt-1 text-xs text-gray-500">
              <button
                type="button"
                onClick={() => session.advance()}
                className="hover:text-lang"
                title={t('review.skipTitle')}
              >
                {t('review.skip')}
              </button>
              {!cram && (
                <button
                  type="button"
                  onClick={() => {
                    if (
                      window.confirm(
                        t('review.retireConfirm'),
                      )
                    )
                      knownMutation.mutate(card.id)
                  }}
                  disabled={knownMutation.isPending}
                  className="hover:text-lang disabled:opacity-50"
                  title={t('review.retireTitle')}
                >
                  {t('review.retire')}
                </button>
              )}
            </div>
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
                {showKeyboard ? t('review.hideKeyboard') : t('review.showKeyboard')}
              </button>
            </div>
            {showKeyboard && (
              <OnScreenKeyboard
                languageCode={card.language_code as KeyboardLanguage}
                onKeyPress={handleKeyboardKeyPress}
                onEnter={handleSubmitAnswer}
                onBackspace={handleKeyboardBackspace}
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
              {!cram && (
                <SuggestChange
                  languageId={activeLanguageId}
                  targetType={card.card_type === 'grammar' ? 'drill' : 'vocabulary'}
                  targetId={card.card_id}
                  targetLabel={card.sentence.replace('{{answer}}', card.correct_answer)}
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
                  <span className="flex items-center gap-1 text-gray-500">
                    <SpeakButton
                      text={completedSentence}
                      languageCode={card.language_code}
                      label={
                        completedSentence === card.correct_answer
                          ? t('review.hearAnswer', { word: card.correct_answer })
                          : t('review.hearFullSentence')
                      }
                    />
                    {/* Distinguish this from the word audio above — this speaker
                        plays the whole sentence, that one just the answer word. */}
                    {completedSentence !== card.correct_answer && (
                      <span className="text-[11px] tracking-wide">{t('review.sentenceTag')}</span>
                    )}
                  </span>
                  <span className="flex-1 text-center font-semibold">
                    {card.correct_answer}
                  </span>
                  <button
                    type="button"
                    aria-label={t('review.continue')}
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
                    className="text-xs text-gray-500 hover:text-lang"
                  >
                    <Undo2 aria-hidden className="me-0.5 inline h-3.5 w-3.5 align-[-2px]" />{t('review.undo')}
                  </button>
                  {(session.validationResult.answer_result === 'correct' ||
                    session.validationResult.answer_result === 'correct_sloppy') && (
                    <button
                      type="button"
                      onClick={() => handleRate('wrong')}
                      disabled={submitMutation.isPending}
                      className="text-xs text-gray-500 hover:text-red-500"
                    >
                      {t('review.gotItWrong')}
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
