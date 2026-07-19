import { useEffect, useState } from 'react'
import { usePrefsStore } from '../stores/prefsStore'

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>
}

function isStandalone(): boolean {
  try {
    return (
      window.matchMedia?.('(display-mode: standalone)')?.matches ||
      (navigator as unknown as { standalone?: boolean }).standalone === true
    )
  } catch {
    return false
  }
}

function isIos(): boolean {
  return /iphone|ipad|ipod/i.test(navigator.userAgent)
}

/** "Install the app" banner (the mobile option, phase 1).
 *
 * The app is already an installable PWA; this makes that discoverable:
 *  - Android/desktop Chrome fire `beforeinstallprompt` — we catch it and
 *    show a one-tap Install button.
 *  - iOS Safari has no prompt API, so we show the Add-to-Home-Screen steps.
 * Hidden once installed (standalone) or dismissed (persisted). */
export default function InstallPrompt() {
  const dismissed = usePrefsStore((s) => s.installPromptDismissed)
  const setDismissed = usePrefsStore((s) => s.setInstallPromptDismissed)
  const [installEvent, setInstallEvent] = useState<BeforeInstallPromptEvent | null>(null)

  useEffect(() => {
    const onPrompt = (e: Event) => {
      e.preventDefault()
      setInstallEvent(e as BeforeInstallPromptEvent)
    }
    window.addEventListener('beforeinstallprompt', onPrompt)
    return () => window.removeEventListener('beforeinstallprompt', onPrompt)
  }, [])

  if (dismissed || isStandalone()) return null
  const ios = isIos()
  if (!installEvent && !ios) return null

  return (
    <div
      className="flex items-center gap-3 rounded-2xl border border-lang/30 bg-lang-soft px-4 py-3 text-sm"
      data-testid="install-prompt"
    >
      <span className="text-xl" aria-hidden="true">📱</span>
      <div className="flex-1 text-gray-700">
        {installEvent ? (
          <>
            <b>Use PolyglotSRS as an app</b> — reviews one tap from your home
            screen.
          </>
        ) : (
          <>
            <b>Add to your home screen:</b> tap Share
            <span aria-hidden="true"> ⎋ </span>then “Add to Home Screen”.
          </>
        )}
      </div>
      {installEvent && (
        <button
          type="button"
          onClick={() => {
            void installEvent.prompt()
            setDismissed(true)
          }}
          className="rounded-lg bg-lang px-3 py-1.5 font-semibold text-lang-on"
        >
          Install
        </button>
      )}
      <button
        type="button"
        onClick={() => setDismissed(true)}
        aria-label="Dismiss install prompt"
        className="text-gray-400 hover:text-gray-600 text-lg leading-none"
      >
        ×
      </button>
    </div>
  )
}
