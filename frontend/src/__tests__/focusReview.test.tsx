import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ChangeRequestsPanel from '../features/contribute/ChangeRequestsPanel'
import ReviewInbox from '../features/contribute/ReviewInbox'
import QueueHelp, { QUEUE_HELP } from '../features/contribute/QueueHelp'
import { QUEUE_META } from '../lib/reviewTaxonomy'

vi.mock('../api/contribute', async (orig) => ({
  ...(await orig<typeof import('../api/contribute')>()),
  getChangeRequests: vi.fn(),
  voteChangeRequest: vi.fn(() => Promise.resolve()),
  resolveChangeRequest: vi.fn(() => Promise.resolve()),
  getReviewInbox: vi.fn(),
}))

import {
  getChangeRequests,
  getReviewInbox,
  resolveChangeRequest,
} from '../api/contribute'

const mockRequests = getChangeRequests as ReturnType<typeof vi.fn>
const mockInbox = getReviewInbox as ReturnType<typeof vi.fn>
const mockResolve = resolveChangeRequest as ReturnType<typeof vi.fn>

function req(id: string, issue: string) {
  return {
    id,
    target_type: 'vocabulary',
    target_id: `w-${id}`,
    target_label: `word ${id}`,
    field: 'hint',
    issue,
    suggestion: null,
    status: 'open',
    quote: null,
    quote_context: {},
    author_email: 'tester@example.com',
    is_advisory: true,
    score: 0,
    upvotes: 0,
    downvotes: 0,
    my_vote: 0,
    created_at: '2026-08-01T00:00:00Z',
  }
}

function renderWith(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

describe('focus mode: one review item at a time', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockRequests.mockResolvedValue({
      requests: [req('a', 'Gives answer away'), req('b', 'Makes no sense'),
                 req('c', 'Hint is wrong')],
      can_resolve: true,
      can_vote: true,
    })
  })

  it('shows the whole board when focus is off', async () => {
    renderWith(<ChangeRequestsPanel languageId="lang-1" />)
    expect(await screen.findByText('Gives answer away')).toBeDefined()
    expect(screen.getByText('Makes no sense')).toBeDefined()
    expect(screen.getByText('Hint is wrong')).toBeDefined()
    // No stepper when you asked for the list.
    expect(screen.queryByTestId('focus-nav')).toBeNull()
  })

  it('shows one at a time, and ‹ › walks the queue', async () => {
    renderWith(<ChangeRequestsPanel languageId="lang-1" focus />)

    expect(await screen.findByText('Gives answer away')).toBeDefined()
    expect(screen.queryByText('Makes no sense')).toBeNull()
    expect(screen.getByTestId('focus-nav')).toBeDefined()
    expect(screen.getByText(/of 3 change requests/)).toBeDefined()

    fireEvent.click(screen.getByRole('button', { name: /next change request/i }))
    expect(screen.getByText('Makes no sense')).toBeDefined()
    expect(screen.queryByText('Gives answer away')).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: /previous change request/i }))
    expect(screen.getByText('Gives answer away')).toBeDefined()
  })

  it('stops at both ends rather than wrapping', async () => {
    renderWith(<ChangeRequestsPanel languageId="lang-1" focus />)
    await screen.findByText('Gives answer away')

    const prev = screen.getByRole('button', { name: /previous change request/i })
    const next = screen.getByRole('button', { name: /next change request/i })
    expect((prev as HTMLButtonElement).disabled).toBe(true)

    fireEvent.click(next)
    fireEvent.click(next)
    expect(screen.getByText('Hint is wrong')).toBeDefined()
    expect((next as HTMLButtonElement).disabled).toBe(true)
  })

  it('the arrow keys move too', async () => {
    renderWith(<ChangeRequestsPanel languageId="lang-1" focus />)
    await screen.findByText('Gives answer away')

    fireEvent.keyDown(window, { key: 'ArrowRight' })
    expect(screen.getByText('Makes no sense')).toBeDefined()
    fireEvent.keyDown(window, { key: 'ArrowLeft' })
    expect(screen.getByText('Gives answer away')).toBeDefined()
  })

  it('an arrow typed into a text field moves the cursor, not the queue', async () => {
    renderWith(<ChangeRequestsPanel languageId="lang-1" focus />)
    await screen.findByText('Gives answer away')

    // A reviewer writing a note must be able to press ← without the card
    // they are describing jumping out from under them.
    const input = document.createElement('input')
    document.body.appendChild(input)
    fireEvent.keyDown(input, { key: 'ArrowRight' })
    expect(screen.getByText('Gives answer away')).toBeDefined()
    input.remove()
  })

  it('acting on an item lands you on the next one — the queue clears itself', async () => {
    renderWith(<ChangeRequestsPanel languageId="lang-1" focus />)
    await screen.findByText('Gives answer away')

    // Accepting removes it server-side; the refetch returns the shorter list
    // and the reviewer stays at the same index, which is the next item.
    mockRequests.mockResolvedValue({
      requests: [req('b', 'Makes no sense'), req('c', 'Hint is wrong')],
      can_resolve: true,
      can_vote: true,
    })
    fireEvent.click(screen.getByRole('button', { name: 'Accept' }))

    await waitFor(() => expect(mockResolve).toHaveBeenCalledWith('a', 'accepted'))
    expect(await screen.findByText('Makes no sense')).toBeDefined()
    expect(screen.getByText(/of 2 change requests/)).toBeDefined()
  })

  it('clamps back rather than showing an empty frame on the last item', async () => {
    mockRequests.mockResolvedValue({
      requests: [req('a', 'Gives answer away'), req('b', 'Makes no sense')],
      can_resolve: true,
      can_vote: true,
    })
    renderWith(<ChangeRequestsPanel languageId="lang-1" focus />)
    await screen.findByText('Gives answer away')

    fireEvent.click(screen.getByRole('button', { name: /next change request/i }))
    expect(screen.getByText('Makes no sense')).toBeDefined()

    mockRequests.mockResolvedValue({
      requests: [req('a', 'Gives answer away')],
      can_resolve: true,
      can_vote: true,
    })
    fireEvent.click(screen.getByRole('button', { name: 'Accept' }))
    expect(await screen.findByText('Gives answer away')).toBeDefined()
  })

  it('keeps the full card and its actions — focus is the same card, not a summary', async () => {
    renderWith(<ChangeRequestsPanel languageId="lang-1" focus />)
    await screen.findByText('Gives answer away')
    // Votes, the advisory marking and both decisions all survive the mode.
    expect(screen.getByRole('button', { name: 'Upvote' })).toBeDefined()
    expect(screen.getByRole('button', { name: 'Downvote' })).toBeDefined()
    expect(screen.getByText('advisory')).toBeDefined()
    expect(screen.getByRole('button', { name: 'Accept' })).toBeDefined()
    expect(screen.getByRole('button', { name: 'Reject' })).toBeDefined()
  })
})

