import { useState } from 'react'
import { Trans, useTranslation } from 'react-i18next'
import UiLanguageSwitcher from '../../components/UiLanguageSwitcher'
import { useLocation, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getLanguages, getProfile, updateProfile } from '../../api/profile'
import { getLearnDecks, resetProgress } from '../../api/review'
import { getPlacementHistory, setLearnerLevel } from '../../api/onboarding'
import PlacementTest from '../onboarding/PlacementTest'
import {
  formatPrice,
  getPlanPrices,
  openBillingPortal,
  startPlanCheckout,
} from '../../api/billing'
import { getDashboardStats } from '../../api/dashboard'
import { getTutorStatus } from '../../api/tutor'
import UsageMeter from '../../components/UsageMeter'
import { usePrefsStore } from '../../stores/prefsStore'
import type { Theme } from '../../stores/prefsStore'
import AppearanceTrial from './AppearanceTrial'
import { hasTranslit } from '../keyboards/translit'
import RecoSettings from '../recommendations/RecoSettings'
import TutorMemoryPanel from './TutorMemoryPanel'
import { supabase } from '../../lib/supabase'
import LanguagePicker from '../../components/LanguagePicker'
import LanguageWrapper from '../../components/LanguageWrapper'
import { getGrammarForLanguage, getMyRoles } from '../../api/contribute'
import {
  canContributeWith,
  canReviewWith,
  canTrialReviewWith,
} from '../../lib/roleFlags'
import { accentExampleFor } from '../../lib/accentExamples'
import { languageDisplayName } from '../../lib/languages'
import { useViewAsKey } from '../../stores/viewAsStore'
import AccountsPanel from '../contribute/AccountsPanel'
import PlanLimitsPanel from '../contribute/PlanLimitsPanel'
import RoleGuide from '../contribute/RoleGuide'
import FeedbackQueuePanel from '../contribute/FeedbackQueuePanel'
import InvitePanel from '../contribute/InvitePanel'
import MyFeedback from '../feedback/MyFeedback'
import GenerationPanel from '../contribute/GenerationPanel'
import LanguageVisibilityPanel from '../contribute/LanguageVisibilityPanel'
import RolesPanel from '../contribute/RolesPanel'
import ReviewQueue from '../contribute/ReviewQueue'
import AnalyticsPanel from '../contribute/AnalyticsPanel'
import EngagementPanel from '../contribute/EngagementPanel'
import {
  ReviewPolicyControl,
  TutorModelControl,
  TutorCostsPanel,
} from '../contribute/ContributorPage'
import { useAuthStore } from '../../stores/authStore'
import { CARD_COLUMNS, PAGE_WIDE } from '../../lib/layout'

type AccountTab = 'learner' | 'contribute' | 'review' | 'invite' | 'admin'

// Tab labels live in the catalog as settings.tabs.<key>. Ambassadors get
// their own "Invite" tab rather than a cut-down "Admin" one: calling it
// Admin for someone who can do exactly one admin thing misdescribes both
// the tab and the role.

/** The tabs an account can actually reach.
 *
 * One question per tab, because the roles are not a ladder (see lib/viewAs.ts):
 *
 *   Contribute — canContribute. NOT admin-only; gating it on
 *     `canReview || isAdmin` once hid it from every plain contributor and left
 *     them no route to their own panel.
 *   Review — canReview OR canTrialReview. Asking only canReview left trial
 *     reviewers with nothing but the Learner tab, so the queue they exist to
 *     work was unreachable and their guide panel rendered in a tab they could
 *     not open. Publishing stays gated separately: ReviewQueue takes
 *     canReview, so a trial reviewer sees the queue and recommends on it
 *     without being able to publish.
 *   Admin — isAdmin. */
export function accountTabsFor(flags: {
  canContribute: boolean
  canReview: boolean
  canTrialReview?: boolean
  canAddAccounts?: boolean
  isAdmin: boolean
}): AccountTab[] {
  return [
    'learner' as const,
    ...(flags.canContribute ? (['contribute'] as const) : []),
    ...(flags.canReview || flags.canTrialReview
      ? (['review'] as const)
      : []),
    // Admins reach account creation through Admin, which has the full
    // panel; Invite is for the ambassador who has only this one power.
    ...(flags.canAddAccounts && !flags.isAdmin ? (['invite'] as const) : []),
    ...(flags.isAdmin ? (['admin'] as const) : []),
  ]
}

/** The tab to actually render. The available set SHRINKS when an admin starts
 * a "view as" preview, and a selection pointing at a tab that no longer
 * exists rendered a completely blank page — every panel is gated on an exact
 * match, so 'admin' under a Reviewer preview matched nothing. */
export function resolveTab(
  selected: AccountTab,
  available: AccountTab[],
): AccountTab {
  return available.includes(selected) ? selected : 'learner'
}

// Reminder hours are stored in UTC; the picker shows the learner's local
// hour. Rounded whole-hour conversion (half-hour zones shift by ≤30 min).
export function utcToLocalHour(utc: number): number {
  const offset = Math.round(-new Date().getTimezoneOffset() / 60)
  return (((utc + offset) % 24) + 24) % 24
}
export function localToUtcHour(local: number): number {
  const offset = Math.round(-new Date().getTimezoneOffset() / 60)
  return (((local - offset) % 24) + 24) % 24
}

const BATCH_SIZES = [3, 5, 10, 15, 20]
const SESSION_SIZES = [10, 20, 50, 100]
const CEFR_LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']

// Index = Postgres EXTRACT(DOW): 0 = Sunday. Key names only — the display
// names come from the catalog (settings.weekdays.<key>) at render time.
const WEEKDAY_KEYS = [
  'sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday',
] as const

