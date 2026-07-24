import { useState, useEffect } from 'react'
import { usePrefsStore } from '../../stores/prefsStore'
import { pickTip, type TipContext } from './tips'

/**
 * A small, dismissible learning tip. Renders nothing most of the time — a tip
 * is chosen at most about once a day (see pickTip), never repeats until the set
 * is exhausted, and can be switched off entirely in Settings. Placed on the
 * dashboard and at the start of a session.
 */
export default function LearningTip({ context }: { context: TipContext }) {
  const enabled = usePrefsStore((s) => s.learningTipsEnabled)
  const seenTipIds = usePrefsStore((s) => s.seenTipIds)
  const lastTipShownAt = usePrefsStore((s) => s.lastTipShownAt)
  const recordTipShown = usePrefsStore((s) => s.recordTipShown)

  // Decide once per mount, from the state as it was when the screen opened.
  const [tip] = useState(() =>
    pickTip({
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
  // tip the learner never saw.
  useEffect(() => {
    if (tip) recordTipShown(tip.id)
  }, [tip, recordTipShown])

  if (!tip || dismissed) return null

  return (
    <div
      data-testid="learning-tip"
      className="relative rounded-2xl border border-lang/20 bg-lang-soft/60 px-4 py-3 pr-9"
    >
      <button
        type="button"
        onClick={() => setDismissed(true)}
        aria-label="Dismiss tip"
        className="absolute top-2 right-2 h-6 w-6 rounded-full text-gray-400 hover:text-gray-600 hover:bg-white/60 leading-none"
      >
        ×
      </button>
      <p className="text-sm font-semibold text-lang-dark">
        <span aria-hidden className="mr-1">💡</span>
        {tip.title}
      </p>
      <p className="mt-1 text-sm text-gray-600">{tip.body}</p>
      <p className="mt-1 text-[11px] text-gray-400">
        Learning tip · turn these off in Settings
      </p>
    </div>
  )
}
