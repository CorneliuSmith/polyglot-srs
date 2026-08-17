import { useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate } from 'react-router-dom'
import { BookOpen, X } from 'lucide-react'
import { usePendingReadingStore } from '../stores/pendingReadingStore'

/** Routes where a floating card would land on top of a learner mid-answer.
 * The reading waits — it is already saved, and nothing about it expires. */
const SESSION_ROUTES = ['/review', '/cram', '/learn', '/gym', '/speak']

/**
 * "Your text is ready" — the other half of letting someone leave the
 * Reader while their text is written.
 *
 * Mounted app-wide, because the whole point is that the learner went
 * somewhere else. Two channels: this in-app banner always, plus a browser
 * notification when the tab is in the background and permission was
 * granted (asked for at the moment they chose to wander off — see
 * ReadingWait.askToNotify).
 */
export default function ReadingReadyBanner() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const ready = usePendingReadingStore((s) => s.ready)
  const clear = usePendingReadingStore((s) => s.clear)
  const notifiedFor = useRef<string | null>(null)

  // The OS-level nudge, once per finished text, only while they're looking
  // at something else. Firing it with the tab focused would duplicate the
  // banner they can already see.
  useEffect(() => {
    if (!ready || notifiedFor.current === ready.id) return
    notifiedFor.current = ready.id
    try {
      if (typeof Notification === 'undefined') return
      if (Notification.permission !== 'granted') return
      if (typeof document !== 'undefined' && !document.hidden) return
      new Notification(t('reader.ready.title'), {
        body: t('reader.ready.body', { topic: ready.topic }),
        tag: `reading-${ready.id}`,
      })
    } catch {
      // Notification constructors throw in some webviews — the banner is
      // the channel that always works.
    }
  }, [ready, t])

  if (!ready) return null
  // On the Reader the page itself opens the text; a banner announcing what
  // is already on screen is noise. Inside a running session it would land
  // on top of someone mid-answer.
  if (pathname === '/read') return null
  if (SESSION_ROUTES.some((r) => pathname.startsWith(r))) return null

  return (
    <div
      data-testid="reading-ready-banner"
      className="fixed inset-x-0 bottom-20 z-50 flex justify-center px-4 pointer-events-none"
    >
      <div className="pointer-events-auto flex items-center gap-3 rounded-xl border border-lang/30 bg-white shadow-lg px-4 py-3 max-w-sm w-full">
        <BookOpen className="w-5 h-5 text-lang shrink-0" aria-hidden="true" />
        <button
          type="button"
          onClick={() => navigate('/read')}
          className="flex-1 text-start"
        >
          <span className="block text-sm font-semibold text-gray-800">
            {t('reader.ready.title')}
          </span>
          <span className="block text-xs text-gray-500">
            {t('reader.ready.body', { topic: ready.topic })}
          </span>
        </button>
        <button
          type="button"
          onClick={clear}
          aria-label={t('reader.ready.dismiss')}
          className="shrink-0 rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
        >
          <X className="w-4 h-4" aria-hidden="true" />
        </button>
      </div>
    </div>
  )
}
