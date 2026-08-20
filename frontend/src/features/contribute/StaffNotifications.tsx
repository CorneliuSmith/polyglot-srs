import { useNavigate } from 'react-router-dom'
import { Inbox, MessageSquareWarning, X } from 'lucide-react'
import { useReviewNotifications } from '../../components/LanguageScopePicker'
import { usePrefsStore } from '../../stores/prefsStore'

/**
 * What is waiting for a reviewer or admin, broken down by language, with
 * every row a way in.
 *
 * Owner: "In the case of reviews as a reviewer or admin there should be
 * some notifications assigned to the language. Same for general feedback
 * for admins."
 *
 * The point is the click count. Finding out whether Hebrew had anything
 * waiting used to mean switching the whole workspace to Hebrew and looking
 * — per language, one at a time, and then switching your study language
 * back. Here every language answers at once, and tapping one opens the
 * workspace already scoped to it.
 *
 * Ordinary learners never see this: the endpoint answers them with an empty
 * set, so nothing renders and no badge appears.
 */
export default function StaffNotifications({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate()
  const setWorkspaceLanguageId = usePrefsStore((s) => s.setWorkspaceLanguageId)
  const { data, isLoading } = useReviewNotifications()

  const languages = (data?.languages ?? []).filter((l) => l.total > 0)
  const feedback = data?.feedback ?? []

  const open = (languageId: string) => {
    // Scope FIRST, then navigate: landing on the workspace and watching it
    // re-scope a frame later is the flash the loading work removed
    // everywhere else.
    setWorkspaceLanguageId(languageId)
    onClose()
    navigate('/contribute')
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/30 p-4 pt-16"
      role="dialog"
      aria-modal="true"
      aria-label="Waiting for review"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-2xl bg-white p-4 shadow-lg"
        onClick={(e) => e.stopPropagation()}
        data-testid="staff-notifications"
      >
        <div className="flex items-start justify-between gap-3">
          <h2 className="font-semibold text-gray-900">Waiting for you</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded-lg p-1 text-gray-400 hover:text-gray-700"
          >
            <X aria-hidden className="h-4 w-4" />
          </button>
        </div>

        {isLoading && <p className="mt-3 text-sm text-gray-500">Loading…</p>}

        {!isLoading && languages.length === 0 && feedback.length === 0 && (
          <p className="mt-3 text-sm text-gray-500" data-testid="staff-all-clear">
            Nothing is waiting on you in any language.
          </p>
        )}

        {languages.length > 0 && (
          <>
            <p className="mt-3 flex items-center gap-1.5 text-xs uppercase tracking-wide text-gray-500">
              <Inbox aria-hidden className="h-3.5 w-3.5" />
              Review queues
            </p>
            <ul className="mt-1.5 space-y-1">
              {languages.map((l) => (
                <li key={l.id}>
                  <button
                    type="button"
                    onClick={() => open(l.id)}
                    data-testid={`staff-lang-${l.code}`}
                    className="flex w-full items-center justify-between gap-3 rounded-lg border border-gray-100 px-3 py-2 text-start hover:border-lang/40 hover:bg-gray-50"
                  >
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-medium text-gray-800">
                        {l.name}
                        {l.is_visible ? '' : ' (hidden)'}
                      </span>
                      {/* The biggest queue by name: "8 waiting" tells you
                          there is work, "8 waiting · generated drills" tells
                          you whether it is yours to do. */}
                      <span className="block text-[11px] text-gray-500">
                        {biggestQueue(l.counts)}
                      </span>
                    </span>
                    <span className="shrink-0 rounded-full bg-lang/10 px-2 py-0.5 text-xs font-semibold text-lang">
                      {l.total}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}

        {/* Admin-only, and the endpoint enforces that — a reviewer is sent
            no feedback rows at all, so there is nothing here to hide. */}
        {feedback.length > 0 && (
          <>
            <p className="mt-4 flex items-center gap-1.5 text-xs uppercase tracking-wide text-gray-500">
              <MessageSquareWarning aria-hidden className="h-3.5 w-3.5" />
              Learner feedback
            </p>
            <ul className="mt-1.5 space-y-1">
              {feedback.map((f) => (
                <li
                  key={f.language_id ?? 'none'}
                  className="flex items-center justify-between gap-3 rounded-lg border border-gray-100 px-3 py-2"
                >
                  <span className="min-w-0 truncate text-sm text-gray-800">
                    {/* Feedback about the app as a whole belongs to no
                        course. Saying so beats filing it under a language
                        the sender never mentioned. */}
                    {f.language_name ?? 'Not about one language'}
                  </span>
                  <span className="shrink-0 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800">
                    {f.count}
                  </span>
                </li>
              ))}
            </ul>
            <button
              type="button"
              onClick={() => {
                onClose()
                navigate('/contribute')
              }}
              className="mt-2 text-xs text-lang hover:underline"
              data-testid="staff-open-feedback"
            >
              Open the feedback queue
            </button>
          </>
        )}
      </div>
    </div>
  )
}

/** Human label for the queue with the most in it. */
const QUEUE_LABELS: Record<string, string> = {
  grammar_pending: 'grammar points',
  pending_drills: 'generated drills',
  flagged_drills: 'flagged drills',
  pending_examples: 'generated examples',
  flagged_examples: 'flagged examples',
  translation_suggestions: 'translation fixes',
  tester_recommendations: 'tester recommendations',
  ai_translations: 'AI translations',
  ai_levels: 'AI vocab levels',
  change_requests: 'change requests',
  suggestions: 'content suggestions',
  notes: 'review notes',
  feedback: 'card feedback',
  overlaps: 'overlapping points',
}

function biggestQueue(counts: Record<string, number>): string {
  const entries = Object.entries(counts).filter(([, n]) => n > 0)
  if (entries.length === 0) return ''
  entries.sort((a, b) => b[1] - a[1])
  const [key, n] = entries[0]
  const label = QUEUE_LABELS[key] ?? key.replace(/_/g, ' ')
  const rest = entries.length - 1
  return `${n} ${label}${rest > 0 ? ` · ${rest} more ${rest === 1 ? 'queue' : 'queues'}` : ''}`
}
