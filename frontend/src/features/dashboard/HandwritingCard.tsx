import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { getHandProfile } from '../../api/write'

/**
 * Handwriting on the Progress page: the reader's accuracy on this hand
 * (by the writer's own verdicts), the legibility trend of the last
 * checks, and the letters it trips on. Hidden until there is a check to
 * show — a card of zeros teaches nothing.
 */
export default function HandwritingCard({ languageId }: { languageId: string }) {
  const { t } = useTranslation()
  const { data: profile } = useQuery({
    queryKey: ['hand-profile', languageId],
    queryFn: () => getHandProfile(languageId),
    retry: false,
  })
  if (!profile?.available) return null
  const r = profile.readout
  if (r.history.length === 0 && r.total === 0) return null
  const last = r.history.slice(-12)
  return (
    <div
      data-testid="handwriting-card"
      className="bg-white rounded-2xl shadow-sm border border-gray-100 p-4 space-y-3"
    >
      <h2 className="text-xs uppercase tracking-wide text-gray-500">
        {t('dashboard.handTitle')}
      </h2>
      {r.total > 0 && (
        <p className="text-sm text-gray-800">
          {t('write.accuracy', { right: r.right, total: r.total })}
        </p>
      )}
      {last.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 mb-1">
            {t('dashboard.handLegibility', {
              mean: r.legibility_mean != null ? r.legibility_mean.toFixed(1) : '—',
            })}
          </p>
          {/* Twelve most recent checks as a strip of bars, 1–5. */}
          <div data-testid="handwriting-trend" className="flex items-end gap-1 h-8">
            {last.map((v, i) => (
              <span
                key={i}
                className="w-3 rounded-sm bg-lang"
                style={{ height: `${(v / 5) * 100}%`, opacity: 0.4 + (i / last.length) * 0.6 }}
                aria-label={`${v}/5`}
              />
            ))}
          </div>
        </div>
      )}
      {r.letters_to_watch.length > 0 && (
        <p className="text-sm text-gray-700">
          {t('write.trips')}{' '}
          <span className="font-semibold text-gray-900">
            {r.letters_to_watch.map((x) => x.letter).join(' ')}
          </span>
        </p>
      )}
    </div>
  )
}
