import { useEffect } from 'react'
import { Frown } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useRouteError } from 'react-router-dom'
import { reportError } from '../lib/sentry'

/** Route-level crash screen: apologize, offer reload, log the real error
 * to the console for debugging. Far better than the router's default
 * stack-trace page a beta tester once screenshotted.
 *
 * Mounted as a route errorElement inside the normal React tree, and i18next
 * is initialised synchronously by main.tsx's `./i18n` import before the
 * first render — so useTranslation is safe here. */
export default function ErrorScreen() {
  const { t } = useTranslation()
  const error = useRouteError()
  console.error('Route error:', error)
  // Telemetry (WP19d): the crash the tester used to screenshot now files
  // itself. No-op until the Sentry DSN is configured.
  useEffect(() => {
    reportError(error)
  }, [error])
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="text-center space-y-4 max-w-sm">
        <Frown aria-hidden className="mx-auto h-10 w-10 text-gray-300" strokeWidth={1.5} />
        <h1 className="text-lg font-semibold text-gray-800">
          {t('errorScreen.title')}
        </h1>
        <p className="text-sm text-gray-500">{t('errorScreen.body')}</p>
        <button
          type="button"
          onClick={() => window.location.assign('/')}
          className="rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold px-6 py-2.5 text-sm"
        >
          {t('errorScreen.reload')}
        </button>
      </div>
    </div>
  )
}
