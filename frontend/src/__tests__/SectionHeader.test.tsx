import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import SectionHeader from '../components/SectionHeader'

// The switcher talks to the profile API on interaction; this test only
// needs it to EXIST, so the network side stays quiet.
// The header's staff inbox circle asks whether this account has review work
// waiting. A learner gets an empty, well-formed answer — no badge, no circle.
vi.mock('../api/contribute', async (orig) => ({
  ...(await orig<typeof import('../api/contribute')>()),
  getReviewNotifications: vi.fn(() =>
    Promise.resolve({
      languages: [], review_total: 0, feedback: [], feedback_total: 0,
      is_admin: false, is_staff: false,
    }),
  ),
}))

vi.mock('../api/profile', async (orig) => ({
  ...(await orig()),
  getProfile: vi.fn(() => Promise.resolve({ ui_language: 'en' })),
  updateProfile: vi.fn(() => Promise.resolve()),
}))

/**
 * Owner: "No matter what tab — study, practice, progress, more — I want to
 * see the four circle icons." Study renders its own header (with the tour
 * auto-open); the other three sections all render THIS component, so the
 * cluster being here is what puts it on every tab.
 */
describe('SectionHeader', () => {
  it('carries all four utility circles, not just the globe', () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <SectionHeader title="Practice" />
      </MemoryRouter>
      </QueryClientProvider>,
    )
    expect(screen.getByTestId('header-account')).toBeInTheDocument()
    expect(screen.getByTestId('ui-language-switcher')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /what's new/i }),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /tour/i })).toBeInTheDocument()
  })

  it('does not auto-open the tour outside Study', () => {
    // The tour offers itself once per edition on the LANDING page. A learner
    // opening Practice mid-task must not be interrupted by it there.
    render(
      <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <SectionHeader title="Practice" />
      </MemoryRouter>
      </QueryClientProvider>,
    )
    expect(screen.queryByRole('dialog', { name: /feature tour/i })).toBeNull()
  })
})
