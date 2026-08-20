import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ReviewInbox from '../features/contribute/ReviewInbox'

vi.mock('../api/contribute', () => ({
  getReviewInbox: vi.fn(),
}))

import { getReviewInbox } from '../api/contribute'
const mockGet = getReviewInbox as ReturnType<typeof vi.fn>

const ZERO = {
  grammar_pending: 0, pending_drills: 0, flagged_drills: 0, pending_examples: 0,
  flagged_examples: 0, translation_suggestions: 0, ai_levels: 0,
  change_requests: 0, suggestions: 0, notes: 0, feedback: 0, overlaps: 0,
  ai_translations: 0, tester_recommendations: 0, app_feedback: 0,
}

function renderInbox(onSwitchLanguage?: (id: string) => void) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  render(
    <QueryClientProvider client={qc}>
      <ReviewInbox languageId="lang-1" onSwitchLanguage={onSwitchLanguage} />
    </QueryClientProvider>,
  )
}

describe('ReviewInbox', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows only the non-empty queues with their counts and a total', async () => {
    mockGet.mockResolvedValue({
      counts: { ...ZERO, flagged_drills: 1, flagged_examples: 3, change_requests: 2 },
      can_publish: true,
    })
    renderInbox()
    expect(await screen.findByTestId('review-inbox')).toBeDefined()
    expect(screen.getByText(/6 awaiting/)).toBeDefined()
    expect(screen.getByText('Flagged drills')).toBeDefined()
    expect(screen.getByText('Flagged examples')).toBeDefined()
    expect(screen.getByText('Change requests')).toBeDefined()
    // Empty queues are not rendered.
    expect(screen.queryByText('Learner feedback')).toBeNull()
  })

  it('counts AI translations awaiting review, marked with their type', async () => {
    mockGet.mockResolvedValue({
      counts: { ...ZERO, ai_translations: 4 },
      can_publish: true,
      is_admin: true,
    })
    renderInbox()
    expect(await screen.findByTestId('review-inbox')).toBeDefined()
    expect(screen.getByText('AI translations')).toBeDefined()
    // The taxonomy answers all three of the owner's questions on the tile:
    // its origin section, who sees it, and where it is acted on.
    expect(screen.getByTestId('inbox-origin-ai')).toBeDefined()
    expect(screen.getByTestId('queue-audience-ai_translations'))
      .toHaveTextContent(/admins only/i)
    expect(screen.getByText('AI translations panel · Review tab')).toBeDefined()
    expect(screen.getByText(/4 awaiting/)).toBeDefined()
  })

  it('reads All clear when nothing is pending', async () => {
    mockGet.mockResolvedValue({ counts: ZERO, can_publish: false })
    renderInbox()
    expect(await screen.findByTestId('review-inbox')).toBeDefined()
    expect(screen.getByText(/All clear/)).toBeDefined()
  })

  it('counts tester recommendations as a queue of their own', async () => {
    // The testers' main deliverable used to be counted nowhere.
    mockGet.mockResolvedValue({
      counts: { ...ZERO, tester_recommendations: 5 },
      can_publish: true,
    })
    renderInbox()
    expect(await screen.findByText('Tester recommendations')).toBeDefined()
    expect(screen.getByText(/5 awaiting/)).toBeDefined()
  })

  it('hides the admin-only AI translations tile from a non-admin', async () => {
    // GET /translation-reviews is admin-only: a tile a reviewer cannot open
    // sends them hunting for a panel that silently 403'd.
    mockGet.mockResolvedValue({
      counts: { ...ZERO, ai_translations: 12 },
      can_publish: true,
      is_admin: false,
    })
    renderInbox()
    expect(await screen.findByTestId('review-inbox')).toBeDefined()
    expect(screen.queryByText('AI translations')).toBeNull()
    // …and it doesn't inflate the total either.
    expect(screen.getByText(/All clear/)).toBeDefined()
  })

  it('hides reviewer-only queues from a tester', async () => {
    mockGet.mockResolvedValue({
      counts: { ...ZERO, feedback: 3, notes: 2, pending_drills: 1 },
      can_publish: false,
      is_admin: false,
    })
    renderInbox()
    expect(await screen.findByTestId('review-inbox')).toBeDefined()
    expect(screen.queryByText('Learner feedback')).toBeNull()
    expect(screen.queryByText('Review notes')).toBeNull()
    expect(screen.getByText('Generated drills')).toBeDefined()
    expect(screen.getByText(/1 awaiting/)).toBeDefined()
  })

  it('says "showing first N of M" when a count exceeds the panel limit', async () => {
    mockGet.mockResolvedValue({
      counts: { ...ZERO, feedback: 150 },
      can_publish: true,
    })
    renderInbox()
    expect(await screen.findByText(/showing first 100 of 150/)).toBeDefined()
  })
})

