import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { CARD_COLUMNS, PAGE_WIDE } from '../lib/layout'

const src = (rel: string) => readFileSync(join(__dirname, '..', rel), 'utf8')

/**
 * Two rules, and the second is the one that is easy to lose.
 *
 * Dashboards of independent cards use the shared width ramp — a wide
 * monitor showed Account as a 576-pixel ribbon down the middle of 2000
 * pixels of empty grey.
 *
 * Pages you READ do not. Line length is a legibility constraint: past
 * roughly 75 characters the eye loses its place on the way back to the
 * left. The tempting next commit is "make everything wide"; this test is
 * where that stops.
 */
describe('page width', () => {
  const DASHBOARDS = [
    'features/dashboard/DashboardPage.tsx',
    'features/dashboard/PracticePage.tsx',
    'features/dashboard/ProgressPage.tsx',
    'features/dashboard/MorePage.tsx',
    'features/settings/SettingsPage.tsx',
  ]

  it.each(DASHBOARDS)('%s uses the shared width ramp', (file) => {
    expect(src(file)).toContain('PAGE_WIDE')
  })

  it('the ramp widens in steps rather than jumping to full bleed', () => {
    // A phone is unaffected; the growth is all at lg and above.
    expect(PAGE_WIDE).toMatch(/^max-w-2xl /)
    expect(PAGE_WIDE).toContain('lg:max-w-5xl')
    expect(PAGE_WIDE).toContain('xl:max-w-6xl')
    expect(PAGE_WIDE).toContain('2xl:max-w-7xl')
    // No `max-w-full`/`w-screen`: text that runs the whole monitor is the
    // problem this replaced, not the goal.
    expect(PAGE_WIDE).not.toMatch(/max-w-full|w-screen|max-w-none/)
  })

  it('card columns pair up without stretching a short card', () => {
    expect(CARD_COLUMNS).toContain('lg:grid-cols-2')
    expect(CARD_COLUMNS).toContain('items-start')
  })

  const READING = [
    // The answer-a-card and read-a-text surfaces. Measured, not wide.
    'features/review/ReviewSessionPage.tsx',
    'features/review/LearnPage.tsx',
    'features/reader/ReaderPage.tsx',
  ]

  it.each(READING)('%s keeps its reading measure', (file) => {
    expect(src(file)).not.toContain('PAGE_WIDE')
  })
})
