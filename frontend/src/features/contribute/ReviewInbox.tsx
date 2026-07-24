import { useQuery } from '@tanstack/react-query'
import { getReviewInbox, type ReviewInboxCounts } from '../../api/contribute'

/** Each queue's label and a hint of where it's acted on, in review-priority
 * order. Keys line up with the backend's ReviewInboxCounts. */
const QUEUES: { key: keyof ReviewInboxCounts; label: string; hint: string }[] = [
  { key: 'grammar_pending', label: 'Grammar points', hint: 'Contribute · pending review' },
  { key: 'pending_drills', label: 'Generated drills', hint: 'Generated drills panel' },
  { key: 'pending_examples', label: 'Generated examples', hint: 'Word examples' },
  { key: 'flagged_examples', label: 'Flagged examples', hint: 'Word examples · flagged' },
  { key: 'translation_suggestions', label: 'Translation fixes', hint: 'Word examples · suggested' },
  { key: 'ai_levels', label: 'AI vocab levels', hint: 'AI levels panel' },
  { key: 'change_requests', label: 'Change requests', hint: 'Change requests board' },
  { key: 'suggestions', label: 'Content suggestions', hint: 'Suggestions panel' },
  { key: 'notes', label: 'Review notes', hint: 'Point review notes' },
  { key: 'feedback', label: 'Learner feedback', hint: 'Feedback panel' },
]

/**
 * The unified Review Inbox: one at-a-glance roll-up of everything awaiting
 * review action for a language, sitting above the individual queue panels so a
 * reviewer knows what needs attention before scrolling. Counts only — each tile
 * points to the panel below that acts on it.
 */
export default function ReviewInbox({ languageId }: { languageId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ['review-inbox', languageId],
    queryFn: () => getReviewInbox(languageId),
    enabled: !!languageId,
    retry: false,
  })

  if (isLoading || !data) return null
  const counts = data.counts
  const total = QUEUES.reduce((sum, q) => sum + (counts[q.key] ?? 0), 0)
  const active = QUEUES.filter((q) => (counts[q.key] ?? 0) > 0)

  return (
    <section
      data-testid="review-inbox"
      className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm"
    >
      <div className="flex items-baseline justify-between">
        <h3 className="text-sm font-semibold text-gray-800">Review inbox</h3>
        <span className="text-xs text-gray-400">
          {total === 0 ? 'All clear' : `${total} awaiting`}
        </span>
      </div>
      {total === 0 ? (
        <p className="mt-2 text-xs text-gray-400">
          Nothing is waiting on a reviewer for this language right now.
        </p>
      ) : (
        <ul className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
          {active.map((q) => (
            <li
              key={q.key}
              className="rounded-lg border border-gray-100 bg-gray-50 px-3 py-2"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-medium text-gray-700">{q.label}</span>
                <span className="rounded-full bg-lang/10 text-lang px-2 py-0.5 text-xs font-semibold">
                  {counts[q.key]}
                </span>
              </div>
              <span className="mt-0.5 block text-[10px] uppercase tracking-wide text-gray-400">
                {q.hint}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
