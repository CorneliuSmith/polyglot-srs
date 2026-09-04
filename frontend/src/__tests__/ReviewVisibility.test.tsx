import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ReviewInbox from '../features/contribute/ReviewInbox'
import ChangeRequestsPanel from '../features/contribute/ChangeRequestsPanel'
import FeedbackPanel from '../features/contribute/FeedbackPanel'
import TesterRecommendationsPanel from '../features/contribute/TesterRecommendationsPanel'
import TranslationReviewsPanel from '../features/contribute/TranslationReviewsPanel'
import VocabReviewPanel from '../features/contribute/VocabReviewPanel'

/**
 * Regression tests for "testers submit reviews, the admin never sees them".
 *
 * The submissions were always in the database. What made them invisible was
 * the read side, in two ways this file pins down:
 *
 *  1. the workspace is scoped to ONE language while a submission carries the
 *     language its author was studying, so the admin's tiles were honestly
 *     empty and told the wrong story;
 *  2. a queue panel that renders nothing on a failed fetch is
 *     indistinguishable from a queue with nothing in it — and "nothing in
 *     it" is exactly the wrong conclusion.
 */

vi.mock('../api/contribute', async (orig) => ({
  ...(await orig<typeof import('../api/contribute')>()),
  getReviewInbox: vi.fn(),
  getChangeRequests: vi.fn(),
  voteChangeRequest: vi.fn(),
  resolveChangeRequest: vi.fn(),
  getFeedback: vi.fn(),
  resolveFeedback: vi.fn(),
  getTesterRecommendations: vi.fn(),
  getTranslationReviews: vi.fn(),
  getVocabForLanguage: vi.fn(),
  getMyRoles: vi.fn(() =>
    Promise.resolve({ roles: [{ role: 'reviewer', language_id: null }], is_admin: false }),
  ),
}))

import {
  getReviewInbox,
  getChangeRequests,
  getFeedback,
  getTesterRecommendations,
  getTranslationReviews,
  getVocabForLanguage,
} from '../api/contribute'

const mockInbox = getReviewInbox as ReturnType<typeof vi.fn>
const mockRequests = getChangeRequests as ReturnType<typeof vi.fn>
const mockFeedback = getFeedback as ReturnType<typeof vi.fn>
const mockRecos = getTesterRecommendations as ReturnType<typeof vi.fn>
const mockTranslations = getTranslationReviews as ReturnType<typeof vi.fn>
const mockVocab = getVocabForLanguage as ReturnType<typeof vi.fn>

const ZERO = {
  grammar_pending: 0, pending_drills: 0, flagged_drills: 0, pending_examples: 0,
  flagged_examples: 0, translation_suggestions: 0, ai_levels: 0,
  change_requests: 0, suggestions: 0, notes: 0, feedback: 0, overlaps: 0,
  ai_translations: 0, tester_recommendations: 0,
}

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

/* ── 1. the language the admin is not looking at ───────────────────────── */

describe('ReviewInbox — work in a language the selector is not on', () => {
  beforeEach(() => vi.clearAllMocks())

  const hebrew = {
    id: 'lang-he', code: 'he', name: 'Hebrew', total: 6,
    counts: { ...ZERO, tester_recommendations: 4, notes: 2 },
  }
  const latin = {
    id: 'lang-la', code: 'la', name: 'Latin', total: 3,
    counts: { ...ZERO, change_requests: 3 },
  }

  it('tells a TESTER too, whose tiles are filtered but whose reports are the ones going missing', async () => {
    // The reported failure, from the seat it was reported in: this language
    // is genuinely all clear, and the strip is the only thing that says the
    // work exists. The tile list is filtered by role (can_publish false
    // hides reviewer-only queues) — the strip must not be filtered with it,
    // or the one person who knows they filed something is told nothing did.
    mockInbox.mockResolvedValue({
      counts: ZERO,
      other_languages: [hebrew],
      can_publish: false,
      is_admin: false,
    })
    wrap(<ReviewInbox languageId="lang-ar" />)

    const strip = await screen.findByTestId('inbox-other-languages')
    expect(strip.textContent).toContain('Hebrew')
    expect(strip.textContent).toContain('6')
    // The "nothing arrived" reading is still on screen for THIS language —
    // and no longer the whole story.
    expect(screen.getByText(/All clear/)).toBeDefined()
    expect(strip.textContent).toMatch(/testers file against the\s+language they were studying/)
  })

  it('sums every other language, and names how many there are', async () => {
    mockInbox.mockResolvedValue({
      counts: ZERO,
      other_languages: [hebrew, latin],
      can_publish: true,
      is_admin: true,
    })
    wrap(<ReviewInbox languageId="lang-ar" />)

    const strip = await screen.findByTestId('inbox-other-languages')
    expect(strip.textContent).toContain('9 awaiting in 2 other languages')
    expect(strip.textContent).toContain('Latin')
  })

  it('switches the workspace to the language holding the work', async () => {
    // Naming the language is only half a fix if getting there is a hunt.
    const onSwitch = vi.fn()
    mockInbox.mockResolvedValue({
      counts: ZERO, other_languages: [hebrew, latin], can_publish: true,
    })
    wrap(<ReviewInbox languageId="lang-ar" onSwitchLanguage={onSwitch} />)
    fireEvent.click(await screen.findByRole('button', { name: /Latin/ }))
    expect(onSwitch).toHaveBeenCalledWith('lang-la')
  })

  it('stays quiet when the work really is only here', async () => {
    // The strip has to be trustworthy in both directions, or it becomes
    // noise that gets ignored on the day it matters.
    mockInbox.mockResolvedValue({
      counts: { ...ZERO, notes: 2 }, other_languages: [], can_publish: true,
    })
    wrap(<ReviewInbox languageId="lang-ar" />)
    expect(await screen.findByTestId('review-inbox')).toBeDefined()
    expect(screen.queryByTestId('inbox-other-languages')).toBeNull()
  })
})

