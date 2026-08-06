/**
 * The admin readout's job is to make each way this feature can silently do
 * nothing look DIFFERENT. Two of them didn't:
 *
 *  - A sweep that isn't running and a queue that's genuinely empty both
 *    rendered as a panel with no complaints. The backend has reported the
 *    loop's heartbeat for a while; the panel simply dropped it.
 *  - "Migrations applied" only ever probed three tables, so the retry
 *    ledger being unapplied showed as green.
 *
 * Both cost real debugging time, which is what these tests are protecting.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import TranslationStatusPanel from '../features/contribute/TranslationStatusPanel'

vi.mock('../api/contribute', () => ({ getTranslationStatus: vi.fn() }))
import { getTranslationStatus } from '../api/contribute'
const mockStatus = getTranslationStatus as ReturnType<typeof vi.fn>

const base = {
  provider_ready: true,
  budget_per_cycle: 50,
  sweep_seconds: 900,
  loop_enabled: true,
  loop: {
    started: true,
    last_cycle_at: new Date(Date.now() - 4 * 60_000).toISOString(),
    cycles: 12,
    last_error: null,
    last_stats: null,
  },
  migrations: {
    translation_demand: true,
    translation_attempts: true,
    grammar_point_translations: true,
    gym_label_translations: true,
  },
  switched_off: [],
  pairs: [],
}

async function show(overrides: Record<string, unknown> = {}) {
  mockStatus.mockResolvedValue({ ...base, ...overrides })
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={qc}>
      <TranslationStatusPanel />
    </QueryClientProvider>,
  )
  return screen.findByTestId('translation-status')
}

describe('TranslationStatusPanel', () => {
  it('says the sweep is alive, and how recently', async () => {
    await show()
    expect(await screen.findByText(/Sweep running/)).toBeInTheDocument()
    expect(screen.getByText(/4 min ago/)).toBeInTheDocument()
    expect(screen.getByText(/12 cycles/)).toBeInTheDocument()
  })

  it('separates "switched off" from "never started"', async () => {
    await show({ loop_enabled: false })
    expect(await screen.findByText(/Sweep switched off/)).toBeInTheDocument()
  })

  it('flags a loop that is enabled but not running in this process', async () => {
    await show({ loop: { ...base.loop, started: false } })
    expect(await screen.findByText(/never started/)).toBeInTheDocument()
  })

  it('surfaces the last sweep error rather than looking healthy', async () => {
    await show({ loop: { ...base.loop, last_error: 'RateLimitError: 429' } })
    expect(await screen.findByText(/RateLimitError: 429/)).toBeInTheDocument()
  })

  it('does not claim to know the loop when the server is older than the field', async () => {
    await show({ loop: undefined, loop_enabled: true })
    expect(await screen.findByText(/status unknown/)).toBeInTheDocument()
  })

  it('names an unapplied translation_attempts migration', async () => {
    await show({ migrations: { ...base.migrations, translation_attempts: false } })
    expect(await screen.findByText(/translation_attempts/)).toBeInTheDocument()
    expect(screen.getByText(/supabase db push/)).toBeInTheDocument()
  })

  it('turns a backlog into a duration, because the number alone reads as a fault', async () => {
    // 20,506 items at 50 per 15 min ≈ 102.5 hours ≈ 4 days.
    await show({
      pairs: [
        {
          language: 'Catalan',
          code: 'ca',
          locale: 'fr',
          learners: 1,
          pending: { words: 14830, drills: 75, explanations: 22, examples: 5557, grammar_meta: 22 },
          filled: { words: 165, drills: 256, explanations: 20 },
        },
      ],
    })
    expect(await screen.findByText(/≈4d at this rate/)).toBeInTheDocument()
  })
})
