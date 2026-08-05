import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import StaffBar from '../components/StaffBar'

vi.mock('../api/contribute', () => ({
  getMyRoles: vi.fn(() => Promise.resolve({ roles: ['reviewer'] })),
  canSuggestForLanguage: () => true,
}))
vi.mock('../stores/viewAsStore', () => ({
  useViewAsKey: () => 'self',
  useViewAsStore: vi.fn(() => null),
}))
vi.mock('./ViewAsBar', () => ({ default: () => null }))
vi.mock('../components/ViewAsBar', () => ({ default: () => null }))
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn((s: (x: Record<string, unknown>) => unknown) =>
    s({ activeLanguageId: 'lang-es' }),
  ),
}))

let reviewMode = false
const setReviewMode = vi.fn((v: boolean) => {
  reviewMode = v
})
vi.mock('../stores/reviewModeStore', () => ({
  useReviewModeStore: vi.fn((s: (x: Record<string, unknown>) => unknown) =>
    s({ reviewMode, setReviewMode }),
  ),
}))

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}))

function renderBar() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <StaffBar />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('StaffBar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    reviewMode = false
  })

  it('starts collapsed, so admin scaffolding is not the top of every screen', async () => {
    renderBar()
    // Still visible as a chip — collapsed, not removed. Losing the way into
    // review mode would be worse than the row it was costing.
    expect(await screen.findByTestId('staff-bar-expand')).toBeInTheDocument()
    expect(screen.queryByRole('checkbox')).toBeNull()
  })

  it('expands on request and collapses again', async () => {
    renderBar()
    fireEvent.click(await screen.findByTestId('staff-bar-expand'))
    expect(screen.getByRole('checkbox')).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('staff-bar-collapse'))
    expect(await screen.findByTestId('staff-bar-expand')).toBeInTheDocument()
  })

  it('forces itself open while review mode is ON', async () => {
    // A flagging mode you cannot see you are in is worse than a bar you
    // did not want — so it refuses to hide, and offers no collapse.
    reviewMode = true
    renderBar()
    expect(await screen.findByRole('checkbox')).toBeChecked()
    expect(screen.queryByTestId('staff-bar-expand')).toBeNull()
    expect(screen.queryByTestId('staff-bar-collapse')).toBeNull()
  })
})