/* ── 2. a failed fetch must not read as an empty queue ─────────────────── */

describe('review panels say "broken", not "empty", when a fetch fails', () => {
  beforeEach(() => vi.clearAllMocks())

  it('change-request board: an error instead of "No open change requests"', async () => {
    // The board an admin watches for tester reports. Rendering the empty-state
    // copy after a 403/500 is the reported bug in miniature.
    mockRequests.mockRejectedValue(new Error('boom'))
    wrap(<ChangeRequestsPanel languageId="lang-ar" />)

    const row = await screen.findByTestId('change-requests-status')
    expect(row.getAttribute('role')).toBe('alert')
    expect(row.textContent).toMatch(/couldn’t load/i)
    expect(screen.queryByText(/No open change requests/)).toBeNull()
  })

  it('change-request board: the empty-state copy survives a SUCCESSFUL empty load', async () => {
    mockRequests.mockResolvedValue({ requests: [], can_resolve: true, can_vote: true })
    wrap(<ChangeRequestsPanel languageId="lang-ar" />)
    expect(await screen.findByText(/No open change requests/)).toBeDefined()
    expect(screen.queryByTestId('change-requests-status')).toBeNull()
  })

  it('learner feedback: names the reporter and shows the word in its sentences', async () => {
    // Owner: "I need to see the full card if they flagged something … and
    // I would like the user that sent in the request".
    mockFeedback.mockResolvedValue([{
      id: 'f1', card_type: 'vocabulary', content_id: 'v1', card_title: 'cama',
      reporter_email: 'learner@example.com', message: 'Looks wrong',
      status: 'open', created_at: null, target_type: 'vocabulary', target_id: 'v1',
      card: { sentence: 'cama', answer: null, hint: null, translation: 'bed',
              context: 'noun', level: 'A2',
              examples: ['Duermo en la cama. — I sleep in the bed.'] },
    }])
    wrap(<FeedbackPanel languageId="lang-ar" />)
    expect((await screen.findByTestId('feedback-reporter-f1')).textContent).toContain(
      'learner@example.com',
    )
    expect(screen.getByTestId('feedback-card-f1-examples').textContent).toContain(
      'Duermo en la cama.',
    )
  })

  it('learner feedback: an error instead of an absent panel', async () => {
    mockFeedback.mockRejectedValue(new Error('boom'))
    wrap(<FeedbackPanel languageId="lang-ar" />)
    const row = await screen.findByTestId('feedback-panel-status')
    expect(row.getAttribute('role')).toBe('alert')
    expect(row.textContent).toMatch(/Learner feedback/)
  })

  it('tester recommendations: an error outranks the count it failed to load', async () => {
    // The testers' own channel — the one whose silence started this. With a
    // non-zero count the panel has two things it could say; "couldn't load"
    // is the true one, so it has to win.
    mockRecos.mockRejectedValue(new Error('boom'))
    wrap(<TesterRecommendationsPanel languageId="lang-ar" awaiting={2} />)
    await waitFor(() => {
      const row = screen.getByTestId('tester-recommendations-status')
      expect(row.getAttribute('role')).toBe('alert')
      expect(row.textContent).toMatch(/Tester recommendations — couldn’t load/)
    })
  })

  it('AI translations: an error for the admin who can actually open the queue', async () => {
    mockTranslations.mockRejectedValue(new Error('boom'))
    wrap(<TranslationReviewsPanel languageId="lang-ar" awaiting={3} />)
    await waitFor(() => {
      const row = screen.getByTestId('translation-reviews-status')
      expect(row.getAttribute('role')).toBe('alert')
    })
  })

  it('AI translations: still self-hides for a viewer who cannot open it', async () => {
    // Without `awaiting` the viewer is a non-admin whose GET legitimately
    // 403s. Shouting about a queue that was never theirs teaches people to
    // ignore the alert that matters. Both copies share one query, so the
    // admin one appearing proves the failure reached this render — and the
    // non-admin one is the copy that must NOT have shown.
    mockTranslations.mockRejectedValue(new Error('403'))
    wrap(
      <>
        <TranslationReviewsPanel languageId="lang-ar" />
        <TranslationReviewsPanel languageId="lang-ar" awaiting={0} />
      </>,
    )
    await screen.findByTestId('translation-reviews-status')
    expect(screen.getAllByTestId('translation-reviews-status')).toHaveLength(1)
  })

  it('vocab surface: an error instead of an empty-looking language', async () => {
    mockVocab.mockRejectedValue(new Error('boom'))
    wrap(<VocabReviewPanel languageId="lang-ar" languageCode="ar" />)
    const alert = await screen.findByRole('alert')
    expect(alert.textContent).toMatch(/Couldn’t load this language’s vocabulary/)
  })

  it('vocab surface: a 403 says which role is missing, naming testers', async () => {
    // A tester who is told "you don't have a contributor role" stops filing.
    mockVocab.mockRejectedValue({ response: { status: 403 } })
    wrap(<VocabReviewPanel languageId="lang-ar" languageCode="ar" />)
    expect(
      await screen.findByText(/contributor, tester, or reviewer role/i),
    ).toBeDefined()
  })
})
