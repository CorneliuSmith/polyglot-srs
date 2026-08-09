import { useEffect, useState } from 'react'
import { Bell, CircleUserRound, Clapperboard, Menu } from 'lucide-react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
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
import { usePrefsStore } from '../../stores/prefsStore'
import LanguagePicker from '../../components/LanguagePicker'
import UiLanguageSwitcher from '../../components/UiLanguageSwitcher'
import Walkthrough from '../onboarding/Walkthrough'
import PlacementOffer from '../onboarding/PlacementOffer'
import ReviewPromptGate from './ReviewPromptGate'
import WhatsNewPanel from '../announcements/WhatsNewPanel'
import { unseenWhatsNew } from '../announcements/whatsNew'
import DesktopRail from './DesktopRail'
import SectionNav from '../../components/SectionNav'
import InstallPrompt from '../../components/InstallPrompt'
import LearningTip from '../tips/LearningTip'
import FeedbackAlert from '../feedback/FeedbackAlert'
import type { LearnDeck } from '../../api/types'
import { useViewAsKey } from '../../stores/viewAsStore'

/** A first-class practice-destination tile (Gym / Read / Tutor). Users have
 * shown they don't read buried link lists — these sit right under the
 * Learn/Review command center with the same visual weight, so the features
 * are discovered by SEEING them. */
/** Letters & Sounds and Things to Know: the reference pair, above Learn
 * and Review. They were plain white rows with a grey border, which read as
 * secondary chrome next to the coloured study tiles — easy to scroll past
 * on the screen where a new learner most needs them. Tinted with the
 * language's own accent so the top of the dashboard is one family: soft
 * here for reference, solid below for the thing you came to do.
 *
 * bg-lang-soft is theme-safe by construction — index.css maps it through
 * --lang-soft-surface, which `.dark` overrides so the pastel doesn't glare.
 */
/** One Bunpro-style deck row. Two affordances, deliberately separated:
 * the Learn button STARTS learning from this deck (auto-adding it to the
 * queue if needed), and the chevron expands the deck's management panel —
 * add/remove from queue, reset, browse, and a peek at the contents. */
