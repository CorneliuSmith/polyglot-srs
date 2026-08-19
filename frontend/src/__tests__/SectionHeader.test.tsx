import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import SectionHeader from '../components/SectionHeader'

// The switcher talks to the profile API on interaction; this test only
// needs it to EXIST, so the network side stays quiet.
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
      <MemoryRouter>
        <SectionHeader title="Practice" />
      </MemoryRouter>,
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
      <MemoryRouter>
        <SectionHeader title="Practice" />
      </MemoryRouter>,
    )
    expect(screen.queryByRole('dialog', { name: /feature tour/i })).toBeNull()
  })
})
