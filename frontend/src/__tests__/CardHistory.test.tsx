import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import CardHistory from '../features/contribute/CardHistory'

vi.mock('../api/contribute', () => ({
  getContentHistory: vi.fn(),
  revertContentChange: vi.fn(() => Promise.resolve()),
}))

import { getContentHistory, revertContentChange } from '../api/contribute'
const mockGet = getContentHistory as ReturnType<typeof vi.fn>
const mockRevert = revertContentChange as ReturnType<typeof vi.fn>

function renderHistory() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  render(
    <QueryClientProvider client={qc}>
      <CardHistory entityType="example_sentence" entityId="e1" />
    </QueryClientProvider>,
  )
}

const EDIT = {
  id: 'log1', entity_type: 'example_sentence', entity_id: 'e1', action: 'edited',
  field: null, before: { sentence: 'Old text.' }, after: { sentence: 'New text.' },
  note: null, actor_id: 'u1', actor_email: 'rev@x', created_at: '2026-07-24T10:00:00Z',
  revertible: true,
}

describe('CardHistory', () => {
  beforeEach(() => vi.clearAllMocks())

  it('is collapsed until History is clicked, then shows the timeline', async () => {
    mockGet.mockResolvedValue({ changes: [EDIT], can_revert: true })
    renderHistory()
    // Collapsed: the query is not enabled yet.
    expect(screen.queryByTestId('card-history')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: /^history$/i }))
    expect(await screen.findByTestId('card-history')).toBeDefined()
    // The timeline loads asynchronously.
    expect(await screen.findByText(/edited/)).toBeDefined()
    expect(screen.getByText(/rev@x/)).toBeDefined()
    expect(screen.getByText('Old text.')).toBeDefined()
    expect(screen.getByText('New text.')).toBeDefined()
  })

  it('rolls back a revertible change when the reviewer confirms', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    mockGet.mockResolvedValue({ changes: [EDIT], can_revert: true })
    renderHistory()
    fireEvent.click(screen.getByRole('button', { name: /^history$/i }))
    fireEvent.click(await screen.findByRole('button', { name: /roll back/i }))
    await waitFor(() => expect(mockRevert).toHaveBeenCalledWith('log1'))
  })

  it('hides roll-back when the viewer cannot revert', async () => {
    mockGet.mockResolvedValue({ changes: [EDIT], can_revert: false })
    renderHistory()
    fireEvent.click(screen.getByRole('button', { name: /^history$/i }))
    await screen.findByTestId('card-history')
    expect(screen.queryByRole('button', { name: /roll back/i })).toBeNull()
  })
})
