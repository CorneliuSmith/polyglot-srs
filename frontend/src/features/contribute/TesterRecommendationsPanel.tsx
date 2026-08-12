import { useQuery } from '@tanstack/react-query'
import {
  getTesterRecommendations,
  type TesterRecommendation,
} from '../../api/contribute'
import LanguageWrapper from '../../components/LanguageWrapper'
import QueueStatus from './QueueStatus'

/**
 * What the testers actually said — the advisory approve/reject calls they
 * left on items still awaiting review, with the note they wrote as visible
 * text.
 *
 * This channel had no durable surface (gap G4). A tester's written reason
 * existed only as a `title` tooltip on a pending row, on a panel the admin
 * had to already be looking at; then "Approve all" deleted the row and the
 * note with it. Weeks of tester answers could leave no trace, which is how
 * "they say they're sending reviews" and "the reviews always seem lacking"
 * end up being the same bug.
 *
 * Rejections sort first: a "needs work" with an explanation is the item a
 * reviewer should read before publishing anything.
 */
export default function TesterRecommendationsPanel({
  languageId,
  languageCode,
  awaiting,
}: {
  languageId: string
  languageCode?: string
  /** What the Review Inbox counts for this queue (see QueueStatus). */
  awaiting?: number
}) {
  const { data, isError } = useQuery({
    queryKey: ['tester-recommendations', languageId],
    queryFn: () => getTesterRecommendations(languageId),
    enabled: !!languageId,
    retry: false,
  })

  const items = data?.recommendations ?? []
  if (items.length === 0)
    return (
      <QueueStatus
        title="Tester recommendations"
        isError={isError}
        awaiting={awaiting}
        testId="tester-recommendations-status"
      />
    )

  const limit = data?.limit ?? items.length
  // The endpoint clamps; say so rather than let this list quietly disagree
  // with the inbox tile above it.
  const capped = (awaiting ?? 0) > items.length && items.length >= limit

  return (
    <div
      className="rounded-2xl border border-gray-100 bg-white p-4 text-sm space-y-2"
      data-testid="tester-recommendations"
    >
      <div className="flex items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold text-gray-800">
          Tester recommendations
        </h2>
        <span className="text-xs text-gray-400">
          {capped
            ? `showing first ${items.length} of ${awaiting}`
            : `${items.length} on items still pending`}
        </span>
      </div>
      <p className="text-xs text-gray-500">
        Advisory only — testers can’t publish. Read these before approving the
        item they’re about: approving deletes the pending row, and this note
        with it.
      </p>
      <ul className="space-y-1.5">
        {items.map((r: TesterRecommendation) => (
          <li
            key={r.id}
            className="rounded-lg border border-gray-100 px-2.5 py-1.5"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                {r.context && (
                  <div className="text-[11px] uppercase tracking-wide text-gray-400">
                    {r.target_type === 'drill' ? 'Drill' : 'Example'} · {r.context}
                  </div>
                )}
                {r.target_label && (
                  <LanguageWrapper languageCode={languageCode ?? 'en'}>
                    <div className="text-sm text-gray-800">{r.target_label}</div>
                  </LanguageWrapper>
                )}
                {r.target_translation && (
                  <div className="text-[11px] text-gray-400">
                    {r.target_translation}
                  </div>
                )}
              </div>
              <span
                className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                  r.recommendation === 'reject'
                    ? 'bg-red-50 text-red-700'
                    : 'bg-green-50 text-green-700'
                }`}
              >
                {r.recommendation === 'reject' ? 'needs work' : 'looks good'}
              </span>
            </div>
            {/* The note is the whole point of the channel: visible text, not
                a tooltip nobody hovers. */}
            {r.note && (
              <p className="mt-1 whitespace-pre-wrap rounded bg-gray-50 px-2 py-1 text-xs text-gray-700">
                {r.note}
              </p>
            )}
            <p className="mt-0.5 text-[11px] text-gray-400">
              {r.recommender_email ?? 'a tester'}
            </p>
          </li>
        ))}
      </ul>
    </div>
  )
}
