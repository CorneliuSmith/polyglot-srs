import * as Sentry from '@sentry/react'

// Error telemetry (WP19d) — a complete no-op until VITE_SENTRY_DSN is set
// at build time. Errors only (no tracing, no replays) and no PII: beta
// bugs should arrive as stack traces instead of screenshots.
const dsn = import.meta.env.VITE_SENTRY_DSN as string | undefined

export function initSentry(): void {
  if (!dsn) return
  Sentry.init({
    dsn,
    environment: import.meta.env.MODE,
    sendDefaultPii: false,
  })
}

/** Report a caught error (e.g. a route crash) — silently dropped when
 * telemetry is off. */
export function reportError(error: unknown): void {
  if (!dsn) return
  Sentry.captureException(error)
}
