import { useEffect } from 'react'
import { useRouteError } from 'react-router-dom'
import { reportError } from '../lib/sentry'

/** Route-level crash screen: apologize, offer reload, log the real error
 * to the console for debugging. Far better than the router's default
 * stack-trace page a beta tester once screenshotted. */
export default function ErrorScreen() {
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
        <p className="text-3xl">😵</p>
        <h1 className="text-lg font-semibold text-gray-800">
          Something went wrong
        </h1>
        <p className="text-sm text-gray-500">
          Sorry — that page hit an error. Reloading usually fixes it, and
          your progress is saved on the server.
        </p>
        <button
          type="button"
          onClick={() => window.location.assign('/')}
          className="rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold px-6 py-2.5 text-sm"
        >
          Reload the app
        </button>
      </div>
    </div>
  )
}
