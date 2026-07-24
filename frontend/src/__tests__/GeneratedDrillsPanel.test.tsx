import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import GeneratedDrillsPanel from '../features/contribute/GeneratedDrillsPanel'

vi.mock('../api/contribute', async (orig) => ({
  ...(await orig<typeof import('../api/contribute')>()),
  getPendingDrills: vi.fn(),
  reviewDrill: vi.fn(),
  recommend: vi.fn(() => Promise.resolve()),
}))

import { getPendingDrills, reviewDrill, recommend } from '../api/contribute'
const mockPending = getPendingDrills as ReturnType<typeof vi.fn>
const mockReview = reviewDrill as ReturnType<typeof vi.fn>
const mockRecommend = recommend as ReturnType<typeof vi.fn>

function renderPanel() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={qc}>
      <GeneratedDrillsPanel languageId="lang-es" />
    </QueryClientProvider>,
  )
}

const DRILL = {
  id: 'd1', sentence: 'Ella {{answer}} en casa.', answer: 'trabaja',
  translation: 'She works at home.', hint: 'trabajar, ella', cell: 'él/ella',
  origin_detail: 'claude-x', point_title: 'Present -ar', point_id: 'p1',
}

describe('GeneratedDrillsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockReview.mockResolvedValue(undefined)
  })

  it('renders nothing when there are no pending drills', async () => {
    mockPending.mockResolvedValue({ pending: [], can_publish: true })
    renderPanel()
    // Give the query a tick; the panel returns null.
    await waitFor(() => expect(mockPending).toHaveBeenCalled())
    expect(screen.queryByTestId('generated-drills')).toBeNull()
  })

  it('lists pending drills and approves one', async () => {
    mockPending.mockResolvedValue({ pending: [DRILL], can_publish: true })
    renderPanel()
    expect(await screen.findByTestId('generated-drills')).toBeDefined()
    expect(screen.getByText(/Present -ar/)).toBeDefined()
    // the blank is shown filled with the answer for the reviewer
    expect(screen.getByText(/【trabaja】/)).toBeDefined()
    fireEvent.click(screen.getByRole('button', { name: /approve/i }))
    await waitFor(() => expect(mockReview).toHaveBeenCalledWith('d1', true))
  })

  it('rejects a drill', async () => {
    mockPending.mockResolvedValue({ pending: [DRILL], can_publish: true })
    renderPanel()
    await screen.findByTestId('generated-drills')
    fireEvent.click(screen.getByRole('button', { name: /reject/i }))
    await waitFor(() => expect(mockReview).toHaveBeenCalledWith('d1', false))
  })

  it('a trial reviewer recommends instead of publishing', async () => {
    mockPending.mockResolvedValue({ pending: [DRILL], can_publish: false })
    renderPanel()
    await screen.findByTestId('generated-drills')
    // No publish buttons; recommend buttons instead.
    expect(screen.queryByRole('button', { name: /^approve$/i })).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: /recommend ✓/i }))
    await waitFor(() =>
      expect(mockRecommend).toHaveBeenCalledWith('drill', 'd1', 'approve'),
    )
    expect(mockReview).not.toHaveBeenCalled()
  })

  it('shows the recommendation tally to a full reviewer', async () => {
    mockPending.mockResolvedValue({
      pending: [{ ...DRILL, recommendations: { approve: 2, reject: 1, notes: [] } }],
      can_publish: true,
    })
    renderPanel()
    await screen.findByTestId('generated-drills')
    expect(screen.getByText(/2 recommend approve/i)).toBeDefined()
    expect(screen.getByText(/1 recommend reject/i)).toBeDefined()
  })
})
