import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import UsageMeter from '../components/UsageMeter'
import type { TutorAllowance } from '../api/tutor'

const base: TutorAllowance = {
  tier: 'free',
  unlimited: false,
  entitled: false,
  limit: 20,
  used: 6,
  remaining: 14,
  resets_at: '2026-08-01T00:00:00+00:00',
}

describe('UsageMeter', () => {
  it('shows the percentage of the monthly pool and the reset date — never counts', () => {
    render(<UsageMeter allowance={base} />)
    const meter = screen.getByTestId('usage-meter')
    expect(meter.textContent).toContain('Monthly usage')
    expect(meter.textContent).toContain('30% used')
    expect(meter.textContent).toContain('Resets')
    expect(meter.textContent).not.toContain('20') // the raw limit stays hidden
    expect(screen.getByRole('progressbar').getAttribute('aria-valuenow')).toBe('30')
  })

  it('caps the bar at 100% even when usage overshoots', () => {
    render(<UsageMeter allowance={{ ...base, used: 25, remaining: 0 }} />)
    expect(screen.getByTestId('usage-pct').textContent).toBe('100% used')
  })

  it('renders nothing for unlimited accounts — no meter is the default state', () => {
    render(
      <UsageMeter
        allowance={{ ...base, tier: 'unlimited', unlimited: true, limit: null }}
      />,
    )
    expect(screen.queryByTestId('usage-meter')).toBeNull()
  })

  it('renders nothing when there is no allowance at all', () => {
    render(<UsageMeter allowance={null} />)
    expect(screen.queryByTestId('usage-meter')).toBeNull()
  })
})
