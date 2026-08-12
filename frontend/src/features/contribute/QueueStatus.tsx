/**
 * The visible half of a review queue that has nothing to show.
 *
 * These panels used to return null on BOTH "empty" and "fetch failed"
 * (retry:false, data defaulting to []), so a failing endpoint and a quiet
 * day looked identical — the admin saw a bare Review tab and concluded the
 * testers weren't submitting (gap G5). Two states are now loud:
 *
 *  - the fetch errored → say so, and name the usual cause;
 *  - the fetch succeeded empty while the Review Inbox counts N waiting →
 *    say "N awaiting · none loaded", because that mismatch is a bug
 *    (usually a role gate refusing the list endpoint), not an empty queue.
 *
 * A genuinely empty queue with a zero count still renders nothing.
 */
export default function QueueStatus({
  title,
  isError,
  awaiting,
  testId,
}: {
  /** Queue name, so the row identifies itself with no panel around it. */
  title: string
  isError: boolean
  /** What the Review Inbox says is waiting; undefined if it hasn't answered. */
  awaiting?: number
  testId?: string
}) {
  if (isError) {
    return (
      <div
        role="alert"
        data-testid={testId}
        className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"
      >
        <span className="font-semibold">{title} — couldn’t load.</span>{' '}
        This is an error, not an empty queue. If it persists, check{' '}
        <code>/api/health/schema</code> (a server behind on migrations) and
        that your role can read this queue.
      </div>
    )
  }
  if ((awaiting ?? 0) > 0) {
    return (
      <div
        role="status"
        data-testid={testId}
        className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"
      >
        <span className="font-semibold">
          {title}: {awaiting} awaiting · none loaded.
        </span>{' '}
        The inbox counts {awaiting}, but the list came back empty — most
        often a role gate refusing the list endpoint. Ask an admin to open
        this queue.
      </div>
    )
  }
  return null
}
