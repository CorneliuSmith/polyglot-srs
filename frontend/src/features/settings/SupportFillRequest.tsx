import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Loader2 } from 'lucide-react'
import { getTranslationRequest, requestTranslation } from '../../api/profile'

/**
 * "Fill my language on this course" — the learner's side of the admin's
 * auto-translate toggle (migration 20261024).
 *
 * The copy is the load-bearing part. A switched-off course is NOT an
 * untranslated one: the backend always translates what a learner is
 * waiting on, and buys a starter corpus for a course in real use
 * (services/auto_translate.py). What it withholds is the full backlog
 * drain, because that costs the operator real money per word on every
 * course at once. So this says what is already happening, and offers to
 * register a want — never "your language is not supported", which would
 * be both frightening and false.
 *
 * Renders nothing at all when there is nothing to offer: English help,
 * a course already draining, an ask already made (that shows its state),
 * or a database without the migration.
 */
export default function SupportFillRequest({ languageId }: { languageId: string }) {
  const { t } = useTranslation()
  const qc = useQueryClient()
  const [note, setNote] = useState('')
  const { data } = useQuery({
    queryKey: ['translation-request', languageId],
    queryFn: () => getTranslationRequest(languageId),
    retry: false,
  })
  const ask = useMutation({
    mutationFn: () => requestTranslation(languageId, note.trim() || undefined),
    onSuccess: (next) => qc.setQueryData(['translation-request', languageId], next),
  })

  if (!data || !data.available || !data.locale) return null
  // Already draining: nothing to ask for, and saying so would be noise.
  if (data.auto_translate_enabled) return null

  const language = data.locale_name ?? data.locale

  if (data.request) {
    return (
      <div
        data-testid="support-fill-asked"
        className="rounded-xl border border-green-200 bg-green-50 p-3 text-sm text-green-900"
      >
        <p className="flex items-center gap-1.5 font-semibold">
          <Check className="h-4 w-4" aria-hidden />
          {data.request.status === 'fulfilled'
            ? t('settings.support.fillOn', { language })
            : t('settings.support.fillAsked', { language })}
        </p>
        {data.request.status !== 'fulfilled' && (
          <p className="mt-1 text-xs text-green-800">{t('settings.support.fillMeanwhile')}</p>
        )}
      </div>
    )
  }

  return (
    <div
      data-testid="support-fill-ask"
      className="rounded-xl border border-gray-200 bg-gray-50 p-3 space-y-2"
    >
      <p className="text-sm text-gray-800">{t('settings.support.fillState', { language })}</p>
      <p className="text-xs text-gray-600">{t('settings.support.fillMeanwhile')}</p>
      <label className="block">
        <span className="sr-only">{t('settings.support.fillNoteLabel')}</span>
        <input
          type="text"
          value={note}
          maxLength={500}
          onChange={(e) => setNote(e.target.value)}
          placeholder={t('settings.support.fillNotePlaceholder')}
          data-testid="support-fill-note"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
        />
      </label>
      <button
        type="button"
        onClick={() => ask.mutate()}
        disabled={ask.isPending || !data.can_ask}
        data-testid="support-fill-button"
        className="inline-flex items-center gap-1.5 rounded-xl bg-lang px-3 py-2 text-sm font-bold text-lang-on disabled:opacity-50"
      >
        {ask.isPending && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
        {t('settings.support.fillAsk', { language })}
      </button>
      {ask.isError && (
        <p className="text-xs text-red-600">{t('settings.support.fillError')}</p>
      )}
    </div>
  )
}
