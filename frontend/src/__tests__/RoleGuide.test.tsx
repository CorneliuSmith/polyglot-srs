import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import RoleGuide from '../features/contribute/RoleGuide'

describe('RoleGuide', () => {
  beforeEach(() => window.localStorage.clear())

  it('is open the first time a volunteer lands on the tab', () => {
    render(<RoleGuide role="contribute" />)
    expect(screen.getByText(/How the Workshop works/)).toBeDefined()
    // The lede is visible, not hidden behind a click.
    expect(screen.getByText(/until a reviewer approves it/)).toBeDefined()
  })

  it('remembers being collapsed, per role', () => {
    const { unmount } = render(<RoleGuide role="contribute" />)
    fireEvent.click(screen.getByRole('button', { expanded: true }))
    unmount()

    render(<RoleGuide role="contribute" />)
    expect(screen.getByRole('button', { expanded: false })).toBeDefined()

    // Reviewing is a different job — dismissing one guide must not hide the
    // other.
    unmount()
    render(<RoleGuide role="review" />)
    expect(screen.getByRole('button', { expanded: true })).toBeDefined()
  })

  it('tells a reviewer that approving publishes', () => {
    render(<RoleGuide role="review" />)
    expect(screen.getByText(/sets it live for learners/)).toBeDefined()
  })

  it('tells a trial reviewer that it does not', () => {
    render(<RoleGuide role="trial_review" />)
    expect(screen.getByText(/do not publish anything/)).toBeDefined()
  })

  it('warns that account deletion is permanent', () => {
    render(<RoleGuide role="admin" />)
    expect(screen.getByText(/permanent and cascades/)).toBeDefined()
  })
})
