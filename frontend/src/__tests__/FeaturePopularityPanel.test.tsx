import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import FeaturePopularityPanel from '../features/contribute/FeaturePopularityPanel'

vi.mock('../api/contribute', () => ({ getFeaturePopularity: vi.fn() }))
import { getFeaturePopularity } from '../api/contribute'
const mockGet = getFeaturePopularity as ReturnType<typeof vi.fn>

function renderPanel() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <FeaturePopularityPanel />
    </QueryClientProvider>,
  )
}

const FEATURES = [
  { key: 'review', label: 'Reviews', unit: 'reviews', users: 9, events: 480 },
  { key: 'speak', label: 'Speak', unit: 'conversations', users: 3, events: 17 },
  { key: 'decks', label: 'Decks', unit: 'decks created', users: 0, events: 0 },
]

describe('FeaturePopularityPanel', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows one bar per feature: users drive the bar, events ride as text', async () => {
    mockGet.mockResolvedValue(FEATURES)
    renderPanel()
    await waitFor(() =>
      expect(screen.getByTestId('feature-popularity')).toBeDefined(),
    )
    // Counts carry each feature's own unit, never a bare "events".
    expect(screen.getByText(/9 users · 480 reviews/)).toBeDefined()
    expect(screen.getByText(/3 users · 17 conversations/)).toBeDefined()
    // Bar widths follow distinct users, on one shared scale.
    const bar = (key: string) =>
      (screen.getByTestId(`feature-${key}`).querySelector(
        '.bg-lang',
      ) as HTMLElement).style.width
    expect(bar('review')).toBe('100%')
    expect(parseFloat(bar('speak'))).toBeCloseTo((3 / 9) * 100, 1)
    // An unused feature is still listed — "nobody touched Decks" is a
    // finding, not missing data — with an empty bar.
    expect(screen.getByText(/0 users · 0 decks created/)).toBeDefined()
    expect(bar('decks')).toBe('0%')
  })

  it('the range buttons refetch for that window', async () => {
    mockGet.mockResolvedValue(FEATURES)
    renderPanel()
    await waitFor(() =>
      expect(screen.getByTestId('feature-popularity')).toBeDefined(),
    )
    expect(mockGet).toHaveBeenLastCalledWith(30)
    fireEvent.click(screen.getByRole('button', { name: '7d' }))
    await waitFor(() => expect(mockGet).toHaveBeenLastCalledWith(7))
    // The panel hides itself while the new window loads, then comes back.
    await waitFor(() => expect(screen.getByText(/last 7 days/)).toBeDefined())
  })

  it('renders nothing while loading or with no data', () => {
    mockGet.mockReturnValue(new Promise(() => {}))
    const { container } = renderPanel()
    expect(
      container.querySelector('[data-testid="feature-popularity"]'),
    ).toBeNull()
  })
})
