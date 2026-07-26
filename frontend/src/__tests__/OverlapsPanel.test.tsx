import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import OverlapsPanel from '../features/contribute/OverlapsPanel'

vi.mock('../api/contribute', () => ({
  getOverlaps: vi.fn(),
  resolveOverlap: vi.fn(),
}))

import { getOverlaps, resolveOverlap } from '../api/contribute'

const mockGet = getOverlaps as ReturnType<typeof vi.fn>
const mockResolve = resolveOverlap as ReturnType<typeof vi.fn>

const PAIR = {
  id: 'ov-1',
  verdict: 'partial' as const,
  reason: 'Both teach forming yes/no questions',
  status: 'open',
  created_at: '2026-07-26T00:00:00Z',
  point_a: { id: 'p1', title: 'Question words overview', level: 'A1' },
  point_b: { id: 'p2', title: 'Question formation', level: 'A2' },
}

function renderPanel(canResolve = true) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={qc}>
      <OverlapsPanel languageId="lang-1" canResolve={canResolve} />
    </QueryClientProvider>,
  )
}

describe('OverlapsPanel', () => {
  beforeEach(() => vi.clearAllMocks())

  it('hides itself when the queue is empty', async () => {
    mockGet.mockResolvedValue([])
    renderPanel()
    await waitFor(() => expect(mockGet).toHaveBeenCalled())
    expect(screen.queryByTestId('overlaps-panel')).toBeNull()
  })

  it('shows each pair with both titles, the verdict, and the reason', async () => {
    mockGet.mockResolvedValue([PAIR])
    renderPanel()
    const pair = await screen.findByTestId('overlap-pair')
    expect(pair.textContent).toContain('Question words overview')
    expect(pair.textContent).toContain('Question formation')
    expect(pair.textContent).toContain('Partial overlap')
    expect(pair.textContent).toContain('yes/no questions')
  })

  it('resolving records the reviewer verdict', async () => {
    mockGet.mockResolvedValue([PAIR])
    mockResolve.mockResolvedValue({ resolved: true })
    renderPanel()
    await screen.findByTestId('overlap-pair')
    fireEvent.click(screen.getByRole('button', { name: /keep both/i }))
    await waitFor(() =>
      expect(mockResolve).toHaveBeenCalledWith('ov-1', 'distinct'),
    )
    fireEvent.click(screen.getByRole('button', { name: /not an overlap/i }))
    await waitFor(() =>
      expect(mockResolve).toHaveBeenCalledWith('ov-1', 'dismissed'),
    )
  })

  it('trial reviewers see the queue but get no resolve buttons', async () => {
    mockGet.mockResolvedValue([PAIR])
    renderPanel(false)
    await screen.findByTestId('overlap-pair')
    expect(screen.queryByRole('button', { name: /keep both/i })).toBeNull()
  })
})
