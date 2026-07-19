import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import EngagementPanel from '../features/contribute/EngagementPanel'

vi.mock('../api/contribute', () => ({
  getEngagement: vi.fn(),
  getEngagementUsers: vi.fn(),
}))
import { getEngagement, getEngagementUsers } from '../api/contribute'
const mockGet = getEngagement as ReturnType<typeof vi.fn>
const mockGetUsers = getEngagementUsers as ReturnType<typeof vi.fn>

function renderPanel() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <EngagementPanel />
    </QueryClientProvider>,
  )
}

describe('EngagementPanel', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders active-user, feature, and language stats', async () => {
    mockGet.mockResolvedValue({
      days: 30, total_users: 12, new_users: 4,
      active_users: { d1: 3, d7: 7, d30: 9 },
      reviews: 186, review_hours: 9.4, tutor_messages: 35,
      readings: 3, cards_started: 325,
      feature_users: { review: 6, tutor: 4, reader: 2 },
      top_languages: [
        { code: 'es', name: 'Spanish', learners: 4, cards: 120 },
      ],
    })
    renderPanel()
    await waitFor(() => expect(screen.getByTestId('engagement')).toBeDefined())
    expect(screen.getByText(/Engagement · last 30 days/)).toBeDefined()
    expect(screen.getByText('9')).toBeDefined() // active · 30 days
    expect(screen.getByText('9.4 h studying')).toBeDefined()
    expect(screen.getByText('Spanish')).toBeDefined()
    expect(screen.getByText('4 learners')).toBeDefined()
  })

  it('renders nothing until data arrives', () => {
    mockGet.mockReturnValue(new Promise(() => {}))
    const { container } = renderPanel()
    expect(container.querySelector('[data-testid="engagement"]')).toBeNull()
  })

  it('tapping an active tile drills into the actual users in that window', async () => {
    mockGet.mockResolvedValue({
      days: 30, total_users: 12, new_users: 4,
      active_users: { d1: 1, d7: 2, d30: 2 },
      reviews: 186, review_hours: 9.4, tutor_messages: 35,
      readings: 3, cards_started: 325,
      feature_users: { review: 6, tutor: 4, reader: 2 },
      top_languages: [],
    })
    const now = new Date().toISOString()
    const tenDaysAgo = new Date(Date.now() - 10 * 86_400_000).toISOString()
    mockGetUsers.mockResolvedValue([
      { id: 'u1', email: 'fresh@x.co', joined: null, last_active: now,
        reviews: 12, review_minutes: 8, tutor_messages: 2, readings: 1,
        cards_started: 5, cards_total: 40, languages: ['es', 'ru'] },
      { id: 'u2', email: 'stale@x.co', joined: null, last_active: tenDaysAgo,
        reviews: 0, review_minutes: 0, tutor_messages: 0, readings: 0,
        cards_started: 0, cards_total: 9, languages: ['sw'] },
    ])
    renderPanel()
    await waitFor(() => expect(screen.getByTestId('engagement')).toBeDefined())
    // no users fetched until a tile is tapped
    expect(mockGetUsers).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: /active today/ }))
    // today's window shows the fresh user (once loaded), filters the stale one
    await waitFor(() => expect(screen.getByText('fresh@x.co')).toBeDefined())
    expect(screen.queryByText('stale@x.co')).toBeNull()
    expect(screen.getByText('es ru')).toBeDefined()
    // the 7-day tile widens the window to include both
    fireEvent.click(screen.getByRole('button', { name: /active · 30 days/ }))
    await waitFor(() => expect(screen.getByText('stale@x.co')).toBeDefined())
    // tapping the active tile again collapses the table
    fireEvent.click(screen.getByRole('button', { name: /active · 30 days/ }))
    expect(screen.queryByTestId('engagement-users')).toBeNull()
  })
})
