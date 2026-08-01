import { useState } from 'react'
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
import { hasTranslit } from '../keyboards/translit'
import RecoSettings from '../recommendations/RecoSettings'
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
import TranslationReviewsPanel from '../contribute/TranslationReviewsPanel'
import {
  ReviewPolicyControl,
  TutorModelControl,
  TutorCostsPanel,
} from '../contribute/ContributorPage'
import { useAuthStore } from '../../stores/authStore'

type AccountTab = 'learner' | 'contribute' | 'review' | 'invite' | 'admin'

const TAB_LABEL: Record<AccountTab, string> = {
  learner: 'Learner',
  contribute: 'Contribute',
  review: 'Review',
  // Ambassadors get their own tab rather than a cut-down "Admin" one:
  // calling it Admin for someone who can do exactly one admin thing
  // misdescribes both the tab and the role.
  invite: 'Invite',
  admin: 'Admin',
}

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

// Index = Postgres EXTRACT(DOW): 0 = Sunday.
const WEEKDAYS = [
  'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday',
]

// Script names for the language-specific section's copy.
const SCRIPT_NAME: Record<string, string> = {
  ru: 'Cyrillic',
  ar: 'Arabic script',
  el: 'Greek',
  hi: 'Devanagari',
  th: 'Thai script',
  ko: 'Hangul',
}

const THEMES: { value: Theme; label: string }[] = [
  { value: 'system', label: 'System' },
  { value: 'light', label: 'Light' },
  { value: 'dark', label: 'Dark' },
]

