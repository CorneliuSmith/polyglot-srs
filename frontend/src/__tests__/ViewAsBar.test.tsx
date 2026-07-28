import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ViewAsBar from '../components/ViewAsBar'
import { useViewAsStore } from '../stores/viewAsStore'

vi.mock('../api/contribute', () => ({ getMyRoles: vi.fn() }))
import { getMyRoles } from '../api/contribute'
const mockRoles = getMyRoles as ReturnType<typeof vi.fn>

function renderBar() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={qc}>
      <ViewAsBar />
    </QueryClientProvider>,
  )
  return qc
}

describe('ViewAsBar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useViewAsStore.setState({ viewAs: null })
  })

  it('renders nothing for a non-admin', async () => {
    mockRoles.mockResolvedValue({ roles: [], is_admin: false, real_is_admin: false })
    renderBar()
    await waitFor(() => expect(mockRoles).toHaveBeenCalled())
    expect(screen.queryByTestId('view-as-bar')).toBeNull()
  })

  it('offers every level to a real admin', async () => {
    mockRoles.mockResolvedValue({
      roles: [{ language_id: null, role: 'admin' }],
      is_admin: true,
      real_is_admin: true,
    })
    renderBar()
    expect(await screen.findByTestId('view-as-bar')).toBeDefined()
    for (const label of ['Admin (you)', 'Learner', 'Trial reviewer', 'Contributor', 'Reviewer']) {
      expect(screen.getByRole('button', { name: label }), label).toBeDefined()
    }
  })

  it('switching level updates the store and shows the preview warning', async () => {
    mockRoles.mockResolvedValue({
      roles: [{ language_id: null, role: 'admin' }],
      is_admin: true,
      real_is_admin: true,
    })
    renderBar()
    fireEvent.click(await screen.findByRole('button', { name: 'Contributor' }))

    expect(useViewAsStore.getState().viewAs).toBe('contributor')
    expect(screen.getByText(/viewing as contributor/i)).toBeDefined()
    expect(screen.getByText(/your real access is unchanged/i)).toBeDefined()
  })

  it('stays visible while previewing, so the way back is always reachable', async () => {
    // The bar reads real_is_admin, NOT is_admin — the preview zeroes the
    // latter, which would otherwise hide the control that ends the preview.
    useViewAsStore.setState({ viewAs: 'learner' })
    mockRoles.mockResolvedValue({
      roles: [],
      is_admin: false, // as downgraded by the active preview
      real_is_admin: true,
    })
    renderBar()
    expect(await screen.findByTestId('view-as-bar')).toBeDefined()

    fireEvent.click(screen.getByRole('button', { name: 'Admin (you)' }))
    expect(useViewAsStore.getState().viewAs).toBeNull()
  })
})
