/**
 * The admin's trial queue: approving mints the account and shows the
 * temporary password ONCE — critical when email is log-only, because an
 * approval whose password nobody can read helps no one.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import TrialRequestsPanel from '../features/contribute/TrialRequestsPanel'

vi.mock('../api/contribute', () => ({
  listTrialRequests: vi.fn(),
  approveTrialRequest: vi.fn(),
  rejectTrialRequest: vi.fn(),
}))

import {
  approveTrialRequest,
  listTrialRequests,
  rejectTrialRequest,
} from '../api/contribute'

const mockList = listTrialRequests as ReturnType<typeof vi.fn>
const mockApprove = approveTrialRequest as ReturnType<typeof vi.fn>
const mockReject = rejectTrialRequest as ReturnType<typeof vi.fn>

const pending = {
  id: 'r-1',
  email: 'kate@example.com',
  name: 'Kate',
  note: 'Thai please',
  status: 'pending',
  requested_at: '2026-08-09T10:00:00Z',
  decided_at: null,
}

function renderPanel() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <TrialRequestsPanel />
    </QueryClientProvider>,
  )
}

describe('TrialRequestsPanel', () => {
  beforeEach(() => vi.clearAllMocks())

  it('lists pending requests with their note', async () => {
    mockList.mockResolvedValue({ requests: [pending], available: true })
    renderPanel()
    expect(await screen.findByText(/kate@example.com/)).toBeDefined()
    expect(screen.getByText(/thai please/i)).toBeDefined()
    expect(screen.getByText('1 waiting')).toBeDefined()
  })

  it('approving shows the temporary password once, with the email status', async () => {
    mockList.mockResolvedValue({ requests: [pending], available: true })
    mockApprove.mockResolvedValue({
      email: 'kate@example.com',
      temp_password: 'kea-tui-9137',
      emailed: false,
    })
    renderPanel()
    await screen.findByText(/kate@example.com/)

    fireEvent.click(screen.getByRole('button', { name: /approve/i }))
    expect(await screen.findByText('kea-tui-9137')).toBeDefined()
    // Email is log-only here — the admin is told to hand it over manually.
    expect(screen.getByText(/copy it to them yourself/i)).toBeDefined()
    expect(mockApprove).toHaveBeenCalledWith('r-1')
  })

  it('rejecting calls the API for that request', async () => {
    mockList.mockResolvedValue({ requests: [pending], available: true })
    mockReject.mockResolvedValue(undefined)
    renderPanel()
    await screen.findByText(/kate@example.com/)
    fireEvent.click(screen.getByRole('button', { name: /reject/i }))
    await waitFor(() => expect(mockReject).toHaveBeenCalledWith('r-1'))
  })

  it('says so when the migration has not landed', async () => {
    mockList.mockResolvedValue({ requests: [], available: false })
    renderPanel()
    expect(
      await screen.findByText(/needs migration 20260921 applied/i),
    ).toBeDefined()
  })
})