export default function SettingsPage() {
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
  // The "learning English from" support locale only matters when the active
  // language IS English — hide it otherwise.
  const studyingEnglish =
    languages.find((l) => l.id === activeLanguageId)?.code === 'en'
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
        `Reset ALL your ${activeLanguage.name} studies? This permanently deletes every ${activeLanguage.name} card and its review history. Your notes and personal sentences are kept.`,
      )
    ) {
      resetMutation.mutate(activeLanguageId)
    }
  }

  const handleResetAll = () => {
    if (
      window.confirm(
        'Reset your studies for EVERY language? This permanently deletes all cards and all review history across all languages. Your notes and personal sentences are kept.',
      )
    ) {
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
      <div className="max-w-xl mx-auto px-4 py-8 space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">Account</h1>
          {/* Arrived mid-exercise? Lead back INTO the parked session (the
              session page restores its snapshot); plain visits go home. */}
          {fromSession ? (
            <button
              type="button"
              onClick={() => navigate(fromSession)}
              className="text-sm font-semibold text-lang hover:underline"
            >
              ← Back to session
            </button>
          ) : (
            <button
              type="button"
              onClick={() => navigate('/')}
              className="text-sm text-lang hover:underline"
            >
              ← Dashboard
            </button>
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
            aria-label="Account sections"
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
                {TAB_LABEL[key]}
              </button>
            ))}
          </div>
        )}

        {activeTab === 'contribute' && activeLanguageId && (
          <>
          <RoleGuide role="contribute" />
          <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3">
            <h2 className="font-semibold text-gray-800">Contribute</h2>
            <p className="text-xs text-gray-500">
              Draft and edit grammar points for the active language in the
              full editor.
            </p>
            <button
              type="button"
              onClick={() => navigate('/contribute')}
              className="rounded-lg bg-lang hover:bg-lang-dark text-lang-on font-semibold px-4 py-2 text-sm"
            >
              Open grammar editor
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
            <TranslationReviewsPanel />
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
        <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3">
          <h2 className="font-semibold text-gray-800">Active language</h2>
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
            <h2 className="font-semibold text-gray-800">Your level</h2>
            <p className="text-xs text-gray-500">
              Sets which decks feed Learn — grammar and vocabulary at this
              level and below. Placement got it wrong? Fix it here any time.
              Cards you've already learned are never removed.
            </p>
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
                Level set to {levelMutation.data.level} —{' '}
                {levelMutation.data.subscribed} deck
                {levelMutation.data.subscribed === 1 ? '' : 's'} added
                {levelMutation.data.unsubscribed > 0
                  ? `, ${levelMutation.data.unsubscribed} removed`
                  : ''}
                . Learn will draw from them right away.
              </p>
            )}
            {levelMutation.isError && (
              <p className="text-xs text-red-500">Couldn't save — try again.</p>
            )}

            {/* Retake (owner request): the placement offer promises the test
                can be taken any time, and this is where that promise is
                kept. Picking a level by hand stays right above it — the test
                is the guided way, never the only way. */}
            <div className="pt-3 border-t border-gray-100 space-y-2">
              <p className="text-xs text-gray-500">
                {placementInfo?.has_placed
                  ? `You last placed at ${placementInfo.last_level ?? '—'}${
                      placementInfo.last_taken_at
                        ? ` on ${new Date(placementInfo.last_taken_at).toLocaleDateString()}`
                        : ''
                    }. Take it again to see how far you've come — the questions
                       change each time.`
                  : `Not sure which level to pick? Take the short adaptive test
                     and we'll suggest one. You can retake it any time.`}
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
                  ? 'Retake the placement test'
                  : 'Take the placement test'}
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
          <h2 className="font-semibold text-gray-800">New here?</h2>
          <p className="text-sm text-gray-600">
            A one-card-per-feature tour of everything in the app.
          </p>
          <button
            type="button"
            onClick={() => navigate('/welcome')}
            className="rounded-xl border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            style={{ minHeight: '44px' }}
          >
            Show me around
          </button>
        </section>

        <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3">
          <h2 className="font-semibold text-gray-800">Plan</h2>
          <p className="text-sm text-gray-600">
            {profile?.plan_scope === 'single'
              ? `Single language${
                  languages.find((l) => l.id === profile?.plan_language_id)
                    ?.name
                    ? ` — ${languages.find((l) => l.id === profile?.plan_language_id)!.name}`
                    : ''
                }`
              : 'All languages'}
          </p>
          {profile?.plan_scope === 'single' && (
            <button
              type="button"
              onClick={() => upgradeMutation.mutate()}
              disabled={upgradeMutation.isPending}
              className="rounded-lg bg-lang hover:bg-lang-dark text-lang-on px-4 py-2 text-sm font-semibold disabled:opacity-50"
            >
              {upgradeMutation.isPending
                ? 'Opening…'
                : allPrice
                  ? `Upgrade to All languages — ${allPrice}`
                  : 'Upgrade to All languages'}
            </button>
          )}
          {tutorStatus?.available && (
            <UsageMeter allowance={tutorStatus.allowance} className="pt-1" />
          )}
          <button
            type="button"
            onClick={() => portalMutation.mutate()}
            disabled={portalMutation.isPending}
            className="block text-xs text-lang hover:underline disabled:opacity-50"
          >
            Manage billing
          </button>
          {billingUnavailable && (
            <p className="text-xs text-gray-400">
              Billing hasn't launched yet — early accounts keep their chosen
              plan for free, and keep their price when it goes live.
            </p>
          )}
        </section>

        <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3">
          <h2 className="font-semibold text-gray-800">Daily learn goal</h2>
          <p className="text-xs text-gray-500">
            What the Learn tile counts toward each day. A small goal keeps the
            queue from feeling overwhelming — or show every queued card.
          </p>
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
                {n === 0 ? 'Whole queue' : n}
              </button>
            ))}
          </div>
        </section>

        <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3">
          <h2 className="font-semibold text-gray-800">New cards per session</h2>
          <p className="text-xs text-gray-500">
            How many new words/grammar points to introduce each time you learn.
          </p>
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
          <h2 className="font-semibold text-gray-800">Cards per review session</h2>
          <p className="text-xs text-gray-500">
            How many due cards each review session pulls. Anything left over
            stays due for the next session.
          </p>
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
              <h2 className="font-semibold text-gray-800">Accents optional</h2>
              <p className="text-xs text-gray-500">
                Count answers correct even when accents or diacritics are
                missing — “
                <LanguageWrapper languageCode={activeLanguage!.code}>
                  <span>{accentExample.loose}</span>
                </LanguageWrapper>
                ” passes for “
                <LanguageWrapper languageCode={activeLanguage!.code}>
                  <span>{accentExample.strict}</span>
                </LanguageWrapper>
                ” ({accentExample.gloss}). The right spelling still shows, so
                you keep learning the marks.
              </p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={accentsOptional}
              aria-label="Accents optional"
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
                Explicit words and sentences
              </h2>
              <p className="text-xs text-gray-500">
                Slurs and strong profanity are hidden from your cards, reading
                and examples. They are genuinely common words — turn this on if
                you want to learn them, and they will be taught like anything
                else.
              </p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={profile?.allow_explicit_content ?? false}
              aria-label="Explicit words and sentences"
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
                {activeLanguage.name} options
              </h2>
              <p className="text-xs text-gray-500">
                Settings that only apply when studying {activeLanguage.name}.
              </p>
            </div>

            {activeLanguage.code === 'ar' && (
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h3 className="text-sm font-medium text-gray-800">
                    Short vowels (tashkeel)
                  </h3>
                  <p className="text-xs text-gray-500">
                    Show the fully vocalized form — كَتَبَ — under new words.
                    Turn off to practise reading bare script, the way native
                    materials are written.
                  </p>
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={showTashkeel}
                  aria-label="Short vowels (tashkeel)"
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
                  Type with QWERTY letters
                </h3>
                <p className="text-xs text-gray-500">
                  Answers typed in Latin letters convert to{' '}
                  {SCRIPT_NAME[activeLanguage.code] ?? 'the target script'} as
                  you type. Turn off if you have a real{' '}
                  {activeLanguage.name} keyboard.
                </p>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={qwertyTranslit[activeLanguage.code] ?? true}
                aria-label="Type with QWERTY letters"
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

        <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="font-semibold text-gray-800">Learning tips</h2>
              <p className="text-xs text-gray-500">
                Occasional evidence-based study nudges — how to practise, why the
                schedule works — shown at most about once a day. Turn them off
                here to never see them.
              </p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={learningTipsEnabled}
              aria-label="Learning tips"
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
          <h2 className="font-semibold text-gray-800">Email</h2>
          <div className="flex items-start justify-between gap-4 border-t border-gray-100 pt-3">
            <div>
              <h3 className="text-sm font-medium text-gray-800">
                Daily reminder
              </h3>
              <p className="text-xs text-gray-500">
                One email a day when reviews are waiting — nothing on days with
                no reviews due.
              </p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={profile?.reminder_opt_in ?? false}
              aria-label="Email reminders"
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
              Send around
              <select
                value={utcToLocalHour(profile?.reminder_hour_utc ?? 16)}
                onChange={(e) =>
                  reminderMutation.mutate({
                    reminder_hour_utc: localToUtcHour(Number(e.target.value)),
                  })
                }
                className="rounded-lg border border-gray-200 px-2 py-1 text-sm"
                aria-label="Reminder hour"
              >
                {Array.from({ length: 24 }, (_, h) => (
                  <option key={h} value={h}>
                    {h.toString().padStart(2, '0')}:00
                  </option>
                ))}
              </select>
              your time
            </label>
          )}

          <div className="flex items-start justify-between gap-4 border-t border-gray-100 pt-3">
            <div>
              <h3 className="text-sm font-medium text-gray-800">
                Weekly review
              </h3>
              <p className="text-xs text-gray-500">
                Your week in one email — what you studied, how it went, and
                that week's reading, watching and listening picks.
              </p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={profile?.weekly_digest_opt_in ?? false}
              aria-label="Weekly review email"
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
              Send on
              <select
                value={profile?.weekly_digest_dow ?? 0}
                onChange={(e) =>
                  reminderMutation.mutate({
                    weekly_digest_dow: Number(e.target.value),
                  })
                }
                className="rounded-lg border border-gray-200 px-2 py-1 text-sm"
                aria-label="Weekly review day"
              >
                {WEEKDAYS.map((label, i) => (
                  <option key={i} value={i}>{label}</option>
                ))}
              </select>
            </label>
          )}
        </section>

        {studyingEnglish && (
          <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3">
            <h2 className="font-semibold text-gray-800">Learning English from</h2>
            <p className="text-xs text-gray-500">
              Hints, definitions, and example-sentence translations appear in
              this language instead of English.
            </p>
            <select
              value={profile?.support_locale ?? 'en'}
              onChange={(e) => supportMutation.mutate(e.target.value)}
              disabled={supportMutation.isPending}
              aria-label="Learning English from"
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm bg-white"
            >
              <option value="en">English (definitions)</option>
              {languages
                .filter((l) => l.code !== 'en')
                .map((l) => (
                  <option key={l.code} value={l.code}>{l.name}</option>
                ))}
            </select>
            {supportMutation.isError && (
              <p className="text-xs text-red-500">Couldn’t save — try again.</p>
            )}
          </section>
        )}

        <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3">
          <h2 className="font-semibold text-gray-800">Theme</h2>
          <p className="text-xs text-gray-500">
            System follows your device's light/dark preference.
          </p>
          <div className="flex gap-2">
            {THEMES.map((t) => (
              <button
                key={t.value}
                type="button"
                onClick={() => setTheme(t.value)}
                aria-pressed={theme === t.value}
                className={
                  'rounded-lg px-4 py-2 text-sm font-medium border ' +
                  (theme === t.value
                    ? 'bg-lang text-white border-lang'
                    : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50')
                }
                style={{ minHeight: '44px' }}
              >
                {t.label}
              </button>
            ))}
          </div>
        </section>

        <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">
          <h2 className="font-semibold text-gray-800 mb-3">Your progress</h2>
          <div className="grid grid-cols-3 gap-3 text-center">
            <div>
              <div className="text-2xl font-bold text-lang">{stats?.due_count ?? 0}</div>
              <div className="text-xs text-gray-500">due now</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-lang">{stats?.streak_days ?? 0}</div>
              <div className="text-xs text-gray-500">day streak</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-lang">{learned}</div>
              <div className="text-xs text-gray-500">cards learned</div>
            </div>
          </div>
        </section>

        <section className="bg-white rounded-2xl shadow-sm border border-red-100 p-5 space-y-3">
          <h2 className="font-semibold text-red-700">Danger zone</h2>
          <p className="text-xs text-gray-500">
            Resetting deletes cards and their full review history. It cannot
            be undone. Notes and personal sentences are never deleted. To
            reset a single deck, use its "Reset progress" link on the
            dashboard.
          </p>
          <div className="flex flex-col gap-2">
            <button
              type="button"
              onClick={handleResetLanguage}
              disabled={!activeLanguageId || resetMutation.isPending}
              className="rounded-lg px-4 py-2 text-sm font-medium border border-red-200 text-red-700 bg-white hover:bg-red-50 disabled:opacity-50 text-left"
              style={{ minHeight: '44px' }}
            >
              Reset {activeLanguage?.name ?? 'active language'} studies…
            </button>
            <button
              type="button"
              onClick={handleResetAll}
              disabled={resetMutation.isPending}
              className="rounded-lg px-4 py-2 text-sm font-medium border border-red-200 text-red-700 bg-white hover:bg-red-50 disabled:opacity-50 text-left"
              style={{ minHeight: '44px' }}
            >
              Reset ALL studies (every language)…
            </button>
            {resetMutation.isSuccess && (
              <p className="text-xs text-green-700">
                Progress reset ({resetMutation.data.cards_deleted} cards removed).
              </p>
            )}
          </div>
        </section>

        <button
          type="button"
          onClick={handleSignOut}
          className="w-full text-sm text-red-600 hover:text-red-700 hover:underline py-2"
        >
          Sign out
        </button>

        <p className="text-center text-xs text-gray-400">
          <a href="/terms" className="hover:text-lang hover:underline">
            Terms of Service
          </a>
        </p>
        </>
        )}
      </div>
    </div>
  )
}