export function DeckRow({ deck, onLearn }: { deck: LearnDeck; onLearn: (d: LearnDeck) => void }) {
  const queryClient = useQueryClient()
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const pct = deck.total > 0 ? Math.round((deck.learned / deck.total) * 100) : 0
  const label = `${deck.level ?? t('dashboard.allLevel')} · ${deck.list_type === 'grammar' ? t('common.grammar') : t('common.vocab')}`
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
        t('dashboard.resetConfirm', { label, count: deck.total }),
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
      <div className="w-full text-start px-4 py-3">
        <div className="flex items-center justify-between gap-3">
          <span className="text-sm font-medium text-gray-800">
            {label}
            {deck.subscribed && !done && (
              <span className="ms-2 text-[10px] uppercase tracking-wide bg-lang-soft text-lang rounded px-1.5 py-0.5 align-middle">
                {t('dashboard.inQueue')}
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
              title={done ? t('dashboard.deckComplete') : t('dashboard.startLearningDeck')}
              className="rounded-lg bg-lang hover:bg-lang-dark disabled:opacity-40 text-lang-on text-xs font-semibold px-3 py-1.5"
            >
              {t('dashboard.deckLearn')}
            </button>
            <button
              type="button"
              onClick={() => setOpen((v) => !v)}
              aria-expanded={open}
              aria-label={t('dashboard.deckOptionsFor', { label })}
              title={t('dashboard.deckOptionsHint')}
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
                  title={t('dashboard.removeFromQueueHint')}
                >
                  {t('dashboard.removeFromQueue')}
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => subMutation.mutate(true)}
                  disabled={subMutation.isPending}
                  className="text-lang hover:underline font-medium"
                >
                  {t('dashboard.addToQueue')}
                </button>
              )}
              <Link to={`/decks/${deck.id}`} className="text-gray-500 hover:text-lang">
                {t('dashboard.browseAll')}
              </Link>
              {deck.learned > 0 && (
                <button
                  type="button"
                  onClick={handleReset}
                  disabled={resetMutation.isPending}
                  className="text-gray-400 hover:text-red-600"
                  title={t('dashboard.resetProgressHint')}
                >
                  {t('dashboard.resetProgress')}
                </button>
              )}
            </div>
            <div
              className="rounded-lg bg-gray-50 border border-gray-100 p-3 text-xs space-y-1"
              data-testid="deck-preview"
            >
              {previewLoading && <p className="text-gray-400">{t('common.loading')}</p>}
              {preview?.items.map((it, i) => (
                <p key={i} className="text-gray-700">
                  <span className="font-medium">{it.item}</span>
                  {it.detail && <span className="text-gray-500"> — {it.detail}</span>}
                </p>
              ))}
              {preview && preview.items.length === 0 && (
                <p className="text-gray-400">{t('dashboard.deckEmpty')}</p>
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
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)
  const walkthroughDone = usePrefsStore((s) => s.walkthroughDone)
  const dailyLearnGoal = usePrefsStore((s) => s.dailyLearnGoal)
  const [learnOpen, setLearnOpen] = useState(false)
  const [reviewOpen, setReviewOpen] = useState(false)
  const [navOpen, setNavOpen] = useState(false)
  const [showTour, setShowTour] = useState(false)
  const [showWhatsNew, setShowWhatsNew] = useState(false)
  const whatsNewSeen = usePrefsStore((s) => s.whatsNewSeen)
  const unseenCount = unseenWhatsNew(whatsNewSeen).length

  // Open the feature tour once, for someone who hasn't dismissed it.
  useEffect(() => {
    if (!walkthroughDone) setShowTour(true)
  }, [walkthroughDone])

  // First-run users are routed into onboarding before they can study.
  const { data: onboarding, isLoading: onboardingLoading } = useQuery({
    queryKey: ['onboarding-status'],
    queryFn: getOnboardingStatus,
  })


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
    queryKey: ['my-roles', useViewAsKey()],
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

  // The Learn tile STARTS a session drawing from the WHOLE queue: it goes
  // unscoped (no level), so the backend round-robins new items across every
  // subscribed deck of that type — all queued decks advance together instead
  // of the lowest level draining first. The type is taken from the next
  // queued deck with items left; deck rows still learn one specific deck via
  // handleLearnDeck. With nothing queued it opens the deck panel to add one.
  const handleLearnStart = () => {
    const queued = visibleDecks.filter((d) => d.subscribed && d.learned < d.total)
    if (queued.length === 0) {
      setLearnOpen(true)
      return
    }
    // With both grammar and vocab queued, interleave them in one session;
    // otherwise learn the one type that has items left.
    const hasGrammar = queued.some((d) => d.list_type === 'grammar')
    const hasVocab = queued.some((d) => d.list_type === 'vocabulary')
    const type = hasGrammar && hasVocab ? 'both' : queued[0].list_type
    navigate(`/learn?type=${type}`)
  }

  if (!onboardingLoading && onboarding && !onboarding.onboarded) {
    return <Navigate to="/onboarding" replace />
  }

  // Top-level destinations. Rendered inline on desktop and inside a collapsible
  // menu on phones, where a single row of them overflowed the viewport.
  const navItems: { label: string; to: string }[] = [
    { label: t('nav.decks'), to: '/decks' },
    { label: t('nav.tutor'), to: '/tutor' },
    { label: t('nav.read'), to: '/read' },
    ...(hasGym ? [{ label: t('nav.gym'), to: '/gym' }] : []),
    { label: t('nav.search'), to: '/search' },
    { label: t('nav.account'), to: '/account' },
  ]

  return (
    <div className="min-h-screen bg-gray-50 overflow-x-hidden">
      {/* Occasional forced-feedback nudge for trial reviewers (self-gates:
          renders nothing unless one is due). */}
      <ReviewPromptGate />
      {/* First time in this language? Offer to place them (self-gates on the
          server's per-language attempt history). */}
      <PlacementOffer languageId={activeLanguageId} />
      {/* Narrow on a phone, wider once there is a second column to hold.
          The reading measure of the loop itself doesn't change — the extra
          width goes to the rail, not to stretching the tiles. */}
      <div className="max-w-2xl lg:max-w-5xl mx-auto px-4 py-8 space-y-6 pb-24 md:pb-8">
        {/* Header. On phones the full row of destinations overflowed the
            viewport (the source of the "shaky", clipped layout), so the
            nav links collapse behind a menu button below md and only the
            title + utility icons stay on the bar. */}
        <div className="flex items-center justify-between gap-2">
          <h1 className="text-2xl font-bold text-gray-900">{t('nav.study')}</h1>
          <div className="flex items-center gap-3 sm:gap-4">
            {/* Desktop section nav. The individual destinations that used
                to sit here (Decks, Tutor, Read…) live inside these four
                sections, exactly as they do on a phone — and unlike that
                row, this one can actually reach Practice, Progress and
                More, which desktop previously could not open at all. */}
            <SectionNav />
            {/* Utility cluster, set apart from navigation: announcements
                and the tour are ABOUT the app, not places in it. */}
            <span aria-hidden className="hidden md:block h-4 w-px bg-gray-200" />
            {/* Account as a one-tap symbol (owner): it was reachable only
                through the mobile menu or the More section — the last
                text-only destination while everything else got an icon. */}
            <button
              type="button"
              data-testid="header-account"
              onClick={() => navigate('/account')}
              aria-label={t('nav.account')}
              title={t('nav.account')}
              className="w-9 h-9 md:w-7 md:h-7 flex items-center justify-center rounded-full border border-gray-200 text-gray-400 hover:text-lang hover:border-lang/40"
            >
              <CircleUserRound aria-hidden className="h-4 w-4 md:h-3.5 md:w-3.5" />
            </button>
            <UiLanguageSwitcher />
            <button
              type="button"
              onClick={() => setShowWhatsNew(true)}
              aria-label={t('header.whatsNew')}
              title={t('header.whatsNew')}
              className="relative w-9 h-9 md:w-7 md:h-7 flex items-center justify-center rounded-full border border-gray-200 text-gray-400 hover:text-lang hover:border-lang/40 text-sm md:text-xs leading-none"
            >
              <Bell aria-hidden className="h-4 w-4 md:h-3.5 md:w-3.5" />
              {unseenCount > 0 && (
                <span
                  data-testid="whats-new-badge"
                  className="absolute -top-1.5 -end-1.5 min-w-4 h-4 rounded-full bg-lang text-white text-[10px] font-bold leading-4 text-center px-0.5"
                >
                  {unseenCount}
                </span>
              )}
            </button>
            <button
              type="button"
              onClick={() => setShowTour(true)}
              aria-label={t('header.takeTour')}
              title={t('header.takeTour')}
              className="w-9 h-9 md:w-7 md:h-7 flex items-center justify-center rounded-full border border-gray-200 text-gray-400 hover:text-lang hover:border-lang/40 text-sm md:text-xs leading-none"
            >
              ?
            </button>
            {/* Mobile-only menu toggle for the destinations above */}
            <button
              type="button"
              onClick={() => setNavOpen((v) => !v)}
              aria-label={t('nav.menu')}
              aria-expanded={navOpen}
              title={t('nav.menu')}
              className={`md:hidden w-9 h-9 flex items-center justify-center rounded-full border text-base leading-none transition-colors ${
                navOpen
                  ? 'border-lang/40 bg-lang-soft text-lang'
                  : 'border-gray-200 text-gray-500 hover:text-lang hover:border-lang/40'
              }`}
            >
              <Menu aria-hidden className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Mobile nav dropdown */}
        {navOpen && (
          <nav className="md:hidden bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
            {navItems.map((item) => (
              <button
                key={item.to}
                type="button"
                onClick={() => {
                  setNavOpen(false)
                  navigate(item.to)
                }}
                className="w-full text-start px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 border-t border-gray-100 first:border-t-0"
                style={{ minHeight: '44px' }}
              >
                {item.label}
              </button>
            ))}
          </nav>
        )}

        {showTour && <Walkthrough onClose={() => setShowTour(false)} />}
        {showWhatsNew && <WhatsNewPanel onClose={() => setShowWhatsNew(false)} />}

        <InstallPrompt />

        {/* Two columns from lg up: the daily loop keeps the left, and the
            things a learner reaches for next sit beside it instead of
            behind a tab. One column below that, unchanged. */}
        <div className="lg:grid lg:grid-cols-[minmax(0,1fr)_18rem] lg:gap-6 lg:items-start">
        <div className="space-y-6">
        {/* The STUDY language. A deliberate, infrequent choice, and legible
            by definition — so it stays here as a labelled control rather
            than following the learner around. The globe in the header is
            the interface language, which is a different thing entirely. */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            {t('dashboard.activeLanguage')}
          </label>
          <LanguagePicker />
        </div>

        {/* Learning tip (throttled to ~once a day; off in Settings) */}
        {/* Staff only: something came in and nobody has closed it out. */}
        <FeedbackAlert canSeeQueue={canContribute} />

        <LearningTip context="dashboard" />

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
                  title={t('dashboard.learnStartHint')}
                  className="flex-1 min-w-0 text-start rounded-xl hover:bg-white/10 disabled:opacity-50 p-2 transition-colors"
                  style={{ minHeight: '44px' }}
                >
                  <span className="block text-sm font-semibold uppercase tracking-wide text-white/70">
                    {t('dashboard.learn')}
                  </span>
                  {/* Daily goal framing (beta request): "538 queued" was
                      overwhelming — show progress toward a small daily
                      target instead. Goal 0 = the old full-queue count. */}
                  {dailyLearnGoal > 0 ? (
                    <>
                      {/* Overflow shows honestly — 21 / 20, not a clamped
                          20 / 20 (owner request): going past the goal is
                          worth seeing. */}
                      <span className="block text-3xl font-bold mt-1">
                        {stats.learned_today} / {dailyLearnGoal}
                      </span>
                      <span className="block text-xs text-white/60 mt-1">
                        {stats.learned_today >= dailyLearnGoal
                          ? t('dashboard.goalDoneQueued', { count: newAvailable })
                          : t('dashboard.learnedTodayQueued', { count: newAvailable })}
                      </span>
                    </>
                  ) : (
                    <>
                      <span className="block text-3xl font-bold mt-1">{newAvailable}</span>
                      <span className="block text-xs text-white/60 mt-1">{t('dashboard.newQueued')}</span>
                    </>
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => setLearnOpen((v) => !v)}
                  aria-expanded={learnOpen}
                  aria-label={t('dashboard.learnDecksAria')}
                  title={t('dashboard.learnDecksHint')}
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
                  title={t('dashboard.reviewAllHint')}
                  className="flex-1 min-w-0 text-start rounded-xl hover:bg-black/10 disabled:opacity-50 p-2 transition-colors"
                  style={{ minHeight: '44px' }}
                >
                  <span className="block text-sm font-semibold uppercase tracking-wide text-lang-on/70">
                    {t('dashboard.review')}
                  </span>
                  <span className="block text-3xl font-bold mt-1">{stats.due_count}</span>
                  <span className="block text-xs text-lang-on/70 mt-1">{t('dashboard.allReviews')}</span>
                </button>
                <button
                  type="button"
                  onClick={() => setReviewOpen((v) => !v)}
                  aria-expanded={reviewOpen}
                  aria-label={t('dashboard.reviewOptionsAria')}
                  title={t('dashboard.reviewOptionsHint')}
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
                    {t('dashboard.noDecks')}
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
                    { label: t('dashboard.grammarOnly'), count: stats.due_grammar ?? 0, type: 'grammar' },
                    { label: t('dashboard.vocabOnly'), count: stats.due_vocab ?? 0, type: 'vocabulary' },
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

          </div>
        )}

        {/* Weekly picks — its own card, NOT filed under Practice (owner:
            "it is not a part of practice"). Below lg only; desktop has the
            rail's own Recommended card. */}
        <button
          type="button"
          data-testid="reco-card"
          onClick={() => navigate('/recommendations')}
          className="lg:hidden w-full bg-white hover:bg-gray-50 rounded-2xl px-4 py-3 border border-gray-200 shadow-sm text-start flex items-center gap-3"
          style={{ minHeight: '44px' }}
        >
          <span className="shrink-0 rounded-xl bg-lang/10 p-2">
            <Clapperboard aria-hidden className="h-5 w-5 text-lang" strokeWidth={1.75} />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block text-sm font-semibold text-gray-800">
              {t('dashboard.recommendedTitle')}
            </span>
            <span className="block text-xs text-gray-500">
              {t('dashboard.recommendedSub')}
            </span>
          </span>
        </button>
        </div>

        <DesktopRail stats={stats} />
        </div>

      </div>
    </div>
  )
}
