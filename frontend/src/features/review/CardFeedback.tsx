import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation } from '@tanstack/react-query'
import { submitCardFeedback, type CardFeedbackField } from '../../api/review'

// The chips, in the order a card reads top to bottom. Six of the column's
// seven values: 'answer' stays something a learner says in words.
const FIELDS: { value: CardFeedbackField; key: string }[] = [
  { value: 'sentence', key: 'review.fieldSentence' },
  { value: 'hint', key: 'review.fieldHint' },
  { value: 'translation', key: 'review.fieldTranslation' },
  { value: 'definition', key: 'review.fieldDefinition' },
  { value: 'explanation', key: 'review.fieldExplanation' },
  { value: 'other', key: 'review.fieldOther' },
]

/**
 * Lets a learner flag a problem with the card they just answered. Collapsed by
 * default; the feedback is routed to contributors for that language.
 *
 * The field chips (migration 20261030, plan A6) are the reviewer form's
 * "what needs fixing?" brought to the learner: a report that names the layer
 * can be routed to the check that owns it, and one that does not is a
 * sentence someone has to read first. Choosing one is optional — the message
 * alone still sends, as it always did. The locale the session is rendering
 * and the drill it rendered ride along so the row can say which overlay and
 * which sentence, not just which point.
 */
export default function CardFeedback({
  cardId,
  locale = null,
  drillId = null,
}: {
  cardId: string
  /** The locale overlay this session is rendering, for the row. */
  locale?: string | null
  /** The drill actually shown, when the card payload carries one. */
  drillId?: string | null
}) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const [message, setMessage] = useState('')
  const [field, setField] = useState<CardFeedbackField | null>(null)

  const mutation = useMutation({
    mutationFn: () =>
      submitCardFeedback(cardId, message.trim(), {
        field,
        drill_id: drillId,
        locale,
      }),
  })

  if (mutation.isSuccess) {
    return <p className="text-xs text-gray-500">{t('review.feedbackThanks')}</p>
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="text-xs text-gray-500 hover:text-gray-600 hover:underline"
      >
        {t('review.reportIssue')}
      </button>
    )
  }

  return (
    <div className="space-y-1">
      <div
        role="group"
        aria-label={t('review.fieldPrompt')}
        className="flex flex-wrap justify-center gap-1"
      >
        {FIELDS.map((f) => {
          const selected = field === f.value
          return (
            <button
              key={f.value}
              type="button"
              aria-pressed={selected}
              // A second tap clears it: none selected is a valid answer.
              onClick={() => setField(selected ? null : f.value)}
              className={
                'rounded-full border px-2.5 py-0.5 text-xs ' +
                (selected
                  ? 'border-gray-700 bg-gray-700 text-white'
                  : 'border-gray-300 text-gray-600 hover:border-gray-500')
              }
            >
              {t(f.key)}
            </button>
          )
        })}
      </div>
      <textarea
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        rows={2}
        placeholder={t('review.reportPlaceholder')}
        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-lang"
      />
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => mutation.mutate()}
          disabled={!message.trim() || mutation.isPending}
          className="bg-gray-700 hover:bg-gray-800 disabled:opacity-50 text-white rounded-lg px-3 py-1.5 text-xs"
        >
          {mutation.isPending ? t('review.sending') : t('review.sendFeedback')}
        </button>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="text-xs text-gray-500 hover:underline"
        >
          {t('review.cancel')}
        </button>
        {mutation.isError && <span className="text-xs text-red-500">{t('review.couldNotSend')}</span>}
      </div>
    </div>
  )
}
