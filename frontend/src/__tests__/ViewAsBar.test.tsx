import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ViewAsBar from '../components/ViewAsBar'
import { useViewAsStore } from '../stores/viewAsStore'

vi.mock('../api/contribute', () => ({ getMyRoles: vi.fn() }))
import { getMyRoles } from '../api/contribute'
const mockRoles = getMyRoles as ReturnType<typeof vi.fn>

const ADMIN = {
  roles: [{ language_id: null, role: 'admin' }],
  is_admin: true,
  real_is_admin: true,
}

function renderBar() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={qc}>
      <ViewAsBar />
    </QueryClientProvider>,
  )
  return qc
}

const picker = () => screen.getByLabelText(/view(ing)? as/i) as HTMLSelectElement

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
    mockRoles.mockResolvedValue(ADMIN)
    renderBar()
    expect(await screen.findByTestId('view-as-bar')).toBeDefined()
    for (const label of [
      'Admin (you)', 'Learner', 'Tester', 'Contributor', 'Reviewer',
    ]) {
      expect(screen.getByRole('option', { name: label }), label).toBeDefined()
    }
  })

  it('switching level updates the store and shows the preview warning', async () => {
    mockRoles.mockResolvedValue(ADMIN)
    renderBar()
    await screen.findByTestId('view-as-bar')
    fireEvent.change(picker(), { target: { value: 'contributor' } })

    expect(useViewAsStore.getState().viewAs).toBe('contributor')
    expect(screen.getByText(/viewing as/i)).toBeDefined()
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

    fireEvent.click(screen.getByRole('button', { name: /exit preview/i }))
    expect(useViewAsStore.getState().viewAs).toBeNull()
  })

  it('the picker also walks back to Admin without the exit button', async () => {
    useViewAsStore.setState({ viewAs: 'reviewer' })
    mockRoles.mockResolvedValue({ ...ADMIN, is_admin: false })
    renderBar()
    await screen.findByTestId('view-as-bar')
    fireEvent.change(picker(), { target: { value: '' } })
    expect(useViewAsStore.getState().viewAs).toBeNull()
  })

  it('sticks to the top so it survives scrolling into a session', async () => {
    // The original bar sat in normal flow: on a phone it scrolled away the
    // moment a learn session started, which is exactly when an admin wants
    // to check what a learner sees.
    mockRoles.mockResolvedValue(ADMIN)
    renderBar()
    const bar = await screen.findByTestId('view-as-bar')
    expect(bar.className).toContain('sticky')
    expect(bar.className).toContain('top-0')
  })

  it('stays one row wide — a single control, not a wrapping chip set', async () => {
    mockRoles.mockResolvedValue(ADMIN)
    renderBar()
    await screen.findByTestId('view-as-bar')
    // One <select> replaces five buttons; nothing to wrap at 320px.
    expect(screen.getAllByRole('combobox')).toHaveLength(1)
    expect(screen.queryAllByRole('button')).toHaveLength(0)
  })
})
