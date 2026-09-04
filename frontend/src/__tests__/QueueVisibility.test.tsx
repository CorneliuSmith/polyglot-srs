import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import IssuesPanel from '../features/contribute/IssuesPanel'
import TesterRecommendationsPanel from '../features/contribute/TesterRecommendationsPanel'

vi.mock('../api/contribute', () => ({
  getReviewNotes: vi.fn(),
  resolveReviewNote: vi.fn(),
  getTesterRecommendations: vi.fn(),
}))

import { getReviewNotes, getTesterRecommendations } from '../api/contribute'
const mockNotes = getReviewNotes as ReturnType<typeof vi.fn>
const mockRecos = getTesterRecommendations as ReturnType<typeof vi.fn>

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

/* Gap G5: these panels used to return null on BOTH "empty" and "failed", so
 * a broken queue endpoint looked exactly like a quiet day and the admin
 * concluded the testers weren't submitting. */
describe('queue panels distinguish empty from broken', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders nothing when the queue is genuinely empty', async () => {
    mockNotes.mockResolvedValue([])
    const { container } = wrap(
      <IssuesPanel languageId="l1" canResolve awaiting={0} />,
    )
    await waitFor(() => expect(mockNotes).toHaveBeenCalled())
    expect(container.querySelector('[data-testid="issues-panel-status"]')).toBeNull()
  })

  it('says so out loud when the fetch fails', async () => {
    mockNotes.mockRejectedValue(new Error('boom'))
    wrap(<IssuesPanel languageId="l1" canResolve awaiting={0} />)
    const row = await screen.findByTestId('issues-panel-status')
    expect(row.textContent).toMatch(/couldn’t load/i)
    expect(row.getAttribute('role')).toBe('alert')
  })

  it('flags the mismatch when the inbox counts work the list did not load', async () => {
    mockNotes.mockResolvedValue([])
    wrap(<IssuesPanel languageId="l1" canResolve awaiting={4} />)
    const row = await screen.findByTestId('issues-panel-status')
    expect(row.textContent).toMatch(/4 awaiting · none loaded/i)
  })
})

/* Gap G4: the tester's written reason existed only as a tooltip on a row
 * that the next bulk-approve would delete. */
describe('TesterRecommendationsPanel', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders the note as visible text, with the sentence it is about', async () => {
    mockRecos.mockResolvedValue({
      recommendations: [
        {
          id: 'r1', target_type: 'example', target_id: 'e1',
          recommendation: 'reject', note: "'Leo' reads as the name Leo here.",
          recommender_email: 'tester@example.com', target_label: 'Leo un libro.',
          target_translation: 'I read a book.', context: 'libro',
          created_at: '2026-08-12T09:14:22Z',
        },
      ],
      limit: 200,
      can_publish: true,
    })
    wrap(<TesterRecommendationsPanel languageId="l1" languageCode="es" awaiting={1} />)
    const panel = await screen.findByTestId('tester-recommendations')
    expect(panel.textContent).toContain("'Leo' reads as the name Leo here.")
    expect(panel.textContent).toContain('Leo un libro.')
    expect(panel.textContent).toContain('tester@example.com')
    expect(screen.getByText('needs work')).toBeDefined()
  })

  it('says what the recommendation IS, and when there is no note says so', async () => {
    // The verdict used to be only a badge in the corner; the owner read the
    // row as a card with no recommendation on it ("I don't see an actual
    // recommendation anywhere").
    mockRecos.mockResolvedValue({
      recommendations: [
        {
          id: 'r1', target_type: 'drill', target_id: 'd1',
          recommendation: 'approve', note: '',
          recommender_email: 'tester@example.com',
          target_label: 'Vosotros {{answer}} cerca de la playa.',
          target_translation: 'You all live near the beach.',
          context: 'Present tense', created_at: '2026-09-04T09:00:00Z',
        },
      ],
      limit: 200,
      can_publish: true,
    })
    wrap(<TesterRecommendationsPanel languageId="l1" languageCode="es" awaiting={1} />)
    expect((await screen.findByTestId('reco-verdict-r1')).textContent).toBe(
      'Recommends: approve this item',
    )
    expect(screen.getByTestId('reco-no-note-r1').textContent).toMatch(/whole recommendation/)
  })

  it('shows a visible row when the inbox counts recommendations it could not load', async () => {
    mockRecos.mockResolvedValue({ recommendations: [], limit: 200, can_publish: false })
    wrap(<TesterRecommendationsPanel languageId="l1" awaiting={3} />)
    const row = await screen.findByTestId('tester-recommendations-status')
    expect(row.textContent).toMatch(/3 awaiting · none loaded/i)
  })
})
