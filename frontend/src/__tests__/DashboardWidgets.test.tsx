import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ForecastStrip from '../features/dashboard/ForecastStrip'
import ActivityChart from '../features/dashboard/ActivityChart'
import StageTiles from '../features/dashboard/StageTiles'
import ProfileCard from '../features/dashboard/ProfileCard'
import type { StageName } from '../api/types'

const stages: Record<'vocab' | 'grammar', Record<StageName, number>> = {
  grammar: {
    beginner: 12, adept: 1, seasoned: 0, expert: 0, master: 0,
    self_study: 0, ghost: 2,
  },
  vocab: {
    beginner: 26, adept: 3, seasoned: 4, expert: 0, master: 1,
    self_study: 5, ghost: 0,
  },
}

describe('ForecastStrip', () => {
  it('renders one bar per day with counts', () => {
    render(
      <ForecastStrip
        forecast={[
          { date: '2026-07-06', count: 0 },
          { date: '2026-07-07', count: 5 },
        ]}
      />,
    )
    expect(screen.getByText(/review forecast/i)).toBeDefined()
    expect(screen.getByText('Today')).toBeDefined()
    expect(screen.getByText('5')).toBeDefined()
  })
})

describe('ActivityChart', () => {
  it('renders the legend', () => {
    render(
      <ActivityChart
        activity={[{ date: '2026-07-06', vocab: 4, grammar: 3 }]}
      />,
    )
    expect(screen.getByText('Vocab')).toBeDefined()
    expect(screen.getByText('Grammar')).toBeDefined()
  })
})

describe('StageTiles', () => {
  it('shows grammar counts by default and toggles to vocab', () => {
    render(<StageTiles stages={stages} />)
    // grammar beginner
    expect(screen.getByText('12')).toBeDefined()
    // Ghosts tile present
    expect(screen.getByText('Ghosts')).toBeDefined()
    fireEvent.click(screen.getByRole('button', { name: /vocab/i }))
    expect(screen.getByText('26')).toBeDefined()
    expect(screen.getByText('Self-Study')).toBeDefined()
  })
})

describe('ProfileCard', () => {
  const profile = {
    days_studied: 12,
    items_studied: 101,
    last_session_accuracy: 0.29,
    week: [
      { date: '2026-07-05', studied: false },
      { date: '2026-07-06', studied: true },
    ],
  }

  it('renders streak, totals, and accuracy', () => {
    render(<ProfileCard profile={profile} streakDays={2} />)
    expect(screen.getByText(/current streak — 2 days/i)).toBeDefined()
    expect(screen.getByText('12')).toBeDefined()
    expect(screen.getByText('101')).toBeDefined()
    expect(screen.getByText('29%')).toBeDefined()
  })

  it('shows a dash when there is no session yet', () => {
    render(
      <ProfileCard
        profile={{ ...profile, last_session_accuracy: null }}
        streakDays={0}
      />,
    )
    expect(screen.getByText('—')).toBeDefined()
  })
})