describe('ReviewInbox — other languages', () => {
  beforeEach(() => vi.clearAllMocks())

  const HEBREW = {
    id: 'lang-he', code: 'he', name: 'Hebrew', total: 7, counts: { ...ZERO, feedback: 7 },
  }

  it('surfaces work in other languages even when this one is all clear', async () => {
    // The whole complaint: the admin's selector sat on Arabic while the
    // testers were exercising Hebrew, so the inbox said "All clear".
    mockGet.mockResolvedValue({
      counts: ZERO,
      other_languages: [HEBREW],
      can_publish: true,
    })
    renderInbox()
    const strip = await screen.findByTestId('inbox-other-languages')
    expect(strip.textContent).toContain('Hebrew')
    expect(strip.textContent).toContain('7')
    // Still "All clear" for the CURRENT language — the strip is the extra.
    expect(screen.getByText(/All clear/)).toBeDefined()
  })

  it('switches the working language when a language is clicked', async () => {
    const onSwitch = vi.fn()
    mockGet.mockResolvedValue({
      counts: ZERO,
      other_languages: [HEBREW],
      can_publish: true,
    })
    renderInbox(onSwitch)
    fireEvent.click(await screen.findByRole('button', { name: /Hebrew/ }))
    expect(onSwitch).toHaveBeenCalledWith('lang-he')
  })

  it('renders no strip when nothing is waiting elsewhere', async () => {
    mockGet.mockResolvedValue({
      counts: { ...ZERO, feedback: 1 },
      other_languages: [],
      can_publish: true,
    })
    renderInbox()
    expect(await screen.findByTestId('review-inbox')).toBeDefined()
    expect(screen.queryByTestId('inbox-other-languages')).toBeNull()
  })
})


describe('the four streams, visible as themselves', () => {
  it('groups the tiles by origin with subtotals', async () => {
    mockGet.mockResolvedValue({
      counts: {
        ...ZERO,
        notes: 2,                 // a report from a person
        pending_drills: 3,        // AI awaiting a human
        grammar_pending: 1,       // a contribution awaiting approval
        app_feedback: 4,          // general feedback
      },
      can_publish: true,
      is_admin: true,
    })
    renderInbox()
    await screen.findByTestId('review-inbox')
    for (const origin of ['reports', 'general', 'ai', 'contributions']) {
      expect(screen.getByTestId(`inbox-origin-${origin}`)).toBeDefined()
    }
    // The general-feedback tile names where it is acted on.
    expect(screen.getByText('General feedback queue · Review tab')).toBeDefined()
  })

  it('keeps the general-feedback tile away from a non-admin reviewer', async () => {
    // The panel behind it refuses non-admins; a tile with no panel behind
    // it reads as a broken inbox.
    mockGet.mockResolvedValue({
      counts: { ...ZERO, app_feedback: 4, notes: 1 },
      can_publish: true,
      is_admin: false,
    })
    renderInbox()
    await screen.findByTestId('review-inbox')
    expect(screen.queryByTestId('inbox-origin-general')).toBeNull()
    expect(screen.queryByText('App feedback')).toBeNull()
    // …and the header total counts only what this viewer can act on.
    expect(screen.getByText('1 awaiting')).toBeDefined()
  })

  it('a quiet origin contributes no empty section', async () => {
    mockGet.mockResolvedValue({
      counts: { ...ZERO, notes: 2 },
      can_publish: true,
      is_admin: true,
    })
    renderInbox()
    await screen.findByTestId('review-inbox')
    expect(screen.getByTestId('inbox-origin-reports')).toBeDefined()
    expect(screen.queryByTestId('inbox-origin-ai')).toBeNull()
    expect(screen.queryByTestId('inbox-origin-contributions')).toBeNull()
  })
})
