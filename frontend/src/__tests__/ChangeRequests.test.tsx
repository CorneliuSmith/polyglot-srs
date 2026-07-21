import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import SuggestChange from '../features/contribute/SuggestChange'
import ChangeRequestsPanel from '../features/contribute/ChangeRequestsPanel'
import { canSuggestForLanguage } from '../api/contribute'

vi.mock('../api/contribute', async (orig) => {
  const actual = await orig<typeof import('../api/contribute')>()
  return {
    ...actual,
    getMyRoles: vi.fn(),
    createChangeRequest: vi.fn(),
    getChangeRequests: vi.fn(),
    voteChangeRequest: vi.fn(),
    resolveChangeRequest: vi.fn(),
  }
})

import {
  createChangeRequest,
  getChangeRequests,
  getMyRoles,
  resolveChangeRequest,
  voteChangeRequest,
} from '../api/contribute'

const mockRoles = getMyRoles as ReturnType<typeof vi.fn>
const mockCreate = createChangeRequest as ReturnType<typeof vi.fn>
const mockGet = getChangeRequests as ReturnType<typeof vi.fn>
const mockVote = voteChangeRequest as ReturnType<typeof vi.fn>
const mockResolve = resolveChangeRequest as ReturnType<typeof vi.fn>

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

describe('canSuggestForLanguage', () => {
  it('admin anywhere; contributor/reviewer only for their language', () => {
    expect(canSuggestForLanguage([{ role: 'admin', language_id: null }], 'ca')).toBe(true)
    expect(canSuggestForLanguage([{ role: 'reviewer', language_id: 'ca' }], 'ca')).toBe(true)
    expect(canSuggestForLanguage([{ role: 'contributor', language_id: 'ca' }], 'ca')).toBe(true)
    expect(canSuggestForLanguage([{ role: 'reviewer', language_id: 'ru' }], 'ca')).toBe(false)
    expect(canSuggestForLanguage([], 'ca')).toBe(false)
  })
})

describe('SuggestChange', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders nothing for a plain learner', async () => {
    mockRoles.mockResolvedValue({ roles: [], is_admin: false })
    wrap(<SuggestChange languageId="ca" targetType="drill" />)
    await waitFor(() => expect(mockRoles).toHaveBeenCalled())
    expect(screen.queryByText(/suggest a change/i)).toBeNull()
  })

  it('a reviewer can open the form and send a request', async () => {
    mockRoles.mockResolvedValue({
      roles: [{ role: 'reviewer', language_id: 'ca' }],
      is_admin: false,
    })
    mockCreate.mockResolvedValue({ id: 'cr-1' })
    wrap(
      <SuggestChange
        languageId="ca"
        targetType="drill"
        targetId="d1"
        targetLabel="El meva cotxe és nou."
      />,
    )
    fireEvent.click(await screen.findByRole('button', { name: /suggest a change/i }))
    fireEvent.change(screen.getByPlaceholderText(/what's wrong/i), {
      target: { value: 'meva should be meu' },
    })
    fireEvent.click(screen.getByRole('button', { name: /send to review board/i }))
    await waitFor(() =>
      expect(mockCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          language_id: 'ca',
          field: 'sentence',
          issue: 'meva should be meu',
          target_label: 'El meva cotxe és nou.',
        }),
      ),
    )
    expect(await screen.findByText(/sent to the review board/i)).toBeDefined()
  })
})

describe('ChangeRequestsPanel', () => {
  beforeEach(() => vi.clearAllMocks())

  const req = {
    id: 'cr-1', target_type: 'drill', target_id: 'd1',
    target_label: 'El meva cotxe és nou.', field: 'sentence',
    issue: 'meva should be meu', suggestion: 'El meu cotxe és nou.',
    status: 'open', author_email: 'friend@beta.test',
    score: 3, upvotes: 3, downvotes: 0, my_vote: 0,
    created_at: '2026-07-21T00:00:00Z',
  }

  it('lists requests with the score and suggestion', async () => {
    mockGet.mockResolvedValue({ requests: [req], can_resolve: false })
    wrap(<ChangeRequestsPanel languageId="ca" />)
    expect(await screen.findByText(/meva should be meu/)).toBeDefined()
    expect(screen.getByText('3')).toBeDefined()
    expect(screen.getByText(/El meu cotxe és nou/)).toBeDefined()
    // Reviewer (not admin) sees no Accept/Reject.
    expect(screen.queryByRole('button', { name: /^accept$/i })).toBeNull()
  })

  it('upvoting calls the vote API', async () => {
    mockGet.mockResolvedValue({ requests: [req], can_resolve: false })
    mockVote.mockResolvedValue(undefined)
    wrap(<ChangeRequestsPanel languageId="ca" />)
    fireEvent.click(await screen.findByRole('button', { name: /upvote/i }))
    await waitFor(() => expect(mockVote).toHaveBeenCalledWith('cr-1', 1))
  })

  it('admins get Accept/Reject that resolve the request', async () => {
    mockGet.mockResolvedValue({ requests: [req], can_resolve: true })
    mockResolve.mockResolvedValue(undefined)
    wrap(<ChangeRequestsPanel languageId="ca" />)
    fireEvent.click(await screen.findByRole('button', { name: /^accept$/i }))
    await waitFor(() => expect(mockResolve).toHaveBeenCalledWith('cr-1', 'accepted'))
  })
})
