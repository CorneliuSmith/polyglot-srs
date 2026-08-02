import { useTranslation } from 'react-i18next'

interface SessionSummaryProps {
  accuracy: number
  totalTimeMs: number
  cardsReviewed: number
  /** shown under the title — e.g. cram's "nothing was recorded" notice */
  note?: string
  onFinish: () => void
}

export default function SessionSummary({
  accuracy,
  totalTimeMs,
  cardsReviewed,
  note,
  onFinish,
}: SessionSummaryProps) {
  const { t } = useTranslation()
  const percent = Math.round(accuracy * 100)

  const totalSeconds = Math.floor(totalTimeMs / 1000)
  const timeSpent = `${t('review.durationMin', {
    count: Math.floor(totalSeconds / 60),
  })} ${t('review.durationSec', { count: totalSeconds % 60 })}`

  let accuracyColor = 'text-red-600'
  if (percent >= 80) {
    accuracyColor = 'text-green-600'
  } else if (percent >= 60) {
    accuracyColor = 'text-yellow-600'
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 max-w-sm w-full text-center space-y-6">
        <h1 className="text-2xl font-bold text-gray-900">{t('review.sessionComplete')}</h1>
        {note && <p className="text-xs text-gray-500">{note}</p>}

        <div className="space-y-4">
          <div>
            <p className="text-sm text-gray-500 mb-1">{t('review.accuracy')}</p>
            <p className={`text-5xl font-bold ${accuracyColor}`} data-testid="accuracy">
              {percent}%
            </p>
          </div>

          <div>
            <p className="text-sm text-gray-500 mb-1">{t('review.timeSpent')}</p>
            <p className="text-xl font-semibold text-gray-800" data-testid="time-spent">
              {timeSpent}
            </p>
          </div>

          <div>
            <p className="text-sm text-gray-500 mb-1">{t('review.cardsReviewed')}</p>
            <p className="text-xl font-semibold text-gray-800" data-testid="cards-reviewed">
              {cardsReviewed}
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={onFinish}
          className="w-full bg-lang hover:bg-lang-dark text-lang-on font-semibold rounded-xl px-6 py-3 text-sm transition-colors"
          style={{ minHeight: '44px' }}
        >
          {t('review.backToDashboard')}
        </button>
      </div>
    </div>
  )
}
