import { useEffect, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getDashboardStats } from '../../api/dashboard'
import { getGymManifest } from '../../api/gym'
import {
  getDeckPreview,
  getLearnDecks,
  resetDeckProgress,
  setDeckSubscription,
} from '../../api/review'
import { getMyRoles } from '../../api/contribute'
import { getOnboardingStatus } from '../../api/onboarding'
import { getLanguages } from '../../api/profile'
import { lettersFor } from '../letters/lettersData'
import { usePrefsStore } from '../../stores/prefsStore'
import LanguagePicker from '../../components/LanguagePicker'
import CEFRProgress from './CEFRProgress'
import ForecastStrip from './ForecastStrip'
import ActivityChart from './ActivityChart'
import StageTiles from './StageTiles'
import ProfileCard from './ProfileCard'
import Walkthrough from '../onboarding/Walkthrough'
import InstallPrompt from '../../components/InstallPrompt'
import type { LearnDeck } from '../../api/types'

/** One Bunpro-style deck row. Two affordances, deliberately separated:
 * the Learn button STARTS learning from this deck (auto-adding it to the
 * queue if needed), and the chevron expands the deck's management panel —
 * add/remove from queue, reset, browse, and a peek at the contents. */
export function DeckRow({ deck, onLearn }: { deck: LearnDeck; onLearn: (d: LearnDeck) => void }) {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const pct = deck.total > 0 ? Math.round((deck.learned / deck.total) * 100) : 0
  const label = `${deck.level ?? 'All'} · ${deck.list_type === 'grammar' ? 'Grammar' : 'Vocab'}`
  const done = deck.total > 0 && deck.learned >= deck.total

  const subMutation = useMutation({
    mutationFn: (subscribed: boolean) => setDeckSubscription(deck.id, subscribed),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['learn-decks'] }),
  })

  const resetMutation = useMutation({
    mutationFn: () => resetDeckProgress(deck.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['learn-decks'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })

  const handleReset = () => {
    if (
      window.confirm(
        `Reset "${label}"? This permanently deletes your progress AND review history for the ${deck.total} items in this deck.`,
      )
    ) {
      resetMutation.mutate()
    }
  }

  const { data: preview, isLoading: previewLoading } = useQuery({
    queryKey: ['deck-preview', deck.id],
    queryFn: () => getDeckPreview(deck.id),
    enabled: open,
    staleTime: 5 * 60 * 1000,
  })

  return (
    <div className="border-t border-gray-100 first:border-t-0">
      <div className="w-full text-left px-4 py-3">
        <div className="flex items-center justify-between gap-3">
          <span className="text-sm font-medium text-gray-800">
            {label}
            {deck.subscribed && !done && (
              <span className="ml-2 text-[10px] uppercase tracking-wide bg-lang-soft text-lang rounded px-1.5 py-0.5 align-middle">
                In queue
              </span>
            )}
          </span>
          <span className="flex items-center gap-2">
            <span className="text-xs tabular-nums text-gray-500">
              {deck.learned} / {deck.total}
            </span>
            <button
              type="button"
              onClick={() => onLearn(deck)}
              disabled={done}
              title={done ? 'Deck complete' : 'Start learning from this deck'}
              className="rounded-lg bg-lang hover:bg-lang-dark disabled:opacity-40 text-lang-on text-xs font-semibold px-3 py-1.5"
            >
              Learn
            </button>
            <button
              type="button"
              onClick={() => setOpen((v) => !v)}
              aria-expanded={open}
              aria-label={`Deck options for ${label}`}
              title="Add to queue, reset, or browse this deck"
              className={`rounded-lg border px-2 py-1.5 text-xs transition-colors ${
                open
                  ? 'border-lang/40 bg-lang-soft text-lang'
                  : 'border-gray-200 text-gray-400 hover:text-lang hover:border-lang/40'
              }`}
            >
              <span
                aria-hidden
                className={`inline-block transition-transform ${open ? 'rotate-180' : ''}`}
              >
                ⌄
              </span>
            </button>
          </span>
        </div>
        <div className="mt-2 w-full bg-gray-100 rounded-full h-1.5">
          <div
            className={`h-1.5 rounded-full ${done ? 'bg-green-400' : 'bg-lang'}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        {open && (
          <div className="mt-3 space-y-3" data-testid="deck-options">
            <div className="flex flex-wrap items-center gap-4 text-xs">
              {deck.subscribed ? (
                <button
                  type="button"
                  onClick={() => subMutation.mutate(false)}
                  disabled={subMutation.isPending}
                  className="text-gray-500 hover:text-red-600"
                  title="Stops new cards from this deck. Cards you already learned keep their schedule."
                >
                  Remove from queue
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => subMutation.mutate(true)}
                  disabled={subMutation.isPending}
                  className="text-lang hover:underline font-medium"
                >
                  Add to queue
                </button>
              )}
              <Link to={`/decks/${deck.id}`} className="text-gray-500 hover:text-lang">
                Browse all items →
              </Link>
              {deck.learned > 0 && (
                <button
                  type="button"
                  onClick={handleReset}
                  disabled={resetMutation.isPending}
                  className="text-gray-400 hover:text-red-600"
                  title="Permanently deletes this deck's cards and their review history."
                >
                  Reset progress
                </button>
              )}
            </div>
            <div
              className="rounded-lg bg-gray-50 border border-gray-100 p-3 text-xs space-y-1"
              data-testid="deck-preview"
            >
              {previewLoading && <p className="text-gray-400">Loading…</p>}
              {preview?.items.map((it, i) => (
                <p key={i} className="text-gray-700">
                  <span className="font-medium">{it.item}</span>
                  {it.detail && <span className="text-gray-500"> — {it.detail}</span>}
                </p>
              ))}
              {preview && preview.items.length === 0 && (
                <p className="text-gray-400">This deck is empty.</p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function SkeletonCard() {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 flex flex-col items-center gap-2 animate-pulse">
      <div className="h-12 w-16 bg-gray-200 rounded" />
      <div className="h-4 w-24 bg-gray-100 rounded" />
    </div>
  )
}

export default function DashboardPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)
  const walkthroughDone = usePrefsStore((s) => s.walkthroughDone)
  const dailyLearnGoal = usePrefsStore((s) => s.dailyLearnGoal)
  const [learnOpen, setLearnOpen] = useState(false)
  const [reviewOpen, setReviewOpen] = useState(false)
  const [showTour, setShowTour] = useState(false)

  // Open the feature tour once, for someone who hasn't dismissed it.
  useEffect(() => {
    if (!walkthroughDone) setShowTour(true)
  }, [walkthroughDone])

  // First-run users are routed into onboarding before they can study.
  const { data: onboarding, isLoading: onboardingLoading } = useQuery({
    queryKey: ['onboarding-status'],
    queryFn: getOnboardingStatus,
  })

  // Active language CODE (for the Letters & Sounds gate) — shares the
  // cached languages query with LanguagePicker.
  const { data: allLanguages = [] } = useQuery({
    queryKey: ['languages'],
    queryFn: getLanguages,
  })
  const activeLanguageCode = allLanguages.find(
    (l) => l.id === activeLanguageId,
  )?.code
  const hasLetters = !!lettersFor(activeLanguageCode)

  // The Gym tile shows only when this language has form categories to
  // train (empty manifest = uninflected language, no tile).
  const { data: gymManifest } = useQuery({
    queryKey: ['gym-manifest', activeLanguageId],
    queryFn: () => getGymManifest(activeLanguageId!),
    enabled: !!activeLanguageId,
    retry: false,
  })
  const hasGym = (gymManifest?.columns.length ?? 0) > 0

  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard', activeLanguageId],
    queryFn: () => getDashboardStats(activeLanguageId!),
    enabled: !!activeLanguageId,
  })

  // Bunpro-style learn decks: per-level sections with progress.
  const { data: decks = [] } = useQuery({
    queryKey: ['learn-decks', activeLanguageId],
    queryFn: () => getLearnDecks(activeLanguageId!),
    enabled: !!activeLanguageId,
  })
  const visibleDecks = decks.filter((d) => d.total > 0)
  // Learn only counts what the learner actually QUEUED — a deck they haven't
  // added shouldn't inflate "new items available".
  const newAvailable = visibleDecks
    .filter((d) => d.subscribed)
    .reduce((sum, d) => sum + Math.max(d.total - d.learned, 0), 0)

  // Surfaces the Contribute link only to users who hold a contributor role.
  const { data: roleInfo } = useQuery({
    queryKey: ['my-roles'],
    queryFn: getMyRoles,
    retry: false,
  })
  const canContribute = (roleInfo?.roles?.length ?? 0) > 0

  // Learning routes through /learn, which TEACHES the new items (lesson
  // pages) before they are ever quizzed. Deck rows scope the batch to one
  // level; the plain buttons draw from everything queued.
  const handleLearnDeck = async (deck: LearnDeck) => {
    if (!activeLanguageId) return
    // Learn batches only draw from subscribed decks — clicking Learn on an
    // unqueued deck adds it first, so Learn always just works. Queue
    // control without starting lives in the row's expansion panel.
    if (!deck.subscribed) {
      try {
        await setDeckSubscription(deck.id, true)
        queryClient.invalidateQueries({ queryKey: ['learn-decks'] })
      } catch {
        return // surface nothing scarier than a no-op; the row still works
      }
    }
    const levelParam = deck.level ? `&level=${encodeURIComponent(deck.level)}` : ''
    navigate(`/learn?type=${deck.list_type}${levelParam}`)
  }

  const handleReview = () => {
    navigate('/review')
  }

  // The Learn tile STARTS a session — the next queued deck with items left,
  // in deck order (Bunpro's learn-queue behavior). With nothing queued it
  // opens the deck panel instead, so the learner can add one.
  const handleLearnStart = () => {
    const next = visibleDecks.find((d) => d.subscribed && d.learned < d.total)
    if (next) {
      void handleLearnDeck(next)
    } else {
      setLearnOpen(true)
    }
  }

  if (!onboardingLoading && onboarding && !onboarding.onboarded) {
    return <Navigate to="/onboarding" replace />
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <div className="flex items-center gap-4">
            <button
              type="button"
              onClick={() => navigate('/decks')}
              aria-label="Decks"
              className="text-sm text-gray-500 hover:text-lang"
            >
              Decks
            </button>
            <button
              type="button"
              onClick={() => navigate('/tutor')}
              aria-label="Tutor"
              className="text-sm text-gray-500 hover:text-lang"
            >
              Tutor
            </button>
            <button
              type="button"
              onClick={() => navigate('/read')}
              aria-label="Read"
              className="text-sm text-gray-500 hover:text-lang"
            >
              Read
            </button>
            <button
              type="button"
              onClick={() => navigate('/search')}
              aria-label="Search"
              className="text-sm text-gray-500 hover:text-lang"
            >
              Search
            </button>
            <button
              type="button"
              onClick={() => navigate('/account')}
              aria-label="Account"
              className="text-sm text-gray-500 hover:text-lang"
            >
              Account
            </button>
            <button
              type="button"
              onClick={() => setShowTour(true)}
              aria-label="Take the feature tour"
              title="Take the tour"
              className="text-sm text-gray-400 hover:text-lang"
            >
              ?
            </button>
          </div>
        </div>

        {showTour && <Walkthrough onClose={() => setShowTour(false)} />}

        <InstallPrompt />

        {/* Language picker */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Active Language
          </label>
          <LanguagePicker />
        </div>

        {/* Letters & Sounds (beta request): the alphabet with pronunciation,
            right under the language and before the study tiles. Hidden for
            languages with no letter guide. */}
        {hasLetters && (
          <button
            type="button"
            onClick={() => navigate('/letters')}
            disabled={!activeLanguageId}
            className="w-full bg-white hover:bg-gray-50 disabled:opacity-50 text-gray-800 font-semibold rounded-xl px-6 py-3 text-sm border border-gray-200 transition-colors text-left flex items-center justify-between"
            style={{ minHeight: '44px' }}
          >
            <span>
              Letters &amp; Sounds
              <span className="block text-xs font-normal text-gray-500">
                Every letter, its variants, and how to say them
              </span>
            </span>
            <span aria-hidden className="text-lang">→</span>
          </button>
        )}

        {/* The Gym (WP25): only for languages with forms to train. */}
        {hasGym && (
          <button
            type="button"
            onClick={() => navigate('/gym')}
            className="w-full bg-white hover:bg-gray-50 text-gray-800 font-semibold rounded-xl px-6 py-3 text-sm border border-gray-200 transition-colors text-left flex items-center justify-between"
            style={{ minHeight: '44px' }}
          >
            <span>
              The Gym
              <span className="block text-xs font-normal text-gray-500">
                Pick a tense or case and drill it — conjugations, declensions, reps
              </span>
            </span>
            <span aria-hidden className="text-lang">→</span>
          </button>
        )}

        {/* Command center: Learn (deck sections) + Review, Bunpro-style */}
        {isLoading || !stats ? (
          <div className="grid grid-cols-2 gap-4">
            <SkeletonCard />
            <SkeletonCard />
          </div>
        ) : (
          <div className="space-y-3">
            {/* Bunpro-style tiles: the big button STARTS the session, the
                chevron beside it expands options (decks / type filters). */}
            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-2xl bg-lang-dark text-white p-3 flex items-stretch gap-2">
                <button
                  type="button"
                  onClick={handleLearnStart}
                  disabled={!activeLanguageId}
                  title="Start learning new items from your queue"
                  className="flex-1 min-w-0 text-left rounded-xl hover:bg-white/10 disabled:opacity-50 p-2 transition-colors"
                  style={{ minHeight: '44px' }}
                >
                  <span className="block text-sm font-semibold uppercase tracking-wide text-white/70">
                    Learn
                  </span>
                  {/* Daily goal framing (beta request): "538 queued" was
                      overwhelming — show progress toward a small daily
                      target instead. Goal 0 = the old full-queue count. */}
                  {dailyLearnGoal > 0 ? (
                    <>
                      <span className="block text-3xl font-bold mt-1">
                        {Math.min(stats.learned_today, dailyLearnGoal)} / {dailyLearnGoal}
                      </span>
                      <span className="block text-xs text-white/60 mt-1">
                        {stats.learned_today >= dailyLearnGoal
                          ? `daily goal done · ${newAvailable} queued`
                          : `learned today · ${newAvailable} queued`}
                      </span>
                    </>
                  ) : (
                    <>
                      <span className="block text-3xl font-bold mt-1">{newAvailable}</span>
                      <span className="block text-xs text-white/60 mt-1">new items queued</span>
                    </>
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => setLearnOpen((v) => !v)}
                  aria-expanded={learnOpen}
                  aria-label="Learn queue decks"
                  title="Choose and manage your learn decks"
                  className={`self-center rounded-xl border border-white/25 px-2.5 py-2 text-sm transition-colors ${
                    learnOpen ? 'bg-white/20' : 'hover:bg-white/10'
                  }`}
                  style={{ minHeight: '44px' }}
                >
                  <span
                    aria-hidden
                    className={`inline-block transition-transform ${learnOpen ? 'rotate-180' : ''}`}
                  >
                    ⌄
                  </span>
                </button>
              </div>
              <div className="rounded-2xl bg-lang text-lang-on p-3 flex items-stretch gap-2">
                <button
                  type="button"
                  onClick={handleReview}
                  disabled={stats.due_count === 0}
                  title="Review everything that's due"
                  className="flex-1 min-w-0 text-left rounded-xl hover:bg-black/10 disabled:opacity-50 p-2 transition-colors"
                  style={{ minHeight: '44px' }}
                >
                  <span className="block text-sm font-semibold uppercase tracking-wide text-lang-on/70">
                    Review
                  </span>
                  <span className="block text-3xl font-bold mt-1">{stats.due_count}</span>
                  <span className="block text-xs text-lang-on/70 mt-1">all reviews</span>
                </button>
                <button
                  type="button"
                  onClick={() => setReviewOpen((v) => !v)}
                  aria-expanded={reviewOpen}
                  aria-label="Review options"
                  title="Grammar-only or vocab-only reviews"
                  className={`self-center rounded-xl border border-lang-on/25 px-2.5 py-2 text-sm transition-colors ${
                    reviewOpen ? 'bg-black/15' : 'hover:bg-black/10'
                  }`}
                  style={{ minHeight: '44px' }}
                >
                  <span
                    aria-hidden
                    className={`inline-block transition-transform ${reviewOpen ? 'rotate-180' : ''}`}
                  >
                    ⌄
                  </span>
                </button>
              </div>
            </div>

            {/* Deck sections (like Bunpro's Learn Queue Decks) */}
            {learnOpen && (
              <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
                {visibleDecks.length === 0 ? (
                  <p className="px-4 py-3 text-sm text-gray-500">
                    No decks for this language yet.
                  </p>
                ) : (
                  visibleDecks.map((deck) => (
                    <DeckRow key={deck.id} deck={deck} onLearn={handleLearnDeck} />
                  ))
                )}
              </div>
            )}

            {/* Review type filters (like Bunpro's Grammar Only / Vocab Only) */}
            {reviewOpen && (
              <div
                className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden"
                data-testid="review-options"
              >
                {(
                  [
                    { label: 'Grammar Only', count: stats.due_grammar ?? 0, type: 'grammar' },
                    { label: 'Vocab Only', count: stats.due_vocab ?? 0, type: 'vocabulary' },
                  ] as const
                ).map((row) => (
                  <button
                    key={row.type}
                    type="button"
                    onClick={() => navigate(`/review?type=${row.type}`)}
                    disabled={row.count === 0}
                    className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-gray-800 hover:bg-gray-50 disabled:opacity-40 border-t border-gray-100 first:border-t-0"
                    style={{ minHeight: '44px' }}
                  >
                    <span>{row.label}</span>
                    <span className="tabular-nums text-xs bg-lang-soft text-lang rounded-lg px-2.5 py-1">
                      {row.count}
                    </span>
                  </button>
                ))}
              </div>
            )}

            {stats.forecast && <ForecastStrip forecast={stats.forecast} />}
            {stats.activity && <ActivityChart activity={stats.activity} />}
            {stats.stages && <StageTiles stages={stats.stages} />}
            {stats.profile && (
              <ProfileCard profile={stats.profile} streakDays={stats.streak_days} />
            )}
          </div>
        )}

        {/* CEFR Progress */}
        {isLoading || !stats ? (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 animate-pulse">
            <div className="h-4 w-28 bg-gray-200 rounded mb-4" />
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="flex items-center gap-3 mb-3">
                <div className="w-7 h-3 bg-gray-100 rounded" />
                <div className="flex-1 h-2 bg-gray-100 rounded-full" />
                <div className="w-9 h-3 bg-gray-100 rounded" />
              </div>
            ))}
          </div>
        ) : (
          <CEFRProgress progress={stats.cefr_progress} />
        )}

        {/* Grammar path */}
        <button
          type="button"
          onClick={() => navigate('/grammar')}
          disabled={!activeLanguageId}
          className="w-full bg-white hover:bg-gray-50 disabled:opacity-50 text-gray-800 font-semibold rounded-xl px-6 py-3 text-sm border border-gray-200 transition-colors text-left flex items-center justify-between"
          style={{ minHeight: '44px' }}
        >
          <span>
            Grammar path
            <span className="block text-xs font-normal text-gray-500">
              Browse and read every grammar point in order
            </span>
          </span>
          <span aria-hidden className="text-lang">→</span>
        </button>

        {/* AI Tutor */}
        <button
          type="button"
          onClick={() => navigate('/tutor')}
          disabled={!activeLanguageId}
          className="w-full bg-white hover:bg-gray-50 disabled:opacity-50 text-gray-800 font-semibold rounded-xl px-6 py-3 text-sm border border-gray-200 transition-colors text-left flex items-center justify-between"
          style={{ minHeight: '44px' }}
        >
          <span>
            Practice with AI Tutor
            <span className="block text-xs font-normal text-gray-500">
              Coaching on the words you keep missing
            </span>
          </span>
          <span aria-hidden className="text-lang">→</span>
        </button>

        {/* The Reader (WP21) */}
        <button
          type="button"
          onClick={() => navigate('/read')}
          disabled={!activeLanguageId}
          className="w-full bg-white hover:bg-gray-50 disabled:opacity-50 text-gray-800 font-semibold rounded-xl px-6 py-3 text-sm border border-gray-200 transition-colors text-left flex items-center justify-between"
          style={{ minHeight: '44px' }}
        >
          <span>
            Read about anything
            <span className="block text-xs font-normal text-gray-500">
              A text written at your level, on your topic
            </span>
          </span>
          <span aria-hidden className="text-lang">→</span>
        </button>

        {/* Learn from your own text */}
        <button
          type="button"
          onClick={() => navigate('/notes')}
          disabled={!activeLanguageId}
          className="w-full bg-white hover:bg-gray-50 disabled:opacity-50 text-gray-800 font-semibold rounded-xl px-6 py-3 text-sm border border-gray-200 transition-colors text-left flex items-center justify-between"
          style={{ minHeight: '44px' }}
        >
          <span>
            Learn from your own text
            <span className="block text-xs font-normal text-gray-500">
              Turn anything you read into review cards
            </span>
          </span>
          <span aria-hidden className="text-lang">→</span>
        </button>

        {/* Contributor link — only for users with a role */}
        {canContribute && (
          <button
            type="button"
            onClick={() => navigate('/contribute')}
            className="w-full text-sm text-gray-500 hover:text-lang hover:underline text-left"
          >
            Contribute grammar notes →
          </button>
        )}
      </div>
    </div>
  )
}
