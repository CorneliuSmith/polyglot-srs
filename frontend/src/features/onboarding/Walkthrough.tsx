import { useState } from 'react'
import { usePrefsStore } from '../../stores/prefsStore'

interface Slide {
  icon: string
  title: string
  body: React.ReactNode
}

const SLIDES: Slide[] = [
  {
    icon: '👋',
    title: 'Welcome — here’s the quick tour',
    body: 'Five things worth knowing before you dive in. Swipe through, then get learning. You can reopen this any time from the “?” on your dashboard.',
  },
  {
    icon: '🔤',
    title: 'Letters & Sounds',
    body: 'New to the script? Start here. Every letter, its variants, and how to say it — right on your dashboard. Especially handy for Russian, Arabic, Greek, Hindi, and Thai.',
  },
  {
    icon: '🌱',
    title: 'Learn vs. Review',
    body: (
      <>
        <b>Learn</b> introduces new words and grammar. <b>Review</b> brings them
        back right before you’d forget — that spacing is what moves them into
        long-term memory. Learn a little, then let Review do the heavy lifting.
      </>
    ),
  },
  {
    icon: '🧑‍🏫',
    title: 'AI Tutor — Practice vs. Reference',
    body: (
      <>
        <b>Practice</b> drills you on the language and saves what you covered to
        your profile, so lessons build on each other. <b>Reference</b> is for a
        quick question — a straight answer, no drills, and nothing saved. Use
        Practice to study, Reference to just ask.
      </>
    ),
  },
  {
    icon: '📖',
    title: 'Read',
    body: 'Read short passages graded to your level and tap any word for its meaning — the fastest way to turn vocabulary into real reading.',
  },
  {
    icon: '✍️',
    title: 'Bring your own text',
    body: 'Paste something you actually want to read into the Reader — a song, an article, a message — and study the words that matter to you.',
  },
]

/** First-run feature tour: a dismissible slide-through of what the app does.
 * Opened automatically once, or on demand from Account. */
export default function Walkthrough({ onClose }: { onClose: () => void }) {
  const setWalkthroughDone = usePrefsStore((s) => s.setWalkthroughDone)
  const [i, setI] = useState(0)
  const [dontShow, setDontShow] = useState(true)
  const last = i === SLIDES.length - 1
  const slide = SLIDES[i]

  const finish = () => {
    if (dontShow) setWalkthroughDone(true)
    onClose()
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Feature tour"
    >
      <div className="w-full max-w-md rounded-2xl bg-white shadow-xl overflow-hidden relative">
        <button
          type="button"
          onClick={finish}
          aria-label="Close tour"
          className="absolute top-2.5 right-3 text-gray-300 hover:text-gray-500 text-xl leading-none"
        >
          ×
        </button>
        <div className="px-6 pt-7 pb-5 text-center min-h-56 flex flex-col items-center justify-center">
          <div className="text-5xl mb-3" aria-hidden="true">{slide.icon}</div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">{slide.title}</h2>
          <p className="text-gray-600 leading-relaxed">{slide.body}</p>
        </div>

        {/* progress dots */}
        <div className="flex justify-center gap-1.5 pb-4">
          {SLIDES.map((_, n) => (
            <button
              key={n}
              type="button"
              aria-label={`Go to step ${n + 1}`}
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
            Don’t show again
          </label>
          <div className="flex items-center gap-2">
            {i > 0 && (
              <button
                type="button"
                onClick={() => setI((n) => n - 1)}
                className="rounded-lg px-3 py-1.5 text-sm text-gray-500 hover:bg-gray-100"
              >
                Back
              </button>
            )}
            {last ? (
              <button
                type="button"
                onClick={finish}
                className="rounded-lg bg-lang px-4 py-1.5 text-sm font-semibold text-lang-on"
              >
                Get started
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setI((n) => n + 1)}
                className="rounded-lg bg-lang px-4 py-1.5 text-sm font-semibold text-lang-on"
              >
                Next
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
