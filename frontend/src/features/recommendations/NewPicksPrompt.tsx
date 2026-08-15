import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Sparkles, X } from 'lucide-react'
import {
  getUnseenRecommendations,
  markRecommendationsSeen,
} from '../../api/recommendations'
import { usePrefsStore } from '../../stores/prefsStore'

/**
 * "Your picks for this week are ready" — on the dashboard, once per batch.
 *
 * Recommendations were generated weekly and then sat there: the only way to
 * find them was to remember the page existed and go looking. So most batches
 * were never seen, which makes the whole feature (and the model call behind
 * each batch) wasted effort.
 *
 * Once per BATCH rather than on a timer: the prompt shows while there's a
 * batch newer than the learner's last look, and goes quiet the moment they
 * open it or dismiss it. Since batches are weekly, that is "once a week" in
 * practice without needing a schedule of its own — and it can never nag
 * about something they've already read.
 */
export default function NewPicksPrompt() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)

  const { data: batch } = useQuery({
    queryKey: ['recommendations-unseen', activeLanguageId],
    queryFn: () => getUnseenRecommendations(activeLanguageId!),
    enabled: !!activeLanguageId,
    retry: false,
    staleTime: 5 * 60 * 1000,
  })

  const dismiss = useMutation({
    mutationFn: markRecommendationsSeen,
    // Optimistic: the prompt disappears on click, not on the round trip.
    onMutate: () =>
      queryClient.setQueryData(['recommendations-unseen', activeLanguageId], null),
  })

  if (!batch || batch.items.length === 0) return null

  const preview = batch.items.slice(0, 2)

  return (
    <section
      data-testid="new-picks-prompt"
      className="rounded-2xl border border-lang/25 bg-lang-soft/60 p-4 space-y-3"
    >
      <div className="flex items-start gap-2">
        <Sparkles aria-hidden className="mt-0.5 h-4 w-4 shrink-0 text-lang" />
        <div className="min-w-0 flex-1">
          <h2 className="font-semibold text-gray-800">
            {t('recos.picksReady')}
          </h2>
          <p className="text-xs text-gray-600">
            {t('recos.picksCount', { count: batch.items.length })}
          </p>
        </div>
        <button
          type="button"
          onClick={() => dismiss.mutate()}
          aria-label={t('recos.dismissPicks')}
          className="shrink-0 text-gray-500 hover:text-gray-600"
        >
          <X aria-hidden className="h-4 w-4" />
        </button>
      </div>

      <ul className="space-y-1">
        {preview.map((item, i) => (
          <li key={i} className="text-sm text-gray-700">
            <span className="text-[11px] uppercase tracking-wide text-gray-500">
              {t(`recos.mediaTypes.${item.type}`, { defaultValue: item.type })}
            </span>{' '}
            <span className="font-medium">{item.title}</span>
          </li>
        ))}
        {batch.items.length > preview.length && (
          <li className="text-xs text-gray-500">
            {t('recos.andMore', { count: batch.items.length - preview.length })}
          </li>
        )}
      </ul>

      <button
        type="button"
        onClick={() => {
          // Opening them IS seeing them — no reason to make someone dismiss
          // a prompt for something they just acted on.
          dismiss.mutate()
          navigate('/recommendations')
        }}
        className="rounded-lg bg-lang px-4 py-2 text-sm font-semibold text-lang-on hover:bg-lang-dark"
        style={{ minHeight: '44px' }}
      >
        {t('recos.seePicks')}
      </button>
    </section>
  )
}
