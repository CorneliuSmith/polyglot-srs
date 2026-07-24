import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  answerReviewPrompt,
  getReviewPrompt,
  type ReviewPrompt,
} from '../../api/contribute'
import LanguageWrapper from '../../components/LanguageWrapper'
import { getLanguages } from '../../api/profile'

/**
 * A blocking, occasionally-shown nudge that puts a trial reviewer to work: it
 * fetches one real pending item (a generated drill or example) and asks them to
 * judge it before they use the dashboard. Approve/Reject records an advisory
 * recommendation; "Can't tell" satisfies the nudge without a vote. It cannot be
 * dismissed except by answering — that's the point — and it only ever appears
 * for trial reviewers, at most once a day (the server rate-limits it).
 */
export default function ReviewPromptGate() {
  const { data } = useQuery({
    queryKey: ['review-prompt'],
    queryFn: getReviewPrompt,
    retry: false,
    staleTime: Infinity, // one check per dashboard mount
  })
  if (!data?.due || !data.prompt) return null
  return <PromptModal prompt={data.prompt} />
}

/** "in about 3 days" / "later today" from an ISO timestamp. */
function untilPhrase(iso: string): string {
  const ms = new Date(iso).getTime() - Date.now()
  if (!Number.isFinite(ms) || ms <= 0) return 'soon'
  const days = Math.round(ms / 86_400_000)
  if (days >= 1) return `in about ${days} day${days === 1 ? '' : 's'}`
  const hours = Math.max(1, Math.round(ms / 3_600_000))
  return `in about ${hours} hour${hours === 1 ? '' : 's'}`
}

function PromptModal({ prompt }: { prompt: ReviewPrompt }) {
  const qc = useQueryClient()
  const [note, setNote] = useState('')
  const [done, setDone] = useState<{ next: string; voted: boolean } | null>(null)
  const { data: languages = [] } = useQuery({
    queryKey: ['languages'],
    queryFn: getLanguages,
  })
  const languageCode =
    languages.find((l) => l.id === prompt.language_id)?.code ?? 'en'

  const answer = useMutation({
    mutationFn: (recommendation: 'approve' | 'reject' | 'skip') =>
      answerReviewPrompt({
        targetType: prompt.target_type,
        targetId: prompt.target_id,
        languageId: prompt.language_id,
        recommendation,
        note: note.trim(),
      }).then((res) => ({ res, recommendation })),
    onSuccess: ({ res, recommendation }) =>
      setDone({ next: res.next_prompt_at, voted: recommendation !== 'skip' }),
  })

  // Fill the {{answer}} blank so the reviewer reads the whole drill.
  const shown = prompt.target_type === 'drill' && prompt.answer
    ? prompt.sentence.replace('{{answer}}', `【${prompt.answer}】`)
    : prompt.sentence

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
      role="dialog"
      aria-modal="true"
      aria-label="Reviewer check-in"
      data-testid="review-prompt-gate"
    >
      <div className="w-full max-w-md rounded-2xl bg-white p-5 shadow-xl space-y-3">
        {done ? (
          <div className="space-y-3 text-center">
            <p className="text-sm font-semibold text-gray-800">
              {done.voted ? 'Thanks — that helps.' : 'No problem.'}
            </p>
            <p className="text-xs text-gray-500">
              {done.voted
                ? 'Your call goes to the reviewers weighing this card. '
                : "We'll pick a different card next time. "}
              We'll check back <b>{untilPhrase(done.next)}</b>
              {done.voted ? ' — the more you help, the less often we ask.' : '.'}
            </p>
            <button
              type="button"
              onClick={() => qc.setQueryData(['review-prompt'], { due: false })}
              className="rounded-lg bg-lang text-lang-on px-4 py-2 text-sm font-semibold hover:bg-lang-dark"
            >
              Continue to dashboard
            </button>
          </div>
        ) : (
          <>
            <div>
              <p className="text-xs uppercase tracking-wide text-lang font-semibold">
                Quick reviewer check-in
              </p>
              <p className="mt-0.5 text-sm text-gray-700">{prompt.question}</p>
              <p className="mt-0.5 text-[11px] text-gray-400">
                One card before you dive in. The more you help, the less often
                we'll ask.
              </p>
            </div>

            <div className="rounded-xl border border-gray-100 bg-gray-50 px-3 py-2.5">
              <div className="text-[11px] uppercase tracking-wide text-gray-400">
                {prompt.target_type === 'drill' ? 'Drill' : 'Example'} ·{' '}
                {prompt.context}
              </div>
              <LanguageWrapper languageCode={languageCode}>
                <p className="mt-1 text-sm text-gray-900">{shown}</p>
              </LanguageWrapper>
              {prompt.translation && (
                <p className="mt-0.5 text-xs text-gray-500">{prompt.translation}</p>
              )}
            </div>

            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={2}
              placeholder="Optional: what's off, or why it's good"
              aria-label="Note"
              className="w-full rounded-lg border border-gray-200 px-2.5 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-lang"
            />

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => answer.mutate('approve')}
                disabled={answer.isPending}
                className="flex-1 rounded-lg bg-green-600 text-white px-3 py-2 text-sm font-semibold hover:bg-green-700 disabled:opacity-50"
              >
                Looks good
              </button>
              <button
                type="button"
                onClick={() => answer.mutate('reject')}
                disabled={answer.isPending}
                className="flex-1 rounded-lg border border-red-300 text-red-700 px-3 py-2 text-sm font-semibold hover:bg-red-50 disabled:opacity-50"
              >
                Needs work
              </button>
            </div>
            <button
              type="button"
              onClick={() => answer.mutate('skip')}
              disabled={answer.isPending}
              className="w-full text-center text-xs text-gray-400 hover:text-gray-600 disabled:opacity-50"
            >
              I can't tell — skip this one
            </button>
            {answer.isError && (
              <p className="text-xs text-red-500 text-center">
                Couldn't save that — try again.
              </p>
            )}
          </>
        )}
      </div>
    </div>
  )
}
