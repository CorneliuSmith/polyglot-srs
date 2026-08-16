import { useState, useEffect } from 'react'
import { Lightbulb } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { usePrefsStore } from '../../stores/prefsStore'
import { dayNumber, pickDailyTip, pickTip, type TipContext } from './tips'

/**
 * A small, dismissible learning tip. Two modes, because "don't interrupt me"
 * and "there should be a tip here" are different jobs:
 *
 *   daily (the Study page) — one tip of the day, always present, rotating
 *     each day and dismissible until tomorrow.
 *   throttled (the start of a session) — at most one about every 20 hours,
 *     so it never becomes noise in front of the cards.
 *
 * The Study page used the throttled rule too, which meant its tip was absent
 * roughly 23 hours in 24 (and a session elsewhere could spend the day's
 * allowance first) — indistinguishable, from the outside, from the tips
 * having been removed.
 */
export default function LearningTip({
  context,
  mode = 'throttled',
}: {
  context: TipContext
  mode?: 'daily' | 'throttled'
}) {
  const { t } = useTranslation()
  const enabled = usePrefsStore((s) => s.learningTipsEnabled)
  const seenTipIds = usePrefsStore((s) => s.seenTipIds)
  const lastTipShownAt = usePrefsStore((s) => s.lastTipShownAt)
  const tipDismissedDay = usePrefsStore((s) => s.tipDismissedDay)
  const recordTipShown = usePrefsStore((s) => s.recordTipShown)
  const dismissTipForToday = usePrefsStore((s) => s.dismissTipForToday)

  // Decide once per mount, from the state as it was when the screen opened.
  const [tip] = useState(() =>
    mode === 'daily'
      ? pickDailyTip({
          enabled,
          seenTipIds,
          now: Date.now(),
          context,
          dismissedDay: tipDismissedDay,
        })
      : pickTip({
          enabled,
          seenTipIds,
          lastTipShownAt,
          now: Date.now(),
          context,
        }),
  )
  const [dismissed, setDismissed] = useState(false)

  // Mark it shown (advances the rotation + resets the throttle) as soon as it
  // actually renders — not at pick time, so an unmounted screen doesn't burn a
  // tip the learner never saw. The daily tip is exempt: it is chosen by the
  // date, and recording it would let one glance at the Study page swallow the
  // session tip for the rest of the day.
  useEffect(() => {
    if (tip && mode !== 'daily') recordTipShown(tip.id)
  }, [tip, mode, recordTipShown])

  if (!tip || dismissed) return null

  const close = () => {
    setDismissed(true)
    if (mode === 'daily') dismissTipForToday(dayNumber(Date.now()))
  }

  return (
    <div
      data-testid="learning-tip"
      className="relative rounded-2xl border border-lang/20 bg-lang-soft/60 px-4 py-3 pe-9"
    >
      <button
        type="button"
        onClick={close}
        aria-label={t('tips.dismiss')}
        className="absolute top-2 end-2 h-6 w-6 rounded-full text-gray-500 hover:text-gray-600 hover:bg-white/60 leading-none"
      >
        ×
      </button>
      <p className="text-sm font-semibold text-lang-dark">
        <Lightbulb aria-hidden className="me-1 inline h-4 w-4 align-[-2px]" />
        {t(`tips.items.${tip.id}.title`)}
      </p>
      <p className="mt-1 text-sm text-gray-600">{t(`tips.items.${tip.id}.body`)}</p>
      <p className="mt-1 text-[11px] text-gray-500">{t('tips.footer')}</p>
    </div>
  )
}
