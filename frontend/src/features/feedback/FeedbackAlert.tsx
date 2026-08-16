import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Inbox, X } from 'lucide-react'
import { getFeedbackSummary } from '../../api/feedback'
import { usePrefsStore } from '../../stores/prefsStore'

/**
 * "Something came in while you were away."
 *
 * The triage queue existed but lived three taps down, inside Settings →
 * Admin, and nothing anywhere told staff there was anything in it. A send
 * button whose replies nobody notices is the same as no send button: the
 * reporter waits, hears nothing, and stops reporting.
 *
 * Shown only when there is something NEWER than the last prompt this person
 * dismissed — an open count alone would nag forever about three items already
 * read and decided against. The seen-marker is client-side (see
 * prefsStore.feedbackSeenAt): whether one staff member has looked is a
 * per-person question a dismissed banner already answers, and making it
 * account state would mean a write on every dashboard load.
 */
export default function FeedbackAlert({ canSeeQueue }: { canSeeQueue: boolean }) {
  const navigate = useNavigate()
  const feedbackSeenAt = usePrefsStore((s) => s.feedbackSeenAt)
  const markFeedbackSeen = usePrefsStore((s) => s.markFeedbackSeen)

  const { data } = useQuery({
    queryKey: ['feedback-summary'],
    queryFn: getFeedbackSummary,
    enabled: canSeeQueue,
    // Staff often leave the dashboard open. A quiet refetch keeps the prompt
    // honest without the page having to be reloaded to notice a new report.
    refetchInterval: 5 * 60_000,
    // Never surface a failure here: this is a nicety on someone else's page.
    retry: false,
  })

  if (!canSeeQueue || !data || data.open_count === 0 || !data.latest_at) {
    return null
  }
  // Strictly newer than what was dismissed. Equal means "this exact batch was
  // already shown", which is the common case on a second page load.
  if (feedbackSeenAt && data.latest_at <= feedbackSeenAt) return null

  const count = data.open_count
  return (
    <div
      data-testid="feedback-alert"
      role="status"
      className="bg-lang-soft/70 border border-lang/25 rounded-2xl px-4 py-3 flex items-center gap-3"
    >
      <Inbox aria-hidden className="h-5 w-5 shrink-0 text-lang" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-gray-800">
          {count === 1 ? 'New feedback' : `${count} pieces of feedback waiting`}
        </p>
        <p className="text-xs text-gray-600">
          Someone told you something about the app. Nobody has closed it out
          yet.
        </p>
      </div>
      <button
        type="button"
        onClick={() => {
          markFeedbackSeen(data.latest_at)
          navigate('/feedback')
        }}
        className="bg-lang hover:bg-lang-dark text-lang-on text-sm font-semibold rounded-lg px-3 py-1.5 shrink-0"
      >
        Read it
      </button>
      <button
        type="button"
        aria-label="Dismiss"
        title="Dismiss until something new arrives"
        onClick={() => markFeedbackSeen(data.latest_at)}
        className="text-gray-500 hover:text-gray-600 shrink-0"
        style={{ minWidth: '32px', minHeight: '32px' }}
      >
        <X aria-hidden className="h-4 w-4 mx-auto" />
      </button>
    </div>
  )
}
