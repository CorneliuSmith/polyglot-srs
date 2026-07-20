import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AnalyticsPanel from '../features/contribute/AnalyticsPanel'

vi.mock('../api/contribute', () => ({
  getAnalyticsTimeseries: vi.fn(),
  getAnalyticsCohorts: vi.fn(),
}))
import {
  getAnalyticsTimeseries,
  getAnalyticsCohorts,
} from '../api/contribute'
const mockSeries = getAnalyticsTimeseries as ReturnType<typeof vi.fn>
const mockCohorts = getAnalyticsCohorts as ReturnType<typeof vi.fn>

const SERIES = [
  { date: '2026-07-18', active_users: 3, reviews: 40, minutes: 25, new_users: 1 },
  { date: '2026-07-19', active_users: 5, reviews: 80, minutes: 60, new_users: 2 },
]
const COHORTS = [
  { cohort_week: '2026-07-06', size: 4, returned: [4, 2, 1, 0, 0, 0, 0, 0] },
]

function renderPanel() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <AnalyticsPanel />
    </QueryClientProvider>,
  )
}

describe('AnalyticsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockSeries.mockResolvedValue(SERIES)
    mockCohorts.mockResolvedValue(COHORTS)
  })

  it('renders trend charts and the signup count', async () => {
    renderPanel()
    await waitFor(() => expect(screen.getByTestId('analytics')).toBeDefined())
    expect(screen.getByText(/Trends · last 30 days/)).toBeDefined()
    expect(screen.getByText('3 new signups in this window.')).toBeDefined()
    expect(
      screen.getByRole('img', { name: /active users \/ day/i }),
    ).toBeDefined()
    expect(screen.getByRole('img', { name: /reviews \/ day/i })).toBeDefined()
    expect(
      screen.getByRole('img', { name: /study minutes \/ day/i }),
    ).toBeDefined()
  })

  it('renders the retention cohort grid with percentages', async () => {
    renderPanel()
    await waitFor(() => expect(screen.getByText('2026-07-06')).toBeDefined())
    expect(screen.getByText('100%')).toBeDefined() // w0: 4 of 4
    expect(screen.getByText('50%')).toBeDefined() // w1: 2 of 4
    expect(screen.getByText('25%')).toBeDefined() // w2: 1 of 4
  })

  it('the range picker refetches with the chosen window', async () => {
    renderPanel()
    await waitFor(() => expect(screen.getByTestId('analytics')).toBeDefined())
    fireEvent.click(screen.getByRole('button', { name: '90d' }))
    await waitFor(() => expect(mockSeries).toHaveBeenCalledWith(90))
    expect(await screen.findByText(/Trends · last 90 days/)).toBeDefined()
  })

  it('renders nothing until the series arrives', () => {
    mockSeries.mockReturnValue(new Promise(() => {}))
    const { container } = renderPanel()
    expect(container.querySelector('[data-testid="analytics"]')).toBeNull()
  })
})
