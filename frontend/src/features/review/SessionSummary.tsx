interface SessionSummaryProps {
  accuracy: number
  totalTimeMs: number
  cardsReviewed: number
  /** shown under the title — e.g. cram's "nothing was recorded" notice */
  note?: string
  onFinish: () => void
}

function formatTime(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes} min ${seconds} sec`
}

export default function SessionSummary({
  accuracy,
  totalTimeMs,
  cardsReviewed,
  note,
  onFinish,
}: SessionSummaryProps) {
  const percent = Math.round(accuracy * 100)

  let accuracyColor = 'text-red-600'
  if (percent >= 80) {
    accuracyColor = 'text-green-600'
  } else if (percent >= 60) {
    accuracyColor = 'text-yellow-600'
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 max-w-sm w-full text-center space-y-6">
        <h1 className="text-2xl font-bold text-gray-900">Session Complete</h1>
        {note && <p className="text-xs text-gray-500">{note}</p>}

        <div className="space-y-4">
          <div>
            <p className="text-sm text-gray-500 mb-1">Accuracy</p>
            <p className={`text-5xl font-bold ${accuracyColor}`} data-testid="accuracy">
              {percent}%
            </p>
          </div>

          <div>
            <p className="text-sm text-gray-500 mb-1">Time Spent</p>
            <p className="text-xl font-semibold text-gray-800" data-testid="time-spent">
              {formatTime(totalTimeMs)}
            </p>
          </div>

          <div>
            <p className="text-sm text-gray-500 mb-1">Cards Reviewed</p>
            <p className="text-xl font-semibold text-gray-800" data-testid="cards-reviewed">
              {cardsReviewed}
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={onFinish}
          className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl px-6 py-3 text-sm transition-colors"
          style={{ minHeight: '44px' }}
        >
          Back to Dashboard
        </button>
      </div>
    </div>
  )
}
