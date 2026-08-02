import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation } from '@tanstack/react-query'
import { MessageSquarePlus, X } from 'lucide-react'
import {
  FEEDBACK_CATEGORIES,
  sendFeedback,
  type FeedbackCategory,
} from '../../api/feedback'
import { usePrefsStore } from '../../stores/prefsStore'

/**
 * "Tell us what you think" — the general feedback channel, on the home page.
 *
 * Every existing channel was scoped to a piece of CONTENT: flag this card,
 * suggest an edit to this sentence, note a problem with this grammar point.
 * A beta user whose keyboard was clipped, or who could not find the Gym, or
 * whose placement test would not start, had nowhere to put any of it — and
 * the reports that did arrive came through other routes entirely, which is
 * evidence the in-app path was missing rather than unused.
 *
 * Design constraints, from what actually stops people sending feedback:
 *   - It is on the home page, not buried in Settings. Broad means findable.
 *   - Category is a chip row, pre-selected, so the form can be sent by typing
 *     one sentence and pressing one button.
 *   - The current page and language ride along automatically. "Which screen
 *     was this?" is the first triage question and the reporter should not
 *     have to answer it.
 *   - It says what happens next. A suggestion box that swallows the message
 *     without acknowledgement trains people to stop using it.
 */
export default function FeedbackButton({ page }: { page: string }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const [category, setCategory] = useState<FeedbackCategory>('bug')
  const [message, setMessage] = useState('')
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)

  const mutation = useMutation({
    mutationFn: () =>
      sendFeedback({ category, message, languageId: activeLanguageId, page }),
  })

  const close = () => {
    setOpen(false)
    // Reset only AFTER a successful send. A failed one keeps the text, so a
    // dropped connection doesn't throw away what someone just wrote.
    if (mutation.isSuccess) {
      setMessage('')
      setCategory('bug')
      mutation.reset()
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        data-testid="feedback-open"
        onClick={() => setOpen(true)}
        className="w-full flex items-center justify-center gap-2 rounded-2xl border border-dashed border-gray-300 bg-white/60 px-4 py-3 text-sm text-gray-600 hover:border-lang hover:text-lang"
        style={{ minHeight: '44px' }}
      >
        <MessageSquarePlus aria-hidden className="h-4 w-4" />
        {t('feedback.open')}
      </button>
    )
  }

  return (
    <section
      data-testid="feedback-form"
      className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm space-y-3"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold text-gray-800">{t('feedback.title')}</h2>
          <p className="text-xs text-gray-500">{t('feedback.desc')}</p>
        </div>
        <button
          type="button"
          onClick={close}
          aria-label={t('feedback.closeAria')}
          className="shrink-0 text-gray-400 hover:text-gray-600"
        >
          <X aria-hidden className="h-4 w-4" />
        </button>
      </div>

      {mutation.isSuccess ? (
        <div className="space-y-3">
          <p className="rounded-xl bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
            {t('feedback.sent')}
          </p>
          <button
            type="button"
            onClick={close}
            className="rounded-lg bg-lang px-4 py-2 text-sm font-semibold text-lang-on hover:bg-lang-dark"
          >
            {t('feedback.done')}
          </button>
        </div>
      ) : (
        <>
          <div className="flex flex-wrap gap-2">
            {FEEDBACK_CATEGORIES.map((c) => (
              <button
                key={c.value}
                type="button"
                onClick={() => setCategory(c.value)}
                aria-pressed={category === c.value}
                className={
                  'rounded-full border px-3 py-1.5 text-xs font-medium ' +
                  (category === c.value
                    ? 'border-lang bg-lang text-lang-on'
                    : 'border-gray-300 bg-white text-gray-600 hover:bg-gray-50')
                }
              >
                {t(`feedback.categories.${c.value}`)}
              </button>
            ))}
          </div>

          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            rows={4}
            maxLength={4000}
            aria-label={t('feedback.yourFeedback')}
            placeholder={t('feedback.placeholder')}
            className="w-full rounded-xl border border-gray-300 p-3 text-sm"
          />

          {mutation.isError && (
            <p className="text-sm text-red-600">{t('feedback.sendError')}</p>
          )}

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => mutation.mutate()}
              disabled={message.trim().length < 3 || mutation.isPending}
              className="rounded-lg bg-lang px-4 py-2 text-sm font-semibold text-lang-on hover:bg-lang-dark disabled:opacity-50"
              style={{ minHeight: '44px' }}
            >
              {mutation.isPending ? t('feedback.sending') : t('feedback.send')}
            </button>
            <span className="text-[11px] text-gray-400">
              {t('feedback.screenNote')}
            </span>
          </div>
        </>
      )}
    </section>
  )
}
