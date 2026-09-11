import { useTranslation } from 'react-i18next'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getHandProfile, resetHand, setHandAdapt } from '../../api/write'
import { getLanguages } from '../../api/profile'
import { usePrefsStore } from '../../stores/prefsStore'

/**
 * "Adapt to my handwriting" — the one place ink is ever kept, and the
 * learner's switch over it (docs/plans/handwriting.md, §11). On by
 * default; off deletes every sample and habit in every language. Reset
 * forgets one language, or all, without turning it off.
 *
 * Hidden until the migration is present: a switch that cannot save is
 * worse than no switch.
 */
export default function HandwritingPanel() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)
  const { data: languages = [] } = useQuery({ queryKey: ['languages'], queryFn: getLanguages })
  const language = languages.find((l) => l.id === activeLanguageId)
  const name = language?.name ?? t('settings.hand.thisLanguage')

  const { data: profile, isError } = useQuery({
    queryKey: ['hand-profile', activeLanguageId],
    queryFn: () => getHandProfile(activeLanguageId!),
    enabled: !!activeLanguageId,
    retry: false,
  })
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['hand-profile'] })
  const toggle = useMutation({
    mutationFn: (adapt: boolean) => setHandAdapt(adapt),
    onSuccess: invalidate,
  })
  const reset = useMutation({
    mutationFn: (languageId?: string) => resetHand(languageId),
    onSuccess: invalidate,
  })

  if (isError || !profile || !profile.available) return null
  const adapt = profile.adapt

  const flip = () => {
    // Off deletes what was kept, so it asks; on just starts collecting.
    if (adapt && !window.confirm(t('settings.hand.offConfirm'))) return
    toggle.mutate(!adapt)
  }
  const confirmReset = (languageId?: string) => {
    const scope = languageId ? name : t('settings.hand.all')
    if (window.confirm(t('settings.hand.resetConfirm', { name: scope }))) reset.mutate(languageId)
  }

  return (
    <section
      data-testid="hand-panel"
      className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="font-semibold text-gray-800">{t('settings.hand.title')}</h2>
          <p className="text-xs text-gray-500">{t('settings.hand.desc')}</p>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={adapt}
          aria-label={t('settings.hand.title')}
          data-testid="hand-toggle"
          disabled={toggle.isPending}
          onClick={flip}
          className={
            'relative shrink-0 inline-flex h-6 w-11 items-center rounded-full transition-colors ' +
            (adapt ? 'bg-lang' : 'bg-gray-300')
          }
        >
          <span
            className={
              'inline-block h-5 w-5 transform rounded-full bg-white transition-transform ' +
              (adapt ? 'translate-x-5' : 'translate-x-1')
            }
          />
        </button>
      </div>
      {adapt && (
        <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
          <p data-testid="hand-kept" className="text-gray-600">
            {profile.samples > 0
              ? t('settings.hand.kept', {
                  count: profile.samples, confirmed: profile.confirmed, language: name,
                })
              : t('settings.hand.none', { language: name })}
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => confirmReset(activeLanguageId ?? undefined)}
              disabled={reset.isPending || !activeLanguageId || profile.samples === 0}
              data-testid="hand-reset"
              className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              {t('settings.hand.reset', { language: name })}
            </button>
            <button
              type="button"
              onClick={() => confirmReset(undefined)}
              disabled={reset.isPending}
              data-testid="hand-reset-all"
              className="rounded-lg px-3 py-1.5 text-xs font-semibold text-gray-500 hover:text-red-700"
            >
              {t('settings.hand.resetAll')}
            </button>
          </div>
        </div>
      )}
    </section>
  )
}
