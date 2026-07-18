import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import EngagementPanel from '../features/contribute/EngagementPanel'

vi.mock('../api/contribute', () => ({ getEngagement: vi.fn() }))
import { getEngagement } from '../api/contribute'
const mockGet = getEngagement as ReturnType<typeof vi.fn>

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
})
