import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getLanguages, getProfile, updateProfile } from '../../api/profile'
import { resetProgress } from '../../api/review'
import {
  formatPrice,
  getPlanPrices,
  openBillingPortal,
  startPlanCheckout,
} from '../../api/billing'
import { getDashboardStats } from '../../api/dashboard'
import { usePrefsStore } from '../../stores/prefsStore'
import type { Theme } from '../../stores/prefsStore'
import { supabase } from '../../lib/supabase'
import LanguagePicker from '../../components/LanguagePicker'
import { getGrammarForLanguage } from '../../api/contribute'
import AccountsPanel from '../contribute/AccountsPanel'
import RolesPanel from '../contribute/RolesPanel'
import IssuesPanel from '../contribute/IssuesPanel'
import FeedbackPanel from '../contribute/FeedbackPanel'
import SuggestionsPanel from '../contribute/SuggestionsPanel'
import EngagementPanel from '../contribute/EngagementPanel'
import {
  ReviewPolicyControl,
  TutorModelControl,
  TutorCostsPanel,
} from '../contribute/ContributorPage'
import { useAuthStore } from '../../stores/authStore'

type AccountTab = 'learner' | 'contribute' | 'review' | 'admin'

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

const THEMES: { value: Theme; label: string }[] = [
  { value: 'system', label: 'System' },
  { value: 'light', label: 'Light' },
  { value: 'dark', label: 'Dark' },
]

export default function SettingsPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)
  const theme = usePrefsStore((s) => s.theme)
  const setTheme = usePrefsStore((s) => s.setTheme)
  const sessionSize = usePrefsStore((s) => s.sessionSize)
  const setSessionSize = usePrefsStore((s) => s.setSessionSize)
  const accentsOptional = usePrefsStore((s) => s.accentsOptional)
  const setAccentsOptional = usePrefsStore((s) => s.setAccentsOptional)

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
  const { data: workspace } = useQuery({
    queryKey: ['contribute-grammar', activeLanguageId],
    queryFn: () => getGrammarForLanguage(activeLanguageId!),
    enabled: !!activeLanguageId,
    retry: false,
  })
  const canReview = workspace?.can_review ?? workspace?.is_admin ?? false
  const isAdmin = workspace?.is_admin ?? false
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
  const allPrice = formatPrice(planPrices?.all ?? null)
  const [billingUnavailable, setBillingUnavailable] = useState(false)

  // Upgrade (single → all): dev-mock grants directly; real mode redirects
  // to Stripe Checkout. A 503 means billing isn't launched — say so.
  const reminderMutation = useMutation({
    mutationFn: (patch: { reminder_opt_in?: boolean; reminder_hour_utc?: number }) =>
      updateProfile(patch),
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

  const activeLanguage = languages.find((l) => l.id === activeLanguageId)

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

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-xl mx-auto px-4 py-8 space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">Account</h1>
          <button
            type="button"
            onClick={() => navigate('/')}
            className="text-sm text-lang hover:underline"
          >
            ← Dashboard
          </button>
        </div>

        {/* Role tabs: Learner is always present; the rest appear by role. */}
        {(canReview || isAdmin) && (
          <div
            className="flex rounded-xl border border-gray-200 bg-white overflow-hidden text-sm"
            role="tablist"
            aria-label="Account sections"
          >
            {(
              [
                ['learner', 'Learner', true],
                ['contribute', 'Contribute', true],
                ['review', 'Review', canReview],
                ['admin', 'Admin', isAdmin],
              ] as [AccountTab, string, boolean][]
            )
              .filter(([, , show]) => show)
              .map(([key, label]) => (
                <button
                  key={key}
                  type="button"
                  role="tab"
                  aria-selected={tab === key}
                  onClick={() => setTab(key)}
                  className={`flex-1 px-4 py-2 font-semibold transition-colors ${
                    tab === key
                      ? 'bg-lang text-lang-on'
                      : 'text-gray-500 hover:bg-gray-50'
                  }`}
                >
                  {label}
                </button>
              ))}
          </div>
        )}

        {tab === 'contribute' && activeLanguageId && (
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
        )}

        {tab === 'review' && activeLanguageId && (
          <>
            {canReview && <SuggestionsPanel languageId={activeLanguageId} />}
            <IssuesPanel languageId={activeLanguageId} canResolve={canReview} />
            <FeedbackPanel languageId={activeLanguageId} />
          </>
        )}

        {tab === 'admin' && activeLanguageId && isAdmin && (
          <>
            <EngagementPanel />
            <AccountsPanel languages={languages} selfId={selfId} />
            <RolesPanel languages={languages} />
            <ReviewPolicyControl
              languageId={activeLanguageId}
              policy={workspace?.review_policy ?? 'strict'}
              onChanged={workspaceRefresh}
            />
            <TutorModelControl
              languageId={activeLanguageId}
              current={workspace?.tutor_model ?? null}
              onChanged={workspaceRefresh}
            />
            <TutorCostsPanel />
          </>
        )}

        {tab === 'learner' && (
        <>
        <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3">
          <h2 className="font-semibold text-gray-800">Active language</h2>
          <LanguagePicker />
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

        <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="font-semibold text-gray-800">Accents optional</h2>
              <p className="text-xs text-gray-500">
                Count answers correct even when accents or diacritics are
                missing — “quien” passes for “quién”. The right spelling still
                shows, so you keep learning the marks.
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

        <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="font-semibold text-gray-800">Email reminders</h2>
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
