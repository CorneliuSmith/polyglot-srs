import { useQuery } from '@tanstack/react-query'
import {
  getReviewInbox,
  type ReviewInbox as ReviewInboxData,
  type ReviewInboxCounts,
} from '../../api/contribute'

/** Who can actually OPEN the panel behind a tile.
 *  - 'all'     — anyone who can see the inbox at all, which is now
 *                reviewers and admins: testers do not get the roll-up
 *  - 'publish' — full reviewers/admins (`can_publish`)
 *  - 'admin'   — admins only
 * A tile whose panel the viewer can't open is a phantom: they scroll for
 * something that 403'd silently and report the inbox as broken (gap G7). */
type Audience = 'all' | 'publish' | 'admin'

/** Each queue's label, a hint of where it's acted on, who can open that
 * panel, and — where the panel caps its own list — that cap, so a count of
 * 150 against a panel that shows 100 says "showing first 100 of 150"
 * instead of quietly disagreeing with itself. Keys line up with the
 * backend's ReviewInboxCounts, which is generated from one definition
 * shared with the other-languages roll-up. */
const QUEUES: {
  key: keyof ReviewInboxCounts
  label: string
  hint: string
  audience: Audience
  limit?: number
}[] = [
  { key: 'grammar_pending', label: 'Grammar points', hint: 'Contribute · pending review', audience: 'all' },
  { key: 'pending_drills', label: 'Generated drills', hint: 'Generated drills panel', audience: 'all' },
  { key: 'flagged_drills', label: 'Flagged drills', hint: 'Point drills · flagged', audience: 'all' },
  { key: 'pending_examples', label: 'Generated examples', hint: 'Word examples', audience: 'all' },
  { key: 'flagged_examples', label: 'Flagged examples', hint: 'Vocab · needs attention', audience: 'all' },
  { key: 'translation_suggestions', label: 'Translation fixes', hint: 'Vocab · needs attention', audience: 'all' },
  {
    key: 'tester_recommendations',
    label: 'Tester recommendations',
    hint: 'Tester recommendations panel',
    audience: 'all',
    limit: 200,
  },
  // Admin-only: GET /translation-reviews refuses everyone else, so the
  // panel below would render nothing for them.
  { key: 'ai_translations', label: 'AI translations', hint: 'AI generated · awaiting review', audience: 'admin' },
  { key: 'ai_levels', label: 'AI vocab levels', hint: 'AI levels panel', audience: 'all' },
  { key: 'change_requests', label: 'Change requests', hint: 'Change requests board', audience: 'all' },
  { key: 'suggestions', label: 'Content suggestions', hint: 'Suggestions panel', audience: 'publish', limit: 100 },
  { key: 'notes', label: 'Review notes', hint: 'Point review notes', audience: 'publish', limit: 200 },
  { key: 'feedback', label: 'Learner feedback', hint: 'Feedback panel', audience: 'publish', limit: 100 },
  { key: 'overlaps', label: 'Overlapping points', hint: 'Overlaps panel', audience: 'all' },
]

/** The inbox query, shared by key with every panel that wants to know how
 * many items its own queue is supposed to be holding. One fetch, one cache
 * entry — the panels don't each hit the endpoint. */
export function useReviewInbox(
  languageId: string | null | undefined,
  /** Reviewers and admins only — the endpoint refuses everyone else, and
   * asking anyway would put a 403 on every tester's page load. */
  allowed = true,
) {
  return useQuery({
    queryKey: ['review-inbox', languageId],
    queryFn: () => getReviewInbox(languageId!),
    enabled: !!languageId && allowed,
    retry: false,
  })
}

/** How many items the inbox says are waiting in one queue, or undefined if
 * the inbox itself hasn't answered. Panels use it to tell "quiet day" from
 * "the queue endpoint failed" (gap G5). */
export function useQueueCount(
  languageId: string | null | undefined,
  queue: keyof ReviewInboxCounts,
): number | undefined {
  const { data } = useReviewInbox(languageId)
  return data?.counts?.[queue]
}

function visibleQueues(data: ReviewInboxData) {
  const isAdmin = data.is_admin ?? false
  const canPublish = data.can_publish ?? false
  return QUEUES.filter((q) =>
    q.audience === 'admin' ? isAdmin : q.audience === 'publish' ? canPublish : true,
  )
}