// Languages with a named script in the catalog (settings.scripts.<code>) for
// the language-specific section's copy; others fall back to
// settings.scripts.fallback.
const SCRIPT_CODES = new Set(['ru', 'ar', 'el', 'hi', 'th', 'ko', 'he', 'fa'])

// Labels come from the catalog (settings.theme.<value>) at render time.
const THEMES: Theme[] = ['system', 'light', 'dark']

/** One example word in the "Accents optional" copy, rendered in the target
 * language's own script treatment. Used through <Trans>, which supplies the
 * interpolated word as children. */
function AccentWord({
  code,
  children,
}: {
  code: string
  children?: React.ReactNode
}) {
  return (
    <LanguageWrapper languageCode={code}>
      <span>{children}</span>
    </LanguageWrapper>
  )
}

export default function SettingsPage() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)
  const theme = usePrefsStore((s) => s.theme)
  const setTheme = usePrefsStore((s) => s.setTheme)
  const sessionSize = usePrefsStore((s) => s.sessionSize)
  const setSessionSize = usePrefsStore((s) => s.setSessionSize)
  const accentsOptional = usePrefsStore((s) => s.accentsOptional)
  const setAccentsOptional = usePrefsStore((s) => s.setAccentsOptional)
  const learningTipsEnabled = usePrefsStore((s) => s.learningTipsEnabled)
  const setLearningTipsEnabled = usePrefsStore((s) => s.setLearningTipsEnabled)
  const dailyLearnGoal = usePrefsStore((s) => s.dailyLearnGoal)
  const setDailyLearnGoal = usePrefsStore((s) => s.setDailyLearnGoal)
  const qwertyTranslit = usePrefsStore((s) => s.qwertyTranslit)
  const setQwertyTranslit = usePrefsStore((s) => s.setQwertyTranslit)
  const showTashkeel = usePrefsStore((s) => s.showTashkeel)
  const setShowTashkeel = usePrefsStore((s) => s.setShowTashkeel)

  const { data: profile } = useQuery({ queryKey: ['profile'], queryFn: getProfile })
  const { data: languages = [] } = useQuery({ queryKey: ['languages'], queryFn: getLanguages })
  const selfId = useAuthStore((s) => s.session?.user?.id ?? null)

  // Account is a role-tabbed hub (beta request): Learner settings are the
  // default; Contribute/Review/Admin appear for accounts that hold those
  // roles, so the panels sit here instead of on a separate page to scroll.
  const [tab, setTab] = useState<AccountTab>('learner')
  const viewAsKey = useViewAsKey()
  const { data: workspace } = useQuery({
    queryKey: ['contribute-grammar', activeLanguageId, viewAsKey],
    queryFn: () => getGrammarForLanguage(activeLanguageId!),
    enabled: !!activeLanguageId,
    retry: false,
  })
  // Which TABS exist comes from the roles payload, not the workspace above:
  // roles are tiny, cached app-wide, and already loaded by the time Account
  // renders. Deriving the bar from the workspace meant a slow or failed
  // grammar fetch silently hid Contribute/Review/Admin — which is how
  // "view as Contributor" ended up showing a learner's page.
  const { data: roleInfo } = useQuery({
    queryKey: ['my-roles', viewAsKey],
    queryFn: getMyRoles,
    retry: false,
    staleTime: 5 * 60 * 1000,
  })
  const roles = roleInfo?.roles ?? []
  const isAdmin = roleInfo?.is_admin ?? false
  const canReview = canReviewWith(roles, isAdmin, activeLanguageId)
  const canContribute = canContributeWith(roles, isAdmin, activeLanguageId)
  // Separate from canReview on purpose: a trial reviewer reaches the queue
  // but cannot publish from it.
  const canTrialReview = canTrialReviewWith(roles, isAdmin, activeLanguageId)

  const canAddAccounts = roleInfo?.can_add_accounts ?? false
  const availableTabs = accountTabsFor({
    canContribute, canReview, canTrialReview, canAddAccounts, isAdmin,
  })
  // Resolved during render, not in an effect, so the page is never blank for
  // even one frame while a preview is switching.
  const activeTab = resolveTab(tab, availableTabs)
  const workspaceRefresh = () =>
    queryClient.invalidateQueries({ queryKey: ['contribute-grammar', activeLanguageId] })
  const { data: stats } = useQuery({
    queryKey: ['dashboard', activeLanguageId],
    queryFn: () => getDashboardStats(activeLanguageId!),
    enabled: !!activeLanguageId,
  })

  const { data: planPrices } = useQuery({
    queryKey: ['plan-prices'],
    queryFn: getPlanPrices,
    staleTime: Infinity,
  })
  // Monthly usage for the Plan section — the Claude-style meter (owner):
  // members with intelligent features see how much of their monthly usage
  // they've drawn, never the machinery behind it.
  const activeLanguageCode =
    languages.find((l) => l.id === activeLanguageId)?.code ?? ''
  const { data: tutorStatus } = useQuery({
    queryKey: ['tutor-status', activeLanguageId],
    queryFn: () => getTutorStatus(activeLanguageId!, activeLanguageCode),
    enabled: !!activeLanguageId && !!activeLanguageCode,
    retry: false,
  })
  const allPrice = formatPrice(planPrices?.all ?? null)
  // The monetization master switch: off (or unknown) hides every money
  // control here — the upgrade button and the billing link. The plan
  // NAME still shows; what you're on isn't a payment mention.
  const monetization = planPrices?.monetization === true
  const [billingUnavailable, setBillingUnavailable] = useState(false)

  // Upgrade (single → all): dev-mock grants directly; real mode redirects
  // to Stripe Checkout. A 503 means billing isn't launched — say so.
  const reminderMutation = useMutation({
    mutationFn: (patch: {
      reminder_opt_in?: boolean
      reminder_hour_utc?: number
      weekly_digest_opt_in?: boolean
      weekly_digest_dow?: number
      allow_explicit_content?: boolean
      sentence_audio_on_correct?: boolean
    }) => updateProfile(patch),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['profile'] }),
  })

  const upgradeMutation = useMutation({
    mutationFn: () => startPlanCheckout('all'),
    onSuccess: (res) => {
      if (res.granted) {
        queryClient.invalidateQueries({ queryKey: ['profile'] })
      } else if (res.url) {
        window.location.assign(res.url)
      }
    },
    onError: () => setBillingUnavailable(true),
  })

  const portalMutation = useMutation({
    mutationFn: openBillingPortal,
    onSuccess: (url) => window.location.assign(url),
    onError: () => setBillingUnavailable(true),
  })

  const batchMutation = useMutation({
    mutationFn: (batch_size: number) => updateProfile({ batch_size }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['profile'] }),
  })

  const resetMutation = useMutation({
    mutationFn: (languageId?: string) => resetProgress(languageId),
    onSuccess: () => queryClient.invalidateQueries(),
  })

  // Your level = the highest deck level currently feeding Learn. Derived
  // from deck subscriptions because that IS the level system — there's no
  // separate stored level.
  const { data: decks = [] } = useQuery({
    queryKey: ['learn-decks', activeLanguageId],
    queryFn: () => getLearnDecks(activeLanguageId!),
    enabled: !!activeLanguageId,
  })
  const currentLevel = decks
    .filter((d) => d.subscribed && d.level)
    .reduce<string | null>(
      (top, d) =>
        top === null || CEFR_LEVELS.indexOf(d.level!) > CEFR_LEVELS.indexOf(top)
          ? d.level!
          : top,
      null,
    )
  const levelMutation = useMutation({
    mutationFn: (level: string) => setLearnerLevel(activeLanguageId!, level),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['learn-decks'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })

  // Placement history for this language — what the retake copy compares
  // against ("you last placed at A2 in March").
  const { data: placementInfo } = useQuery({
    queryKey: ['placement-history', activeLanguageId],
    queryFn: () => getPlacementHistory(activeLanguageId!),
    enabled: !!activeLanguageId,
    retry: false,
  })
  const [retaking, setRetaking] = useState(false)

  const activeLanguage = languages.find((l) => l.id === activeLanguageId)
  const accentExample = accentExampleFor(activeLanguage?.code)

  const handleResetLanguage = () => {
    if (!activeLanguageId || !activeLanguage) return
    if (
      window.confirm(
        t('settings.danger.resetLanguageConfirm', {
          name: languageDisplayName(activeLanguage.code, activeLanguage.name, i18n.language),
        }),
      )
    ) {
      resetMutation.mutate(activeLanguageId)
    }
  }

  const handleResetAll = () => {
    if (window.confirm(t('settings.danger.resetAllConfirm'))) {
      resetMutation.mutate(undefined)
    }
  }

  const supportMutation = useMutation({
    mutationFn: (support_locale: string) => updateProfile({ support_locale }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profile'] })
      // English card content is localized server-side — refetch it.
      queryClient.invalidateQueries({ queryKey: ['due-cards'] })
    },
  })

  // How many cards across all CEFR levels the learner has started.
  const learned = stats
    ? Object.values(stats.cefr_progress).reduce((sum, p) => sum + p.learned, 0)
    : 0

  async function handleSignOut() {
    await supabase.auth.signOut()
    navigate('/login', { replace: true })
  }

  // Set when an exercise session's ⚙ brought us here — its full URL
  // (path + query), so "Back to session" restores the parked session.
  const fromSession = (location.state as { from?: string } | null)?.from

  return (
    <div className="min-h-screen bg-gray-50">
      <div className={`${PAGE_WIDE} mx-auto px-4 py-8 space-y-6`}>
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">{t('settings.title')}</h1>
          {/* Arrived mid-exercise? Lead back INTO the parked session (the
              session page restores its snapshot); plain visits go home. */}
          {fromSession ? (
            <button
              type="button"
              onClick={() => navigate(fromSession)}
              className="text-sm font-semibold text-lang hover:underline"
            >
              {t('settings.backToSession')}
            </button>
          ) : (
            <span className="flex items-center gap-3">
              <UiLanguageSwitcher />
              <button
                type="button"
                onClick={() => navigate('/')}
                className="text-sm text-lang hover:underline"
              >
                {t('common.backToDashboard')}
              </button>
            </span>
          )}
        </div>

        {/* Role tabs: Learner is always present; the rest appear by role.
            Shown whenever there is more than one — the old gate was
            `canReview || isAdmin`, which hid the bar from a plain
            CONTRIBUTOR and left them no way to reach their own Contribute
            panel at all. */}
        {availableTabs.length > 1 && (
          <div
            className="flex rounded-xl border border-gray-200 bg-white overflow-hidden text-sm"
            role="tablist"
            aria-label={t('settings.tabs.aria')}
          >
            {availableTabs.map((key) => (
              <button
                key={key}
                type="button"
                role="tab"
                aria-selected={activeTab === key}
                onClick={() => setTab(key)}
                className={`flex-1 px-4 py-2 font-semibold transition-colors ${
                  activeTab === key
                    ? 'bg-lang text-lang-on'
                    : 'text-gray-500 hover:bg-gray-50'
                }`}
              >
                {t(`settings.tabs.${key}`)}
              </button>
            ))}
          </div>
        )}

        {activeTab === 'contribute' && activeLanguageId && (
          <>
          <RoleGuide role="contribute" />
          <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3">
            <h2 className="font-semibold text-gray-800">Contribute</h2>
            {/* "Open the workspace", not "Open grammar editor": the door
                leads to the whole staff console (drafting, review queues,
                admin), and naming it after one tab inside was exactly the
                flow the owner said they didn't understand. */}
            <p className="text-xs text-gray-500">
              Draft grammar and vocabulary, and work the review queues, in
              the staff workspace.
            </p>
            <button
              type="button"
              onClick={() => navigate('/contribute')}
              className="rounded-lg bg-lang hover:bg-lang-dark text-lang-on font-semibold px-4 py-2 text-sm"
            >
              Open the workspace
            </button>
          </section>
          </>
        )}

        {activeTab === 'review' && activeLanguageId && (
          <>
            {/* A trial reviewer sees the queue but cannot publish — say so
                up front rather than letting them find out by pressing. */}
            <RoleGuide role={canReview ? 'review' : 'trial_review'} />
            {/* User feedback sits WITH the content queue, not off in Admin:
                most of what arrives is a content complaint, and the people
                who can act on those are reviewers. */}
            <FeedbackQueuePanel canTriage={isAdmin} />
            <ReviewQueue languageId={activeLanguageId} canReview={canReview} />
          </>
        )}

        {activeTab === 'invite' && canAddAccounts && !isAdmin && (
          <>
            <RoleGuide role="ambassador" />
            <InvitePanel />
          </>
        )}

        {activeTab === 'admin' && activeLanguageId && isAdmin && (
          <>
            <RoleGuide role="admin" />
            <AnalyticsPanel />
            <EngagementPanel />
            <LanguageVisibilityPanel />
            {/* The content "feeds" — generate, recheck, overlap scan, chart
                backfill — live here too, not just on /contribute, so they're
                findable from either admin surface. */}
            <GenerationPanel />
            {/* AI translation reviews are NOT here. Review work belongs in
                the Review section with the other queues (owner, twice) —
                this page kept a second copy, which is the one the owner
                kept finding. Contribute → Review is the single home. */}
            <AccountsPanel languages={languages} selfId={selfId} />
            <PlanLimitsPanel />
            <RolesPanel languages={languages} />
            <ReviewPolicyControl
              languageId={activeLanguageId}
              languageName={activeLanguage?.name}
              policy={workspace?.review_policy ?? 'strict'}
              uncheckedPoints={workspace?.unchecked_points ?? 0}
              onChanged={workspaceRefresh}
            />
            <TutorModelControl
              languageId={activeLanguageId}
              languageName={activeLanguage?.name}
              current={workspace?.tutor_model ?? null}
              defaultModel={workspace?.default_tutor_model}
              onChanged={workspaceRefresh}
            />
            <TutorCostsPanel />
          </>
        )}

        {activeTab === 'learner' && (
        <>
        {/* Independent settings cards, two across once there is room.
            Fifteen of them in a 576-pixel ribbon meant a monitor showed a
            fifth of the page and three screens of scrolling, with the
            width sitting unused on both sides (owner: make better use of
            the screen real estate on computers). The danger zone below
            deliberately stays full width and last — a destructive control
            should not turn up half-width beside a checkbox. */}
        <div className={CARD_COLUMNS}>
          <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3">
            <h2 className="font-semibold text-gray-800">{t('settings.activeLanguage')}</h2>
            <LanguagePicker />
          </section>

          {/* Renders nothing until you've actually sent something. */}
          <MyFeedback />

          {/* Your level (beta report: a misplaced learner was stuck with A1
              content and couldn't find any way to change it — placement's
              "you can change it later" promise now lives here). */}
          {activeLanguageId && (
            <section
              className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3"
              data-testid="level-section"
            >
              <h2 className="font-semibold text-gray-800">{t('settings.level.title')}</h2>
              <p className="text-xs text-gray-500">{t('settings.level.desc')}</p>
              <div className="flex flex-wrap gap-2">
                {CEFR_LEVELS.map((l) => (
                  <button
                    key={l}
                    type="button"
                    onClick={() => levelMutation.mutate(l)}
                    disabled={levelMutation.isPending}
                    aria-pressed={currentLevel === l}
                    className={
                      'rounded-lg px-4 py-2 text-sm font-medium border ' +
                      (currentLevel === l
                        ? 'bg-lang text-white border-lang'
                        : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50')
                    }
                    style={{ minHeight: '44px' }}
                  >
                    {l}
                  </button>
                ))}
              </div>
              {levelMutation.isSuccess && (
                <p className="text-xs text-green-700">
                  {t('settings.level.setSuccess', {
                    level: levelMutation.data.level,
                    count: levelMutation.data.subscribed,
                    removed:
                      levelMutation.data.unsubscribed > 0
                        ? t('settings.level.removedSuffix', {
                            count: levelMutation.data.unsubscribed,
                          })
                        : '',
                  })}
                </p>
              )}
              {levelMutation.isError && (
                <p className="text-xs text-red-500">{t('settings.level.saveError')}</p>
              )}

              {/* Retake (owner request): the placement offer promises the test
                  can be taken any time, and this is where that promise is
                  kept. Picking a level by hand stays right above it — the test
                  is the guided way, never the only way. */}
              <div className="pt-3 border-t border-gray-100 space-y-2">
                <p className="text-xs text-gray-500">
                  {placementInfo?.has_placed
                    ? placementInfo.last_taken_at
                      ? t('settings.level.lastPlacedOn', {
                          level: placementInfo.last_level ?? '—',
                          date: new Date(
                            placementInfo.last_taken_at,
                          ).toLocaleDateString(i18n.language),
                        })
                      : t('settings.level.lastPlaced', {
                          level: placementInfo.last_level ?? '—',
                        })
                    : t('settings.level.notPlaced')}
                </p>
                <button
                  type="button"
                  onClick={() => setRetaking(true)}
                  disabled={!activeLanguage}
                  className="rounded-xl border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                  style={{ minHeight: '44px' }}
                  data-testid="retake-placement"
                >
                  {placementInfo?.has_placed
                    ? t('settings.level.retake')
                    : t('settings.level.take')}
                </button>
              </div>
              {retaking && activeLanguage && (
                <PlacementTest
                  language={activeLanguage}
                  onClose={() => setRetaking(false)}
                />
              )}
            </section>
          )}

          <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3">
            <h2 className="font-semibold text-gray-800">{t('settings.tour.title')}</h2>
            <p className="text-sm text-gray-600">{t('settings.tour.desc')}</p>
            <button
              type="button"
              onClick={() => navigate('/welcome')}
              className="rounded-xl border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
              style={{ minHeight: '44px' }}
            >
              {t('settings.tour.button')}
            </button>
          </section>

          <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3">
            <h2 className="font-semibold text-gray-800">{t('settings.plan.title')}</h2>
            <p className="text-sm text-gray-600">
              {profile?.plan_scope === 'single'
                ? languages.find((l) => l.id === profile?.plan_language_id)?.name
                  ? t('settings.plan.singleWithLanguage', {
                      name: languages.find(
                        (l) => l.id === profile?.plan_language_id,
                      )!.name,
                    })
                  : t('settings.plan.single')
                : t('settings.plan.all')}
            </p>
            {monetization && profile?.plan_scope === 'single' && (
              <button
                type="button"
                onClick={() => upgradeMutation.mutate()}
                disabled={upgradeMutation.isPending}
                className="rounded-lg bg-lang hover:bg-lang-dark text-lang-on px-4 py-2 text-sm font-semibold disabled:opacity-50"
              >
                {upgradeMutation.isPending
                  ? t('settings.plan.opening')
                  : allPrice
                    ? t('settings.plan.upgradeWithPrice', { price: allPrice })
                    : t('settings.plan.upgrade')}
              </button>
            )}
            {tutorStatus?.available && (
              <UsageMeter allowance={tutorStatus.allowance} className="pt-1" />
            )}
            {monetization && (
              <button
                type="button"
                onClick={() => portalMutation.mutate()}
                disabled={portalMutation.isPending}
                className="block text-xs text-lang hover:underline disabled:opacity-50"
              >
                {t('settings.plan.manageBilling')}
              </button>
            )}
            {monetization && billingUnavailable && (
              <p className="text-xs text-gray-500">
                {t('settings.plan.billingUnavailable')}
              </p>
            )}
          </section>

          <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3">
            <h2 className="font-semibold text-gray-800">{t('settings.dailyGoal.title')}</h2>
            <p className="text-xs text-gray-500">{t('settings.dailyGoal.desc')}</p>
            <div className="flex gap-2">
              {([20, 50, 0] as const).map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => setDailyLearnGoal(n)}
                  aria-pressed={dailyLearnGoal === n}
                  className={
                    'rounded-lg px-4 py-2 text-sm font-medium border ' +
                    (dailyLearnGoal === n
                      ? 'bg-lang text-white border-lang'
                      : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50')
                  }
                  style={{ minHeight: '44px' }}
                >
                  {n === 0 ? t('settings.dailyGoal.wholeQueue') : n}
                </button>
              ))}
            </div>
          </section>

          <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3">
            <h2 className="font-semibold text-gray-800">{t('settings.batch.title')}</h2>
            <p className="text-xs text-gray-500">{t('settings.batch.desc')}</p>
            <div className="flex gap-2">
              {BATCH_SIZES.map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => batchMutation.mutate(n)}
                  aria-pressed={profile?.batch_size === n}
                  className={
                    'rounded-lg px-4 py-2 text-sm font-medium border ' +
                    (profile?.batch_size === n
                      ? 'bg-lang text-white border-lang'
                      : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50')
                  }
                  style={{ minHeight: '44px' }}
                >
                  {n}
                </button>
              ))}
            </div>
          </section>

          <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3">
            <h2 className="font-semibold text-gray-800">{t('settings.sessionSize.title')}</h2>
            <p className="text-xs text-gray-500">{t('settings.sessionSize.desc')}</p>
            <div className="flex gap-2">
              {SESSION_SIZES.map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => setSessionSize(n)}
                  aria-pressed={sessionSize === n}
                  className={
                    'rounded-lg px-4 py-2 text-sm font-medium border ' +
                    (sessionSize === n
                      ? 'bg-lang text-white border-lang'
                      : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50')
                  }
                  style={{ minHeight: '44px' }}
                >
                  {n}
                </button>
              ))}
            </div>
          </section>

          {/* Only for languages whose spelling actually carries marks, and
              always shown with a pair from THAT language — a Spanish example
              told an Arabic learner nothing, and the toggle did nothing at all
              on Indonesian or Tagalog. */}
          {accentExample && (
          <section
            className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3"
            data-testid="accents-optional"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="font-semibold text-gray-800">{t('settings.accents.title')}</h2>
                <p className="text-xs text-gray-500">
                  <Trans
                    i18nKey="settings.accents.desc"
                    values={{
                      loose: accentExample.loose,
                      strict: accentExample.strict,
                      gloss: accentExample.gloss,
                    }}
                    components={{
                      loose: <AccentWord code={activeLanguage!.code} />,
                      strict: <AccentWord code={activeLanguage!.code} />,
                    }}
                  />
                </p>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={accentsOptional}
                aria-label={t('settings.accents.title')}
                onClick={() => setAccentsOptional(!accentsOptional)}
                className={
                  'relative shrink-0 inline-flex h-6 w-11 items-center rounded-full transition-colors ' +
                  (accentsOptional ? 'bg-lang' : 'bg-gray-300')
                }
              >
                <span
                  className={
                    'inline-block h-5 w-5 transform rounded-full bg-white transition-transform ' +
                    (accentsOptional ? 'translate-x-5' : 'translate-x-1')
                  }
                />
              </button>
            </div>
          </section>
          )}

          {/* Explicit content. A learner reported meeting "whore" in their
              vocabulary — nobody chose to teach it: the frequency lists are
              built from subtitle corpora, and Spanish *puta* is rank 505, well
              inside a beginner's first thousand words.

              Off by default, and a setting rather than a deletion: these words
              are frequent for a reason, adult learners reading real material
              will meet them, and someone who asks for them should get them.
              Arriving unannounced in week two is the part that was wrong. */}
          <section
            className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3"
            data-testid="explicit-content"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="font-semibold text-gray-800">
                  {t('settings.explicit.title')}
                </h2>
                <p className="text-xs text-gray-500">{t('settings.explicit.desc')}</p>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={profile?.allow_explicit_content ?? false}
                aria-label={t('settings.explicit.title')}
                disabled={reminderMutation.isPending}
                onClick={() =>
                  reminderMutation.mutate({
                    allow_explicit_content: !(
                      profile?.allow_explicit_content ?? false
                    ),
                  })
                }
                className={
                  'relative shrink-0 inline-flex h-6 w-11 items-center rounded-full transition-colors ' +
                  (profile?.allow_explicit_content ? 'bg-lang' : 'bg-gray-300')
                }
              >
                <span
                  className={
                    'inline-block h-5 w-5 transform rounded-full bg-white transition-transform ' +
                    (profile?.allow_explicit_content
                      ? 'translate-x-5'
                      : 'translate-x-1')
                  }
                />
              </button>
            </div>
          </section>

          {/* Sentence audio on a correct answer (owner request). Account-
              level so every device behaves the same; on by default, this is
              the off switch. */}
          <section
            className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3"
            data-testid="sentence-audio"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="font-semibold text-gray-800">
                  {t('settings.sentenceAudio.title')}
                </h2>
                <p className="text-xs text-gray-500">
                  {t('settings.sentenceAudio.desc')}
                </p>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={profile?.sentence_audio_on_correct ?? true}
                aria-label={t('settings.sentenceAudio.title')}
                disabled={reminderMutation.isPending}
                onClick={() =>
                  reminderMutation.mutate({
                    sentence_audio_on_correct: !(
                      profile?.sentence_audio_on_correct ?? true
                    ),
                  })
                }
                className={
                  'relative shrink-0 inline-flex h-6 w-11 items-center rounded-full transition-colors ' +
                  ((profile?.sentence_audio_on_correct ?? true)
                    ? 'bg-lang'
                    : 'bg-gray-300')
                }
              >
                <span
                  className={
                    'inline-block h-5 w-5 transform rounded-full bg-white transition-transform ' +
                    ((profile?.sentence_audio_on_correct ?? true)
                      ? 'translate-x-5'
                      : 'translate-x-1')
                  }
                />
              </button>
            </div>
          </section>

          {/* Language-specific options (beta request: these belong in account
              learning settings, not buried in exercise UIs). Only shown for
              languages that have any — non-Latin scripts today. */}
          {activeLanguage && hasTranslit(activeLanguage.code) && (
            <section
              className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-4"
              data-testid="language-specific"
            >
              <div>
                <h2 className="font-semibold text-gray-800">
                  {t('settings.langOptions.title', { name: languageDisplayName(activeLanguage.code, activeLanguage.name, i18n.language) })}
                </h2>
                <p className="text-xs text-gray-500">
                  {t('settings.langOptions.desc', { name: languageDisplayName(activeLanguage.code, activeLanguage.name, i18n.language) })}
                </p>
              </div>

              {activeLanguage.code === 'ar' && (
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h3 className="text-sm font-medium text-gray-800">
                      {t('settings.langOptions.tashkeelTitle')}
                    </h3>
                    <p className="text-xs text-gray-500">
                      {t('settings.langOptions.tashkeelDesc')}
                    </p>
                  </div>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={showTashkeel}
                    aria-label={t('settings.langOptions.tashkeelTitle')}
                    onClick={() => setShowTashkeel(!showTashkeel)}
                    className={
                      'relative shrink-0 inline-flex h-6 w-11 items-center rounded-full transition-colors ' +
                      (showTashkeel ? 'bg-lang' : 'bg-gray-300')
                    }
                  >
                    <span
                      className={
                        'inline-block h-5 w-5 transform rounded-full bg-white transition-transform ' +
                        (showTashkeel ? 'translate-x-5' : 'translate-x-1')
                      }
                    />
                  </button>
                </div>
              )}

              <div className="flex items-start justify-between gap-4">
                <div>
                  <h3 className="text-sm font-medium text-gray-800">
                    {t('settings.langOptions.qwertyTitle')}
                  </h3>
                  <p className="text-xs text-gray-500">
                    {t('settings.langOptions.qwertyDesc', {
                      script: SCRIPT_CODES.has(activeLanguage.code)
                        ? t(`settings.scripts.${activeLanguage.code}`)
                        : t('settings.scripts.fallback'),
                      name: languageDisplayName(activeLanguage.code, activeLanguage.name, i18n.language),
                    })}
                  </p>
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={qwertyTranslit[activeLanguage.code] ?? true}
                  aria-label={t('settings.langOptions.qwertyTitle')}
                  onClick={() =>
                    setQwertyTranslit(
                      activeLanguage.code,
                      !(qwertyTranslit[activeLanguage.code] ?? true),
                    )
                  }
                  className={
                    'relative shrink-0 inline-flex h-6 w-11 items-center rounded-full transition-colors ' +
                    ((qwertyTranslit[activeLanguage.code] ?? true)
                      ? 'bg-lang'
                      : 'bg-gray-300')
                  }
                >
                  <span
                    className={
                      'inline-block h-5 w-5 transform rounded-full bg-white transition-transform ' +
                      ((qwertyTranslit[activeLanguage.code] ?? true)
                        ? 'translate-x-5'
                        : 'translate-x-1')
                    }
                  />
                </button>
              </div>
            </section>
          )}

          <RecoSettings />

          <TutorMemoryPanel />

          <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="font-semibold text-gray-800">{t('settings.tips.title')}</h2>
                <p className="text-xs text-gray-500">{t('settings.tips.desc')}</p>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={learningTipsEnabled}
                aria-label={t('settings.tips.title')}
                onClick={() => setLearningTipsEnabled(!learningTipsEnabled)}
                className={
                  'relative shrink-0 inline-flex h-6 w-11 items-center rounded-full transition-colors ' +
                  (learningTipsEnabled ? 'bg-lang' : 'bg-gray-300')
                }
              >
                <span
                  className={
                    'inline-block h-5 w-5 transform rounded-full bg-white transition-transform ' +
                    (learningTipsEnabled ? 'translate-x-5' : 'translate-x-1')
                  }
                />
              </button>
            </div>
          </section>

          {/* Two INDEPENDENT email opt-ins, not a mode switch: the daily nudge
              answers "is there work waiting?", the weekly digest answers "how
              did my week go, and what should I do beyond the app?". A learner
              can want either, both, or neither. */}
          <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3">
            <h2 className="font-semibold text-gray-800">{t('settings.email.title')}</h2>
            <div className="flex items-start justify-between gap-4 border-t border-gray-100 pt-3">
              <div>
                <h3 className="text-sm font-medium text-gray-800">
                  {t('settings.email.dailyTitle')}
                </h3>
                <p className="text-xs text-gray-500">
                  {t('settings.email.dailyDesc')}
                </p>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={profile?.reminder_opt_in ?? false}
                aria-label={t('settings.email.dailyAria')}
                onClick={() =>
                  reminderMutation.mutate({
                    reminder_opt_in: !(profile?.reminder_opt_in ?? false),
                  })
                }
                className={
                  'relative shrink-0 inline-flex h-6 w-11 items-center rounded-full transition-colors ' +
                  (profile?.reminder_opt_in ? 'bg-lang' : 'bg-gray-300')
                }
              >
                <span
                  className={
                    'inline-block h-5 w-5 transform rounded-full bg-white transition-transform ' +
                    (profile?.reminder_opt_in ? 'translate-x-5' : 'translate-x-1')
                  }
                />
              </button>
            </div>
            {profile?.reminder_opt_in && (
              <label className="flex items-center gap-2 text-sm text-gray-700">
                {t('settings.email.sendAround')}
                <select
                  value={utcToLocalHour(profile?.reminder_hour_utc ?? 16)}
                  onChange={(e) =>
                    reminderMutation.mutate({
                      reminder_hour_utc: localToUtcHour(Number(e.target.value)),
                    })
                  }
                  className="rounded-lg border border-gray-200 px-2 py-1 text-sm"
                  aria-label={t('settings.email.hourAria')}
                >
                  {Array.from({ length: 24 }, (_, h) => (
                    <option key={h} value={h}>
                      {h.toString().padStart(2, '0')}:00
                    </option>
                  ))}
                </select>
                {t('settings.email.yourTime')}
              </label>
            )}

            <div className="flex items-start justify-between gap-4 border-t border-gray-100 pt-3">
              <div>
                <h3 className="text-sm font-medium text-gray-800">
                  {t('settings.email.weeklyTitle')}
                </h3>
                <p className="text-xs text-gray-500">
                  {t('settings.email.weeklyDesc')}
                </p>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={profile?.weekly_digest_opt_in ?? false}
                aria-label={t('settings.email.weeklyAria')}
                onClick={() =>
                  reminderMutation.mutate({
                    weekly_digest_opt_in: !(profile?.weekly_digest_opt_in ?? false),
                  })
                }
                className={
                  'relative shrink-0 inline-flex h-6 w-11 items-center rounded-full transition-colors ' +
                  (profile?.weekly_digest_opt_in ? 'bg-lang' : 'bg-gray-300')
                }
              >
                <span
                  className={
                    'inline-block h-5 w-5 transform rounded-full bg-white transition-transform ' +
                    (profile?.weekly_digest_opt_in ? 'translate-x-5' : 'translate-x-1')
                  }
                />
              </button>
            </div>
            {profile?.weekly_digest_opt_in && (
              <label className="flex items-center gap-2 text-sm text-gray-700">
                {t('settings.email.sendOn')}
                <select
                  value={profile?.weekly_digest_dow ?? 0}
                  onChange={(e) =>
                    reminderMutation.mutate({
                      weekly_digest_dow: Number(e.target.value),
                    })
                  }
                  className="rounded-lg border border-gray-200 px-2 py-1 text-sm"
                  aria-label={t('settings.email.dayAria')}
                >
                  {WEEKDAY_KEYS.map((day, i) => (
                    <option key={i} value={i}>{t(`settings.weekdays.${day}`)}</option>
                  ))}
                </select>
              </label>
            )}
          </section>

          {/* Shown on EVERY course, not just English. The backend applies
              support_locale to every course (cards.py _effective_locale), and
              the globe writes it for everyone — so gating this control on
              "studying English" left the setting live and its only off-switch
              invisible. An English speaker learning Spanish got Arabic
              translations with no way back. */}
          <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3">
            <h2 className="font-semibold text-gray-800">{t('settings.support.title')}</h2>
            <p className="text-xs text-gray-500">{t('settings.support.desc')}</p>
            {/* Tri-state, honestly displayed. 'auto' (stored NULL) means the
                help language FOLLOWS the interface language — the default,
                with no stored state to go stale. Any language here, including
                English, is an explicit choice that survives everything,
                globe taps included. 'en' used to double as the reset value,
                which made "English help under a French interface"
                inexpressible once automatic meant "follow the interface". */}
            <select
              value={profile?.support_locale ?? 'auto'}
              onChange={(e) => supportMutation.mutate(e.target.value)}
              disabled={supportMutation.isPending}
              aria-label={t('settings.support.title')}
              data-testid="support-locale-select"
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm bg-white"
            >
              <option value="auto">{t('settings.support.autoOption')}</option>
              <option value="en">{t('settings.support.englishOption')}</option>
              {languages
                .filter((l) => l.code !== 'en')
                .map((l) => (
                  <option key={l.code} value={l.code}>{languageDisplayName(l.code, l.name, i18n.language)}</option>
                ))}
            </select>
            {supportMutation.isError && (
              <p className="text-xs text-red-500">{t('settings.support.saveError')}</p>
            )}
          </section>

          <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3">
            <h2 className="font-semibold text-gray-800">{t('settings.theme.title')}</h2>
            <p className="text-xs text-gray-500">{t('settings.theme.desc')}</p>
            <div className="flex gap-2">
              {THEMES.map((value) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setTheme(value)}
                  aria-pressed={theme === value}
                  className={
                    'rounded-lg px-4 py-2 text-sm font-medium border ' +
                    (theme === value
                      ? 'bg-lang text-white border-lang'
                      : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50')
                  }
                  style={{ minHeight: '44px' }}
                >
                  {t(`settings.theme.${value}`)}
                </button>
              ))}
            </div>
          </section>

          {/* Only renders when this account is in a rollout that was opened
              to learner choice — invisible on a normal account. */}
          <AppearanceTrial />

          <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">
            <h2 className="font-semibold text-gray-800 mb-3">{t('settings.progress.title')}</h2>
            <div className="grid grid-cols-3 gap-3 text-center">
              <div>
                <div className="text-2xl font-bold text-lang">{stats?.due_count ?? 0}</div>
                <div className="text-xs text-gray-500">{t('settings.progress.dueNow')}</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-lang">{stats?.streak_days ?? 0}</div>
                <div className="text-xs text-gray-500">{t('settings.progress.dayStreak')}</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-lang">{learned}</div>
                <div className="text-xs text-gray-500">{t('settings.progress.cardsLearned')}</div>
              </div>
            </div>
          </section>

        </div>

        <section className="bg-white rounded-2xl shadow-sm border border-red-100 p-5 space-y-3">
          <h2 className="font-semibold text-red-700">{t('settings.danger.title')}</h2>
          <p className="text-xs text-gray-500">{t('settings.danger.desc')}</p>
          <div className="flex flex-col gap-2">
            <button
              type="button"
              onClick={handleResetLanguage}
              disabled={!activeLanguageId || resetMutation.isPending}
              className="rounded-lg px-4 py-2 text-sm font-medium border border-red-200 text-red-700 bg-white hover:bg-red-50 disabled:opacity-50 text-start"
              style={{ minHeight: '44px' }}
            >
              {t('settings.danger.resetLanguage', {
                name: activeLanguage
                  ? languageDisplayName(activeLanguage.code, activeLanguage.name, i18n.language)
                  : t('settings.danger.activeLanguageFallback'),
              })}
            </button>
            <button
              type="button"
              onClick={handleResetAll}
              disabled={resetMutation.isPending}
              className="rounded-lg px-4 py-2 text-sm font-medium border border-red-200 text-red-700 bg-white hover:bg-red-50 disabled:opacity-50 text-start"
              style={{ minHeight: '44px' }}
            >
              {t('settings.danger.resetAll')}
            </button>
            {resetMutation.isSuccess && (
              <p className="text-xs text-green-700">
                {t('settings.danger.resetDone', {
                  count: resetMutation.data.cards_deleted,
                })}
              </p>
            )}
          </div>
        </section>

        <button
          type="button"
          onClick={handleSignOut}
          className="w-full text-sm text-red-600 hover:text-red-700 hover:underline py-2"
        >
          {t('settings.signOut')}
        </button>

        <p className="text-center text-xs text-gray-500">
          <a href="/terms" className="hover:text-lang hover:underline">
            {t('login.terms')}
          </a>
        </p>
        </>
        )}
      </div>
    </div>
  )
}
