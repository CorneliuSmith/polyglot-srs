import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { startLearnSession } from '../../api/review'
import { usePrefsStore } from '../../stores/prefsStore'

export default function LearnPage() {
  const navigate = useNavigate()
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)

  const learnMutation = useMutation({
    mutationFn: () => startLearnSession(activeLanguageId!),
  })

  useEffect(() => {
    if (activeLanguageId) {
      learnMutation.mutate()
    }
    // Run once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (learnMutation.isPending) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-500">Adding new cards…</p>
      </div>
    )
  }

  if (learnMutation.isError) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="text-center space-y-4">
          <p className="text-xl text-red-600">Failed to load new cards.</p>
          <p className="text-sm text-gray-500">Please try again later.</p>
          <button
            type="button"
            onClick={() => navigate('/')}
            className="text-indigo-600 hover:underline text-sm"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    )
  }

  if (learnMutation.isSuccess) {
    const { added } = learnMutation.data

    if (added === 0) {
      return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
          <div className="text-center space-y-4">
            <p className="text-xl text-gray-700">No new cards available.</p>
            <p className="text-sm text-gray-500">
              Subscribe to more lists in your profile.
            </p>
            <button
              type="button"
              onClick={() => navigate('/')}
              className="text-indigo-600 hover:underline text-sm"
            >
              Back to Dashboard
            </button>
          </div>
        </div>
      )
    }

    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 max-w-sm w-full text-center space-y-6">
          <h1 className="text-2xl font-bold text-gray-900">Cards Added!</h1>
          <p className="text-4xl font-bold text-indigo-600">{added}</p>
          <p className="text-gray-600">new cards added to your review queue.</p>
          <button
            type="button"
            onClick={() => navigate('/review')}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl px-6 py-3 text-sm transition-colors"
            style={{ minHeight: '44px' }}
          >
            Start Reviewing
          </button>
        </div>
      </div>
    )
  }

  return null
}
