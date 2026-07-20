import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { usePrefsStore } from '../../stores/prefsStore'
import { WHATS_NEW } from './whatsNew'

/** The changelog modal: every entry, newest first, with a try-it link where
 * one makes sense. Opening it marks everything seen (the badge clears). */
export default function WhatsNewPanel({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate()
  const markWhatsNewSeen = usePrefsStore((s) => s.markWhatsNewSeen)
  // Chips show what was unseen when the panel OPENED — the mount effect
  // below marks everything seen, and the chips must not vanish mid-read.
  const [seenAtOpen] = useState(() => usePrefsStore.getState().whatsNewSeen)

  useEffect(() => {
    markWhatsNewSeen(WHATS_NEW.map((e) => e.id))
    // mark once per open — the ids list is static
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="What's new"
    >
      <div className="w-full max-w-md max-h-[85vh] overflow-y-auto rounded-2xl bg-white shadow-xl relative">
        <button
          type="button"
          onClick={onClose}
          aria-label="Close what's new"
          className="absolute top-2.5 right-3 text-gray-300 hover:text-gray-500 text-xl leading-none"
        >
          ×
        </button>
        <div className="px-6 pt-6 pb-5">
          <h2 className="text-xl font-bold text-gray-900 mb-4">What’s new</h2>
          <ul className="space-y-5">
            {WHATS_NEW.map((entry) => (
              <li key={entry.id} data-testid="whats-new-entry">
                <div className="flex items-baseline gap-2">
                  <h3 className="font-semibold text-gray-800">{entry.title}</h3>
                  {!seenAtOpen.includes(entry.id) && (
                    <span className="text-[10px] font-bold uppercase tracking-wide text-lang bg-lang-soft rounded-full px-1.5 py-0.5">
                      new
                    </span>
                  )}
                  <span className="ml-auto text-xs text-gray-400 whitespace-nowrap">
                    {entry.date}
                  </span>
                </div>
                <p className="mt-1 text-sm text-gray-600 leading-relaxed">
                  {entry.body}
                </p>
                {entry.link && (
                  <button
                    type="button"
                    onClick={() => {
                      onClose()
                      navigate(entry.link!)
                    }}
                    className="mt-1.5 text-sm font-medium text-lang hover:underline"
                  >
                    {entry.linkLabel ?? 'Try it'} →
                  </button>
                )}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
