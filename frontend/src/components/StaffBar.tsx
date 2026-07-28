import { useQuery } from '@tanstack/react-query'
import { SquarePen } from 'lucide-react'
import { canSuggestForLanguage, getMyRoles } from '../api/contribute'
import { usePrefsStore } from '../stores/prefsStore'
import { useReviewModeStore } from '../stores/reviewModeStore'
import ViewAsBar from './ViewAsBar'

/**
 * The one strip of staff chrome above every authenticated page. Two controls,
 * both persistent and both sticky:
 *
 *   Review Mode — any reviewer / contributor / admin. Turns on click-to-flag
 *                 across cards, tutor replies and readings.
 *   View as     — admins only. Previews the app at each access level.
 *
 * Together in one bar on purpose: separately they'd be two competing strips
 * at the top of a phone screen, and both are "I am here as staff right now"
 * controls. Renders nothing at all for a plain learner.
 */
export default function StaffBar() {
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)
  const reviewMode = useReviewModeStore((s) => s.reviewMode)
  const setReviewMode = useReviewModeStore((s) => s.setReviewMode)

  const { data } = useQuery({
    queryKey: ['my-roles-real'],
    queryFn: getMyRoles,
    retry: false,
    staleTime: 5 * 60 * 1000,
  })

  // Review Mode follows the ACTIVE language: a reviewer for Spanish gets no
  // flag affordance while studying Turkish, because the endpoint would
  // reject the flag anyway.
  const canReview =
    !!data && canSuggestForLanguage(data.roles ?? [], activeLanguageId)

  return (
    <>
      <ViewAsBar />
      {canReview && (
        <div
          data-testid="staff-bar"
          className={
            'sticky top-0 z-30 border-b ' +
            (reviewMode
              ? 'border-amber-300 bg-amber-100 text-amber-900'
              : 'border-gray-200 bg-gray-50 text-gray-600')
          }
        >
          <label className="max-w-3xl mx-auto flex items-center gap-2 px-4 py-1.5 text-xs">
            <SquarePen aria-hidden className="h-3.5 w-3.5 shrink-0" />
            <span className="font-medium">Review mode</span>
            <input
              type="checkbox"
              checked={reviewMode}
              onChange={(e) => setReviewMode(e.target.checked)}
              className="h-4 w-4 accent-amber-600"
            />
            <span className="min-w-0 flex-1 truncate opacity-80">
              {reviewMode
                ? 'Select any text to flag it'
                : 'Flag content as you study'}
            </span>
          </label>
        </div>
      )}
    </>
  )
}
