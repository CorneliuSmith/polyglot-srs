import { useQuery } from '@tanstack/react-query'
import UiLanguageSwitcher from '../../components/UiLanguageSwitcher'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { getMyRoles } from '../../api/contribute'
import { canContributeWith, canReviewWith } from '../../lib/roleFlags'
import FeedbackQueuePanel from '../contribute/FeedbackQueuePanel'
import { usePrefsStore } from '../../stores/prefsStore'
import { useViewAsKey } from '../../stores/viewAsStore'

/**
 * The triage queue as a page you can reach.
 *
 * It already existed, buried as a panel inside Settings → Admin: three taps
 * from anywhere, and no link to it from the alert that says there is
 * something to read. Same panel, its own address, so the dashboard prompt has
 * somewhere to send you and the URL can be bookmarked or shared with whoever
 * is handling triage this week.
 */
export default function FeedbackPage() {
  const navigate = useNavigate()
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)
  const viewAsKey = useViewAsKey()

  const { data: roleInfo, isLoading } = useQuery({
    queryKey: ['my-roles', viewAsKey],
    queryFn: getMyRoles,
    retry: false,
  })
  const roles = roleInfo?.roles ?? []
  const isAdmin = roles.some((r) => r.role === 'admin')
  // Same rule as the endpoint: any staff role may READ the queue, because the
  // people who can fix a content complaint are contributors, not only admins.
  // Triage (closing an item) stays admin-only, which the panel enforces.
  const canRead =
    isAdmin ||
    canReviewWith(roles, isAdmin, activeLanguageId) ||
    canContributeWith(roles, isAdmin, activeLanguageId) ||
    roles.length > 0

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-6 space-y-4">
        <span className="flex items-center justify-between">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800"
            style={{ minHeight: '44px' }}
          >
            <ArrowLeft aria-hidden className="h-4 w-4" />
            Dashboard
          </button>
          <UiLanguageSwitcher />
        </span>

        {isLoading ? (
          <p className="text-gray-500 text-sm">Loading…</p>
        ) : canRead ? (
          <FeedbackQueuePanel canTriage={isAdmin} />
        ) : (
          <p className="text-gray-600 text-sm">
            Feedback triage is for staff accounts. If you wanted to SEND
            feedback, the button is on the home page.
          </p>
        )}
      </div>
    </div>
  )
}
