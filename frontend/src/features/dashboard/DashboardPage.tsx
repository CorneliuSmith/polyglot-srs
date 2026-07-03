import { Navigate, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getDashboardStats } from '../../api/dashboard'
import { getMyRoles } from '../../api/contribute'
import { getOnboardingStatus } from '../../api/onboarding'
import { usePrefsStore } from '../../stores/prefsStore'
import LanguagePicker from '../../components/LanguagePicker'
import DueCount from './DueCount'
import StreakBadge from './StreakBadge'
import CEFRProgress from './CEFRProgress'

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
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)

  // First-run users are routed into onboarding before they can study.
  const { data: onboarding, isLoading: onboardingLoading } = useQuery({
    queryKey: ['onboarding-status'],
    queryFn: getOnboardingStatus,
  })

  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard', activeLanguageId],
    queryFn: () => getDashboardStats(activeLanguageId!),
    enabled: !!activeLanguageId,
  })

  // Surfaces the Contribute link only to users who hold a contributor role.
  const { data: roleInfo } = useQuery({
    queryKey: ['my-roles'],
    queryFn: getMyRoles,
    retry: false,
  })
  const canContribute = (roleInfo?.roles?.length ?? 0) > 0

  // Learning routes through /learn, which TEACHES the new items (lesson
  // pages) before they are ever quizzed.
  const handleLearn = () => {
    if (activeLanguageId) navigate('/learn?type=vocabulary')
  }

  const handleLearnGrammar = () => {
    if (activeLanguageId) navigate('/learn?type=grammar')
  }

  const handleReview = () => {
    navigate('/review')
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
          <button
            type="button"
            onClick={() => navigate('/settings')}
            aria-label="Settings"
            className="text-sm text-gray-500 hover:text-indigo-600"
          >
            Settings
          </button>
        </div>

        {/* Language picker */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Active Language
          </label>
          <LanguagePicker />
        </div>

        {/* Stats grid */}
        {isLoading || !stats ? (
          <div className="grid grid-cols-2 gap-4">
            <SkeletonCard />
            <SkeletonCard />
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4">
            <DueCount count={stats.due_count} />
            <StreakBadge days={stats.streak_days} />
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

        {/* Action buttons */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <button
            type="button"
            onClick={handleLearn}
            disabled={isLoading || !activeLanguageId}
            className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold rounded-xl px-6 py-3 text-sm transition-colors"
            style={{ minHeight: '44px' }}
          >
            Learn Vocabulary
          </button>
          <button
            type="button"
            onClick={handleLearnGrammar}
            disabled={isLoading || !activeLanguageId}
            className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold rounded-xl px-6 py-3 text-sm transition-colors"
            style={{ minHeight: '44px' }}
          >
            Learn Grammar
          </button>
          <button
            type="button"
            onClick={handleReview}
            disabled={isLoading || !stats || stats.due_count === 0}
            className="w-full bg-white hover:bg-gray-50 disabled:opacity-50 text-indigo-600 font-semibold rounded-xl px-6 py-3 text-sm border border-indigo-200 transition-colors sm:col-span-2"
            style={{ minHeight: '44px' }}
          >
            Review Due Cards
            {stats ? ` (${stats.due_count})` : ''}
          </button>
        </div>

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
          <span aria-hidden className="text-indigo-500">→</span>
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
          <span aria-hidden className="text-indigo-500">→</span>
        </button>

        {/* Contributor link — only for users with a role */}
        {canContribute && (
          <button
            type="button"
            onClick={() => navigate('/contribute')}
            className="w-full text-sm text-gray-500 hover:text-indigo-600 hover:underline text-left"
          >
            Contribute grammar notes →
          </button>
        )}
      </div>
    </div>
  )
}
