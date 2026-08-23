import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { sendFeedback } from '../../api/feedback'
import {
  chooseExperimentVariant,
  getMyExperiments,
} from '../../api/profile'

/**
 * "You're trying something new" — the learner's side of a rollout.
 *
 * Appears in two modes, decided by the server (see /api/auth/experiments):
 * with switch buttons when the admin opened the experiment to learner
 * choice, and WITHOUT them when the admin chooses for the account (the
 * owner's mode: "I as admin choose for the account") — then it renders
 * only for accounts actually placed on a non-default version, telling
 * them what they're on and asking what they think. Invisible on a normal
 * account either way; an experiment still being decided never leaks.
 *
 * Either mode exists for the feedback: the box below sends the sentence
 * from right here, and the server stamps which version the sender was on.
 *
 * The experiment's own name and its variant labels come from the database
 * and are not in the i18n catalogs — everything around them is. That is the
 * deliberate trade: an admin can start a rollout without a translation pass
 * blocking it, and the page furniture still follows the site language.
 */
export default function AppearanceTrial() {
  const { t } = useTranslation()
  const qc = useQueryClient()
  const [note, setNote] = useState('')

  // The reason the trial exists is the sentence, so the sentence is asked
  // for HERE — not via a button on another page. Sent with no language
  // (this is about the app, not a course) and the server stamps which
  // variant the sender was on, so "I like C" arrives already meaning
  // something. Category 'other': it is an opinion, not a bug report.
  const send = useMutation({
    mutationFn: () =>
      sendFeedback({
        category: 'other',
        message: note,
        languageId: null,
        page: 'appearance-trial',
      }),
  })

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
          {experiment.learner_choice ? (
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
          ) : (
            /* The admin chose for this account: say which version, offer
               no switch the server would refuse anyway. */
            <p
              className="w-fit rounded-lg border border-lang bg-lang-soft/50 px-4 py-2 text-sm font-medium text-gray-800"
              data-testid={`trial-assigned-${experiment.key}`}
            >
              {experiment.variants.find((v) => v.key === experiment.current)
                ?.label ?? experiment.current}
            </p>
          )}
        </div>
      ))}
      {choose.isError && (
        <p className="text-xs text-red-500" data-testid="trial-error">
          {t('settings.trial.saveError')}
        </p>
      )}
      {send.isSuccess ? (
        <p
          className="rounded-xl bg-emerald-50 px-3 py-2 text-sm text-emerald-800"
          data-testid="trial-feedback-sent"
        >
          {t('settings.trial.sent')}
        </p>
      ) : (
        <div className="space-y-2">
          <p className="text-xs text-gray-500">{t('settings.trial.feedback')}</p>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={2}
            maxLength={4000}
            aria-label={t('settings.trial.feedback')}
            placeholder={t('settings.trial.placeholder')}
            data-testid="trial-feedback-note"
            className="w-full rounded-xl border border-gray-300 p-3 text-sm"
          />
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => send.mutate()}
              disabled={note.trim().length < 3 || send.isPending}
              data-testid="trial-feedback-send"
              className="rounded-lg bg-lang px-4 py-2 text-sm font-semibold text-lang-on hover:bg-lang-dark disabled:opacity-50"
            >
              {send.isPending
                ? t('settings.trial.sending')
                : t('settings.trial.send')}
            </button>
            {send.isError && (
              <p className="text-xs text-red-500" data-testid="trial-feedback-error">
                {t('settings.trial.sendError')}
              </p>
            )}
          </div>
        </div>
      )}
    </section>
  )
}
