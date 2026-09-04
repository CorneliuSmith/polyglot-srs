import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import FeedbackQueuePanel from '../features/contribute/FeedbackQueuePanel'

vi.mock('../api/feedback', async (orig) => ({
  ...(await orig<typeof import('../api/feedback')>()),
  getFeedbackQueue: vi.fn(),
  triageFeedback: vi.fn(),
}))

import { getFeedbackQueue } from '../api/feedback'

const mockQueue = getFeedbackQueue as ReturnType<typeof vi.fn>

function renderPanel(props: Record<string, unknown> = {}) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <FeedbackQueuePanel canTriage {...props} />
    </QueryClientProvider>,
  )
}

/**
 * The general-feedback queue, scoped by the same language the rest of the
 * Review workspace is on — the fourth stream joining the map
 * (docs/plans/review-visibility.md C4).
 */
describe('FeedbackQueuePanel — language scope', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockQueue.mockResolvedValue({ feedback: [], open_count: 0 })
  })

  it('defaults to the workspace language when it has one', async () => {
    renderPanel({ languageId: 'lang-he', languageName: 'Hebrew' })
    await waitFor(() =>
      expect(mockQueue).toHaveBeenCalledWith({ languageId: 'lang-he' }),
    )
    expect(screen.getByTestId('feedback-scope-language')).toHaveTextContent(
      'Hebrew',
    )
  })

  it('"not about one language" is a scope of its own, not an absence', async () => {
    // "The app is broken" is not about the course the sender had open —
    // and these were the reports a per-language view silently lost.
    renderPanel({ languageId: 'lang-he', languageName: 'Hebrew' })
    fireEvent.click(await screen.findByTestId('feedback-scope-none'))
    await waitFor(() =>
      expect(mockQueue).toHaveBeenLastCalledWith({ unassigned: true }),
    )
  })

  it('can widen to everything without leaving the panel', async () => {
    renderPanel({ languageId: 'lang-he', languageName: 'Hebrew' })
    fireEvent.click(await screen.findByTestId('feedback-scope-all'))
    await waitFor(() =>
      expect(mockQueue).toHaveBeenLastCalledWith(undefined),
    )
  })

  it('with no workspace language the panel shows everything, chipless', async () => {
    // No page mounts it that way any more (the /feedback page and the
    // Account page's copy went in the 4 Sep 2026 consolidation), but the
    // contract is the panel's own and stays pinned;
    // their behavior must not change underneath them.
    renderPanel()
    await waitFor(() => expect(mockQueue).toHaveBeenCalledWith(undefined))
    expect(screen.queryByTestId('feedback-scope')).toBeNull()
  })
})
