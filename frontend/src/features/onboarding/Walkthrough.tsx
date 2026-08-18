import { useState } from 'react'
import {
  BookOpen,
  Dumbbell,
  GraduationCap,
  Hand,
  Languages,
  Mic,
  PenLine,
  Sprout,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { Trans, useTranslation } from 'react-i18next'
import { usePrefsStore } from '../../stores/prefsStore'
import { TOUR_VERSION } from './tour'

interface Slide {
  icon: LucideIcon
  /** i18n key segment: `tour.slides.<key>.{title,body}` */
  key: string
}

const SLIDES: Slide[] = [
  { icon: Hand, key: 'welcome' },
  { icon: Languages, key: 'language' },
  { icon: Sprout, key: 'learnReview' },
  { icon: Dumbbell, key: 'gym' },
  { icon: GraduationCap, key: 'tutor' },
  { icon: BookOpen, key: 'read' },
  // Speak came after the first tour and was the one thing nobody found.
  { icon: Mic, key: 'speak' },
  { icon: PenLine, key: 'ownText' },
]

/** First-run feature tour: a dismissible slide-through of what the app does.
 * Opened automatically once, or on demand from Account. */
export default function Walkthrough({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation()
  const setWalkthroughDone = usePrefsStore((s) => s.setWalkthroughDone)
  const setWalkthroughVersion = usePrefsStore((s) => s.setWalkthroughVersion)
  const [i, setI] = useState(0)
  const [dontShow, setDontShow] = useState(true)
  const last = i === SLIDES.length - 1
  const slide = SLIDES[i]

  const finish = () => {
    if (dontShow) setWalkthroughDone(true)
    // Recorded whichever way they leave: closing THIS edition means it does
    // not reopen, while a later edition still gets its one showing.
    setWalkthroughVersion(TOUR_VERSION)
    onClose()
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-label={t('tour.ariaLabel')}
    >
      <div className="w-full max-w-md rounded-2xl bg-white shadow-xl overflow-hidden relative">
        <button
          type="button"
          onClick={finish}
          aria-label={t('tour.close')}
          className="absolute top-2.5 end-3 text-gray-300 hover:text-gray-500 text-xl leading-none"
        >
          ×
        </button>
        <div className="px-6 pt-7 pb-5 text-center min-h-56 flex flex-col items-center justify-center">
          <slide.icon
            aria-hidden
            className="mb-3 h-12 w-12 text-lang"
            strokeWidth={1.5}
          />
          <h2 className="text-xl font-bold text-gray-900 mb-2">
            {t(`tour.slides.${slide.key}.title`)}
          </h2>
          <p className="text-gray-600 leading-relaxed">
            <Trans
              i18nKey={`tour.slides.${slide.key}.body`}
              components={{ b: <b /> }}
            />
          </p>
        </div>

        {/* progress dots */}
        <div className="flex justify-center gap-1.5 pb-4">
          {SLIDES.map((_, n) => (
            <button
              key={n}
              type="button"
              aria-label={t('tour.goToStep', { step: n + 1 })}
              onClick={() => setI(n)}
              className={`h-2 rounded-full transition-all ${
                n === i ? 'w-5 bg-lang' : 'w-2 bg-gray-200 hover:bg-gray-300'
              }`}
            />
          ))}
        </div>

        <div className="border-t border-gray-100 px-5 py-3 flex items-center justify-between gap-3">
          <label className="flex items-center gap-2 text-xs text-gray-500 select-none">
            <input
              type="checkbox"
              checked={dontShow}
              onChange={(e) => setDontShow(e.target.checked)}
              className="rounded border-gray-300"
            />
            {t('tour.dontShowAgain')}
          </label>
          <div className="flex items-center gap-2">
            {i > 0 && (
              <button
                type="button"
                onClick={() => setI((n) => n - 1)}
                className="rounded-lg px-3 py-1.5 text-sm text-gray-500 hover:bg-gray-100"
              >
                {t('tour.back')}
              </button>
            )}
            {last ? (
              <button
                type="button"
                onClick={finish}
                className="rounded-lg bg-lang px-4 py-1.5 text-sm font-semibold text-lang-on"
              >
                {t('tour.getStarted')}
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setI((n) => n + 1)}
                className="rounded-lg bg-lang px-4 py-1.5 text-sm font-semibold text-lang-on"
              >
                {t('tour.next')}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
