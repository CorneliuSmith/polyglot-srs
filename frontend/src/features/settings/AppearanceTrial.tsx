import { useTranslation } from 'react-i18next'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  chooseExperimentVariant,
  getMyExperiments,
} from '../../api/profile'

/**
 * "You're trying something new" — the learner's side of a rollout.
 *
 * Only appears when an admin has both switched an experiment on AND opened
 * it to learner choice, so it is invisible on a normal account and cannot
 * leak a rollout that is still being decided internally.
 *
 * It exists for the feedback, not for the choice. Someone who can leave
 * says "I switched back because the borders were too heavy"; someone who is
 * stuck says nothing, or says it to a review page. The escape hatch is what
 * makes the answers usable.
 *
 * The experiment's own name and its variant labels come from the database
 * and are not in the i18n catalogs — everything around them is. That is the
 * deliberate trade: an admin can start a rollout without a translation pass
 * blocking it, and the page furniture still follows the site language.
 */
export default function AppearanceTrial() {
  const { t } = useTranslation()
  const qc = useQueryClient()

  const { data: experiments = [] } = useQuery({
    queryKey: ['my-experiments'],
    queryFn: getMyExperiments,
    retry: false,
  })

  const choose = useMutation({
    mutationFn: ({ key, variant }: { key: string; variant: string }) =>
      chooseExperimentVariant(key, variant),
    onSuccess: () => {
      // The profile carries the resolved variant and UiSkinApplier watches
      // it, so refetching both is what actually repaints the app — no
      // reload, and no second source of truth on the client.
      qc.invalidateQueries({ queryKey: ['my-experiments'] })
      qc.invalidateQueries({ queryKey: ['profile'] })
    },
  })

  if (experiments.length === 0) return null

  return (
    <section
      data-testid="appearance-trial"
      className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-4"
    >
      <div>
        <h2 className="font-semibold text-gray-800">
          {t('settings.trial.title')}
        </h2>
        <p className="text-xs text-gray-500">{t('settings.trial.desc')}</p>
      </div>
      {experiments.map((experiment) => (
        <div key={experiment.key} className="space-y-2">
          <p className="text-sm font-medium text-gray-800">{experiment.name}</p>
          {experiment.description && (
            <p className="text-xs text-gray-500">{experiment.description}</p>
          )}
          <div className="flex flex-wrap gap-2">
            {experiment.variants.map((variant) => (
              <button
                key={variant.key}
                type="button"
                disabled={choose.isPending}
                aria-pressed={experiment.current === variant.key}
                data-testid={`trial-${experiment.key}-${variant.key}`}
                onClick={() =>
                  choose.mutate({ key: experiment.key, variant: variant.key })
                }
                className={
                  'rounded-lg px-4 py-2 text-sm font-medium border ' +
                  (experiment.current === variant.key
                    ? 'bg-lang text-white border-lang'
                    : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50')
                }
                style={{ minHeight: '44px' }}
              >
                {variant.label}
              </button>
            ))}
          </div>
        </div>
      ))}
      {choose.isError && (
        <p className="text-xs text-red-500" data-testid="trial-error">
          {t('settings.trial.saveError')}
        </p>
      )}
      <p className="text-xs text-gray-500">{t('settings.trial.feedback')}</p>
    </section>
  )
}
