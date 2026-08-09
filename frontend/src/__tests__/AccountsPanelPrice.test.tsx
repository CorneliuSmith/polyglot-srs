/**
 * The generalized charge (owner): each account's monthly price is set from
 * the Accounts table. Dollars in the box, cents on the wire; blank returns
 * the account to standard plan pricing; 0 marks it free.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AccountsPanel from '../features/contribute/AccountsPanel'

vi.mock('../api/contribute', () => ({
  listAccounts: vi.fn(),
  listAllRoles: vi.fn(() => Promise.resolve([])),
  createAccount: vi.fn(),
  deleteAccount: vi.fn(),
  grantRole: vi.fn(),
  revokeRole: vi.fn(),
  overridePlan: vi.fn(),
  setTutorAccess: vi.fn(),
  setAccountPrice: vi.fn(() => Promise.resolve()),
}))

import { listAccounts, setAccountPrice } from '../api/contribute'

const mockList = listAccounts as ReturnType<typeof vi.fn>
const mockSetPrice = setAccountPrice as ReturnType<typeof vi.fn>

const account = (over: Record<string, unknown> = {}) => ({
  id: 'u-1',
  email: 'kate@beta.test',
  created_at: '2026-01-01T00:00:00Z',
  last_sign_in_at: null,
  plan_scope: 'all',
  plan_language: null,
  tutor_access: 'default',
  tutor_daily_cap: null,
  monthly_cents: null,
  price_currency: null,
  roles: [],
  cards: 12,
  languages_studied: 1,
  ...over,
})

function renderPanel() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <AccountsPanel languages={[]} selfId="admin-1" />
    </QueryClientProvider>,
  )
}

async function openAccounts() {
  fireEvent.click(screen.getByRole('button', { name: /manage accounts/i }))
  await screen.findByText('kate@beta.test')
}

describe('the per-account monthly charge', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('saves the typed dollars as cents', async () => {
    mockList.mockResolvedValue([account()])
    renderPanel()
    await openAccounts()

    const input = screen.getByLabelText(/monthly charge for kate@beta.test/i)
    fireEvent.change(input, { target: { value: '7.50' } })
    fireEvent.blur(input)
    await waitFor(() =>
      expect(mockSetPrice).toHaveBeenCalledWith('u-1', 750))
  })

  it('blank clears back to standard pricing', async () => {
    mockList.mockResolvedValue([account({ monthly_cents: 500 })])
    renderPanel()
    await openAccounts()

    const input = screen.getByLabelText(
      /monthly charge for kate@beta.test/i,
    ) as HTMLInputElement
    expect(input.value).toBe('5.00')
    fireEvent.change(input, { target: { value: '' } })
    fireEvent.blur(input)
    await waitFor(() =>
      expect(mockSetPrice).toHaveBeenCalledWith('u-1', null))
  })

  it('a zero price shows as a free account', async () => {
    mockList.mockResolvedValue([account({ monthly_cents: 0 })])
    renderPanel()
    await openAccounts()
    expect(await screen.findByText('free account')).toBeDefined()
  })

  it('an unchanged value spends no request', async () => {
    mockList.mockResolvedValue([account({ monthly_cents: 500 })])
    renderPanel()
    await openAccounts()

    const input = screen.getByLabelText(/monthly charge for kate@beta.test/i)
    fireEvent.blur(input)
    expect(mockSetPrice).not.toHaveBeenCalled()
  })
})
