import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getProfile, updateProfile } from '../../api/profile'
import { getDashboardStats } from '../../api/dashboard'
import { usePrefsStore } from '../../stores/prefsStore'
import type { Theme } from '../../stores/prefsStore'
import { supabase } from '../../lib/supabase'
import LanguagePicker from '../../components/LanguagePicker'

const BATCH_SIZES = [3, 5, 10, 15, 20]

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

  const { data: profile } = useQuery({ queryKey: ['profile'], queryFn: getProfile })
  const { data: stats } = useQuery({
    queryKey: ['dashboard', activeLanguageId],
    queryFn: () => getDashboardStats(activeLanguageId!),
    enabled: !!activeLanguageId,
  })

  const batchMutation = useMutation({
    mutationFn: (batch_size: number) => updateProfile({ batch_size }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['profile'] }),
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
          <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
          <button
            type="button"
            onClick={() => navigate('/')}
            className="text-sm text-indigo-600 hover:underline"
          >
            ← Dashboard
          </button>
        </div>

        <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3">
          <h2 className="font-semibold text-gray-800">Active language</h2>
          <LanguagePicker />
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
                    ? 'bg-indigo-600 text-white border-indigo-600'
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
                    ? 'bg-indigo-600 text-white border-indigo-600'
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
              <div className="text-2xl font-bold text-indigo-600">{stats?.due_count ?? 0}</div>
              <div className="text-xs text-gray-500">due now</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-indigo-600">{stats?.streak_days ?? 0}</div>
              <div className="text-xs text-gray-500">day streak</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-indigo-600">{learned}</div>
              <div className="text-xs text-gray-500">cards learned</div>
            </div>
          </div>
        </section>

        <button
          type="button"
          onClick={handleSignOut}
          className="w-full text-sm text-red-600 hover:text-red-700 hover:underline py-2"
        >
          Sign out
        </button>
      </div>
    </div>
  )
}
