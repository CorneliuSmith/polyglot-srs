import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import DueCount from '../features/dashboard/DueCount'
import StreakBadge from '../features/dashboard/StreakBadge'
import CEFRProgress from '../features/dashboard/CEFRProgress'

describe('DueCount', () => {
  it('renders the due count number', () => {
    render(<DueCount count={42} />)
    expect(screen.getByText('42')).toBeDefined()
  })

  it('renders the "Cards Due" label', () => {
    render(<DueCount count={0} />)
    expect(screen.getByText(/cards due/i)).toBeDefined()
  })

  it('renders zero count', () => {
    render(<DueCount count={0} />)
    expect(screen.getByText('0')).toBeDefined()
  })
})

describe('StreakBadge', () => {
  it('renders streak days when greater than 0', () => {
    render(<StreakBadge days={7} />)
    expect(screen.getByText('7')).toBeDefined()
    expect(screen.getByText(/day streak/i)).toBeDefined()
  })

  it('renders start message when days is 0', () => {
    render(<StreakBadge days={0} />)
    expect(screen.getByText(/start your streak/i)).toBeDefined()
  })

  it('renders a streak of 1 day', () => {
    render(<StreakBadge days={1} />)
    expect(screen.getByText('1')).toBeDefined()
  })
})

describe('CEFRProgress', () => {
  // Mirrors the backend contract: cefr_progress maps each level to
  // {learned, total} counts (see backend/repositories/dashboard.py).
  const progress = {
    A1: { learned: 100, total: 100 },
    A2: { learned: 75, total: 100 },
    B1: { learned: 50, total: 100 },
    B2: { learned: 25, total: 100 },
    C1: { learned: 10, total: 100 },
    C2: { learned: 0, total: 100 },
  }

  it('renders all 6 CEFR levels', () => {
    render(<CEFRProgress progress={progress} />)
    expect(screen.getByText('A1')).toBeDefined()
    expect(screen.getByText('A2')).toBeDefined()
    expect(screen.getByText('B1')).toBeDefined()
    expect(screen.getByText('B2')).toBeDefined()
    expect(screen.getByText('C1')).toBeDefined()
    expect(screen.getByText('C2')).toBeDefined()
  })

  it('renders percentage text for each level', () => {
    render(<CEFRProgress progress={progress} />)
    expect(screen.getByText('100%')).toBeDefined()
    expect(screen.getByText('75%')).toBeDefined()
    expect(screen.getByText('50%')).toBeDefined()
    expect(screen.getByText('25%')).toBeDefined()
    expect(screen.getByText('10%')).toBeDefined()
    // There will be two 0% — one for C2 and any missing keys
    const zeros = screen.getAllByText('0%')
    expect(zeros.length).toBeGreaterThanOrEqual(1)
  })

  it('renders all levels even when some have no progress', () => {
    render(<CEFRProgress progress={{}} />)
    // All 6 levels should appear even with empty progress
    expect(screen.getByText('A1')).toBeDefined()
    expect(screen.getByText('C2')).toBeDefined()
  })

  it('renders progress bars via role attribute', () => {
    render(<CEFRProgress progress={progress} />)
    const bars = screen.getAllByRole('progressbar')
    expect(bars).toHaveLength(6)
  })
})