describe('inbox tiles open a queue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockInbox.mockResolvedValue({
      counts: { change_requests: 5, overlaps: 2 },
      is_admin: true,
      can_publish: true,
      other_languages: [],
    })
  })

  it('a queue acted on here is a button that focuses its panel', async () => {
    const onFocus = vi.fn()
    renderWith(<ReviewInbox languageId="lang-1" onFocusQueue={onFocus} />)

    const tile = await screen.findByTestId('queue-tile-change_requests')
    fireEvent.click(tile)
    expect(onFocus).toHaveBeenCalledWith('change-requests')
  })

  it('a queue acted on somewhere else is not clickable', async () => {
    const onFocus = vi.fn()
    renderWith(<ReviewInbox languageId="lang-1" onFocusQueue={onFocus} />)

    // Overlaps lives in Settings, not this tab — clicking could only scope
    // the page to nothing, so the tile stays a label.
    const tile = await screen.findByTestId('queue-tile-overlaps')
    fireEvent.click(tile)
    expect(onFocus).not.toHaveBeenCalled()
  })
})

describe('queue help', () => {
  it('every focusable queue has help text written for it', () => {
    for (const meta of QUEUE_META) {
      if (!meta.panel) continue
      expect(QUEUE_HELP[meta.panel], `no help for ${meta.panel}`).toBeDefined()
    }
  })

  it('says what an action DOES, which is the part nobody could tell', () => {
    render(
      <QueueHelp title="Card feedback" help={QUEUE_HELP.feedback} />,
    )
    expect(screen.queryByTestId('queue-help-body')).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: /what is card feedback/i }))
    const body = screen.getByTestId('queue-help-body')
    expect(body.textContent).toContain('Resolve')
    // The specific confusion that prompted this: does Resolve change the
    // card? It does not, and the text has to say so.
    expect(body.textContent).toContain('does not change the card')
  })

  it('warns where an action deletes rather than files away', () => {
    render(
      <QueueHelp title="Generated drills" help={QUEUE_HELP['generated-drills']} />,
    )
    fireEvent.click(screen.getByRole('button', { name: /what is generated drills/i }))
    expect(screen.getByTestId('queue-help-body').textContent).toContain('DELETES')
  })

  it('closes on Escape', () => {
    render(<QueueHelp title="Card feedback" help={QUEUE_HELP.feedback} />)
    fireEvent.click(screen.getByRole('button', { name: /what is card feedback/i }))
    expect(screen.getByTestId('queue-help-body')).toBeDefined()
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByTestId('queue-help-body')).toBeNull()
  })
})
