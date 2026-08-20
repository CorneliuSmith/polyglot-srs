import { useQuery } from '@tanstack/react-query'
import {
  getReviewInbox,
  type ReviewInbox as ReviewInboxData,
  type ReviewInboxCounts,
} from '../../api/contribute'
import {
  ORIGIN_LABELS,
  ORIGIN_ORDER,
  QUEUE_META,
  queueVisible,
  type QueueMeta,
} from '../../lib/reviewTaxonomy'

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
  const viewer = {
    isAdmin: data.is_admin ?? false,
    canPublish: data.can_publish ?? false,
  }
  return QUEUE_META.filter((q) => queueVisible(q, viewer))
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
        /* Grouped by ORIGIN — the owner's own four categories: reports from
           people, general feedback, AI awaiting a human, contributions
           awaiting approval. Fourteen flat tiles answered "how much"; the
           question that kept being asked was "how much of WHAT". */
        <div className="mt-3 space-y-3">
          {ORIGIN_ORDER.map((origin) => {
            const group = active.filter((q) => q.origin === origin)
            if (group.length === 0) return null
            const subtotal = group.reduce(
              (sum, q) => sum + (counts[q.key] ?? 0), 0,
            )
            return (
              <section key={origin} data-testid={`inbox-origin-${origin}`}>
                <p className="flex items-baseline justify-between text-[11px] uppercase tracking-wide text-gray-500">
                  <span>{ORIGIN_LABELS[origin]}</span>
                  <span className="font-semibold tabular-nums">{subtotal}</span>
                </p>
                <ul className="mt-1.5 grid grid-cols-2 gap-2 sm:grid-cols-3">
                  {group.map((q) => (
                    <QueueTile key={q.key} meta={q} count={counts[q.key] ?? 0} />
                  ))}
                </ul>
              </section>
            )
          })}
        </div>
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

function QueueTile({ meta, count }: { meta: QueueMeta; count: number }) {
  const capped = meta.limit != null && count > meta.limit
  return (
    <li className="rounded-lg border border-gray-100 bg-gray-50 px-3 py-2">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-gray-700">{meta.label}</span>
        <span className="rounded-full bg-lang/10 text-lang px-2 py-0.5 text-xs font-semibold">
          {count}
        </span>
      </div>
      {/* WHERE it is acted on, then WHO sees it — the two questions the
          owner asked of every tile. The chip is worth its pixels only when
          the audience is narrower than "everyone reading this inbox". */}
      <span className="mt-0.5 block text-[10px] uppercase tracking-wide text-gray-500">
        {meta.hint}
      </span>
      {meta.audience === 'admin' && (
        <span
          data-testid={`queue-audience-${meta.key}`}
          className="mt-1 inline-block rounded-full border border-gray-200 bg-white px-1.5 py-0.5 text-[10px] font-medium text-gray-500"
        >
          admins only
        </span>
      )}
      {capped && (
        <span className="mt-0.5 block text-[10px] text-amber-600">
          showing first {meta.limit} of {count}
        </span>
      )}
    </li>
  )
}
