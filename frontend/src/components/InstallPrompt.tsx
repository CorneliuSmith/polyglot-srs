import { useEffect, useState } from 'react'
import { Smartphone } from 'lucide-react'
import { Trans, useTranslation } from 'react-i18next'
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
  const { t } = useTranslation()
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
      <Smartphone aria-hidden className="h-6 w-6 shrink-0 text-lang" strokeWidth={1.75} />
      <div className="flex-1 text-gray-700">
        {installEvent ? (
          <Trans i18nKey="install.appBody" components={{ b: <b /> }} />
        ) : (
          <Trans
            i18nKey="install.iosBody"
            components={{ b: <b />, share: <span aria-hidden="true" /> }}
          />
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
          {t('install.install')}
        </button>
      )}
      <button
        type="button"
        onClick={() => setDismissed(true)}
        aria-label={t('install.dismiss')}
        className="text-gray-500 hover:text-gray-600 text-lg leading-none"
      >
        ×
      </button>
    </div>
  )
}