/**
 * The unified Review Inbox: one at-a-glance roll-up of everything awaiting
 * review action, sitting above the individual queue panels so a reviewer
 * knows what needs attention before scrolling. Counts only — each tile
 * points to the panel below that acts on it.
 *
 * Reviewers and admins, never testers (owner: "learners and testers should
 * not see review queues"). A tester keeps the panels that ask them a
 * question; the backlog of what the project still owes is not one of them.
 *
 * The strip underneath is the fix for the complaint that started this work
 * ("testers say they're sending reviews and I'm not seeing them"): every
 * queue here is scoped to the working language, but a submission carries
 * the language the TESTER was studying. An admin parked on Arabic saw "All
 * clear" while Hebrew filled up. So the other-languages strip renders
 * whenever anything is waiting elsewhere — most importantly when the
 * current language IS all clear, which is exactly when it used to be
 * invisible.
 */
export default function ReviewInbox({
  languageId,
  onSwitchLanguage,
}: {
  languageId: string
  /** Switches the workspace's working language — the whole page, every
   * panel, re-scopes to it. */
  onSwitchLanguage?: (languageId: string) => void
}) {
  const { data, isLoading } = useReviewInbox(languageId)

  if (isLoading || !data) return null
  const counts = data.counts
  const queues = visibleQueues(data)
  const total = queues.reduce((sum, q) => sum + (counts[q.key] ?? 0), 0)
  const active = queues.filter((q) => (counts[q.key] ?? 0) > 0)
  const elsewhere = data.other_languages ?? []
  const elsewhereTotal = elsewhere.reduce((sum, l) => sum + l.total, 0)

  return (
    <section
      data-testid="review-inbox"
      className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm"
    >
      <div className="flex items-baseline justify-between">
        <h3 className="text-sm font-semibold text-gray-800">Review inbox</h3>
        <span className="text-xs text-gray-500">
          {total === 0 ? 'All clear' : `${total} awaiting`}
        </span>
      </div>
      {total === 0 ? (
        <p className="mt-2 text-xs text-gray-500">
          Nothing is waiting on a reviewer for this language right now.
        </p>
      ) : (
        <ul className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
          {active.map((q) => {
            const n = counts[q.key] ?? 0
            const capped = q.limit != null && n > q.limit
            return (
              <li
                key={q.key}
                className="rounded-lg border border-gray-100 bg-gray-50 px-3 py-2"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-medium text-gray-700">{q.label}</span>
                  <span className="rounded-full bg-lang/10 text-lang px-2 py-0.5 text-xs font-semibold">
                    {n}
                  </span>
                </div>
                <span className="mt-0.5 block text-[10px] uppercase tracking-wide text-gray-500">
                  {q.hint}
                </span>
                {/* The panel below caps its own list; say so rather than
                    let the tile and the panel disagree in silence. */}
                {capped && (
                  <span className="mt-0.5 block text-[10px] text-amber-600">
                    showing first {q.limit} of {n}
                  </span>
                )}
              </li>
            )
          })}
        </ul>
      )}

      {elsewhere.length > 0 && (
        <div
          className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2"
          data-testid="inbox-other-languages"
        >
          <p className="text-xs font-medium text-amber-900">
            {elsewhereTotal} awaiting in{' '}
            {elsewhere.length === 1 ? 'another language' : `${elsewhere.length} other languages`}
          </p>
          <p className="mt-0.5 text-[11px] text-amber-700">
            This page is scoped to one language, but testers file against the
            language they were studying. Switch to see it.
          </p>
          <ul className="mt-1.5 flex flex-wrap gap-1.5">
            {elsewhere.map((l) => (
              <li key={l.id}>
                <button
                  type="button"
                  onClick={() => onSwitchLanguage?.(l.id)}
                  disabled={!onSwitchLanguage}
                  title={`Switch the working language to ${l.name}`}
                  className="rounded-full border border-amber-300 bg-white px-2.5 py-1 text-xs font-medium text-amber-900 hover:bg-amber-100 disabled:cursor-default disabled:hover:bg-white"
                >
                  {l.name}
                  <span className="ms-1.5 rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-800">
                    {l.total}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}
