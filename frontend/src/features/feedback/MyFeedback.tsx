import { useQuery } from '@tanstack/react-query'
import { FEEDBACK_CATEGORIES, getMyFeedback } from '../../api/feedback'

const CATEGORY_LABEL = Object.fromEntries(
  FEEDBACK_CATEGORIES.map((c) => [c.value, c.label]),
) as Record<string, string>

const STATUS_TEXT: Record<string, string> = {
  open: 'Not looked at yet',
  triaged: 'Being worked on',
  closed: 'Dealt with',
}

/**
 * What you've sent, and what came of it.
 *
 * The send form promises this exists — a channel that never shows you your
 * own messages again, let alone whether anyone read them, teaches people to
 * stop bothering. Renders nothing until there is something to show, so it
 * costs a learner who has never sent feedback no space at all.
 */
export default function MyFeedback() {
  const { data: items = [] } = useQuery({
    queryKey: ['my-feedback'],
    queryFn: getMyFeedback,
    retry: false,
    staleTime: 60 * 1000,
  })

  if (items.length === 0) return null

  return (
    <section
      data-testid="my-feedback"
      className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3"
    >
      <div>
        <h2 className="font-semibold text-gray-800">Your feedback</h2>
        <p className="text-xs text-gray-500">
          What you’ve sent us, and where it got to.
        </p>
      </div>
      <ul className="space-y-3">
        {items.map((item) => (
          <li key={item.id} className="border-t border-gray-100 pt-3 first:border-t-0 first:pt-0">
            <div className="flex flex-wrap items-center gap-2 text-[11px] text-gray-400">
              <span className="rounded bg-gray-100 px-1.5 py-0.5 text-gray-600">
                {CATEGORY_LABEL[item.category] ?? item.category}
              </span>
              <span>{new Date(item.created_at).toLocaleDateString()}</span>
              <span>· {STATUS_TEXT[item.status] ?? item.status}</span>
            </div>
            <p className="mt-1 whitespace-pre-wrap text-sm text-gray-700">
              {item.message}
            </p>
            {item.admin_note && (
              <p className="mt-1 rounded-lg bg-lang-soft/60 px-3 py-2 text-xs text-gray-700">
                {item.admin_note}
              </p>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}
