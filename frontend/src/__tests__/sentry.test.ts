import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@sentry/react', () => ({
  init: vi.fn(),
  captureException: vi.fn(),
}))

import * as Sentry from '@sentry/react'

const mockInit = Sentry.init as ReturnType<typeof vi.fn>
const mockCapture = Sentry.captureException as ReturnType<typeof vi.fn>

describe('sentry wiring (WP19d)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.unstubAllEnvs()
    vi.resetModules()
  })

  it('is a complete no-op without a DSN', async () => {
    const { initSentry, reportError } = await import('../lib/sentry')
    initSentry()
    reportError(new Error('boom'))
    expect(mockInit).not.toHaveBeenCalled()
    expect(mockCapture).not.toHaveBeenCalled()
  })

  it('initializes without PII and reports errors when a DSN is set', async () => {
    vi.stubEnv('VITE_SENTRY_DSN', 'https://key@o0.ingest.sentry.io/0')
    const { initSentry, reportError } = await import('../lib/sentry')
    initSentry()
    expect(mockInit).toHaveBeenCalledWith(
      expect.objectContaining({
        dsn: 'https://key@o0.ingest.sentry.io/0',
        sendDefaultPii: false,
      }),
    )
    const err = new Error('boom')
    reportError(err)
    expect(mockCapture).toHaveBeenCalledWith(err)
  })
})
