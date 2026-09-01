import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  FEEDBACK_CATEGORIES,
  getFeedbackQueue,
  triageFeedback,
  type FeedbackItem,
  type FeedbackStatus,
} from '../../api/feedback'

/**
 * The other half of the feedback channel: somewhere for it to land.
 *
 * A send button with no queue behind it is a suggestion box nailed shut, so
 * this ships with it rather than after it. Staff read; only admins move an
 * item along — same split as the rest of the review surfaces.
 */

const CATEGORY_LABEL = Object.fromEntries(
  FEEDBACK_CATEGORIES.map((c) => [c.value, c.label]),
) as Record<string, string>

const STATUS_STYLE: Record<FeedbackStatus, string> = {
  open: 'bg-amber-50 text-amber-700',
  triaged: 'bg-blue-50 text-blue-700',
  closed: 'bg-gray-100 text-gray-500',
}

function FeedbackRow({
  item,
  canTriage,
  onChanged,
}: {
  item: FeedbackItem
  canTriage: boolean
  onChanged: () => void
}) {
  const [note, setNote] = useState(item.admin_note ?? '')
  const mutation = useMutation({
    mutationFn: (status: FeedbackStatus) => triageFeedback(item.id, status, note),
    onSuccess: onChanged,
  })

  return (
    <li className="border-t border-gray-100 py-3 space-y-2 first:border-t-0">
      <div className="flex flex-wrap items-center gap-2 text-[11px]">
        <span
          className={`rounded px-1.5 py-0.5 uppercase tracking-wide ${STATUS_STYLE[item.status]}`}
        >
          {item.status}
        </span>
        <span className="rounded bg-gray-100 px-1.5 py-0.5 text-gray-600">
          {CATEGORY_LABEL[item.category] ?? item.category}
        </span>
        {item.page && (
          <span className="text-gray-500">on {item.page}</span>
        )}
        {item.language_name && (
          <span className="text-gray-500">· {item.language_name}</span>
        )}
        <span className="text-gray-500">
          · {new Date(item.created_at).toLocaleDateString()}
        </span>
        {item.email && (
          <span className="min-w-0 flex-1 truncate text-end text-gray-500">
            {item.email}
          </span>
        )}
      </div>

      <p className="whitespace-pre-wrap text-sm text-gray-800">{item.message}</p>

      {canTriage ? (
        <div className="flex flex-wrap items-center gap-2">
          <input
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="What was decided? (optional, kept with the item)"
            aria-label={`Note on feedback from ${item.email ?? 'a user'}`}
            className="min-w-0 flex-1 rounded border border-gray-300 px-2 py-1 text-xs"
          />
          {(['triaged', 'closed'] as const).map((next) => (
            <button
              key={next}
              type="button"
              onClick={() => mutation.mutate(next)}
              disabled={mutation.isPending || item.status === next}
              className="rounded border border-gray-300 px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40"
            >
              {next === 'triaged' ? 'Mark triaged' : 'Close'}
            </button>
          ))}
          {item.status !== 'open' && (
            <button
              type="button"
              onClick={() => mutation.mutate('open')}
              disabled={mutation.isPending}
              className="text-xs text-gray-500 hover:underline"
            >
              Reopen
            </button>
          )}
        </div>
      ) : (
        item.admin_note && (
          <p className="text-xs text-gray-500">Note: {item.admin_note}</p>
        )
      )}
    </li>
  )
}

/** The three ways to slice the queue when a workspace language is in
 * scope. "Not about one language" is a real scope, not an absence: the
 * reports about the app as a whole are exactly the ones a per-language
 * view loses, and they used to be findable only by scrolling everything. */
type FeedbackScope = 'language' | 'none' | 'all'

import QueueHelp, { QUEUE_HELP } from './QueueHelp'
import { useFocusList } from './useFocusList'

export default function FeedbackQueuePanel({
  canTriage,
  languageId,
  languageName,
  focus = false,
}: {
  canTriage: boolean
  /** When set (the Review workspace), the panel scopes itself to the same
   * language as every other panel on the page, with scope chips to widen.
   * Absent (the standalone /feedback page, Settings), it shows everything
   * exactly as before. */
  languageId?: string | null
  languageName?: string
  /** One at a time with ‹ › instead of the whole list. */
  focus?: boolean
}) {
  const queryClient = useQueryClient()
  const [showClosed, setShowClosed] = useState(false)
  const [scope, setScope] = useState<FeedbackScope>(
    languageId ? 'language' : 'all',
  )

  const effectiveScope: FeedbackScope = languageId ? scope : 'all'
  const { data, isLoading, isError } = useQuery({
    queryKey: ['feedback-queue', effectiveScope,
               effectiveScope === 'language' ? languageId : null],
    queryFn: () =>
      getFeedbackQueue(
        effectiveScope === 'language'
          ? { languageId }
          : effectiveScope === 'none'
            ? { unassigned: true }
            : undefined,
      ),
    retry: false,
  })

  const refresh = () =>
    queryClient.invalidateQueries({ queryKey: ['feedback-queue'] })

  const all = data?.feedback ?? []
  const items = showClosed ? all : all.filter((f) => f.status !== 'closed')
  const { shown, nav } = useFocusList(items, focus, 'report')

  return (
    <section
      data-testid="feedback-queue"
      className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold text-gray-800">
            Feedback
            <QueueHelp
              title="App feedback"
              help={QUEUE_HELP['feedback-queue']}
              testId="help-feedback-queue"
            />
            {data && data.open_count > 0 && (
              <span className="ms-2 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800">
                {data.open_count} open
              </span>
            )}
          </h2>
          <p className="text-xs text-gray-500">
            Everything sent from the home page — bugs, confusion, content
            problems, ideas.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowClosed((v) => !v)}
          className="shrink-0 text-xs text-lang hover:underline"
        >
          {showClosed ? 'Hide closed' : 'Show closed'}
        </button>
      </div>

      {languageId && (
        <div className="flex flex-wrap gap-2" data-testid="feedback-scope">
          {(
            [
              ['language', languageName ?? 'This language'],
              ['none', 'Not about one language'],
              ['all', 'All'],
            ] as [FeedbackScope, string][]
          ).map(([value, label]) => (
            <button
              key={value}
              type="button"
              onClick={() => setScope(value)}
              aria-pressed={scope === value}
              data-testid={`feedback-scope-${value}`}
              className={
                'rounded-full border px-3 py-1 text-xs font-medium ' +
                (scope === value
                  ? 'border-lang bg-lang text-lang-on'
                  : 'border-gray-300 bg-white text-gray-600 hover:bg-gray-50')
              }
            >
              {label}
            </button>
          ))}
        </div>
      )}

      {isLoading && <p className="text-xs text-gray-500">Loading…</p>}
      {isError && (
        <p className="text-sm text-red-600">Couldn’t load the feedback queue.</p>
      )}
      {!isLoading && !isError && items.length === 0 && (
        <p className="text-sm text-gray-500">
          {all.length === 0
            ? 'Nothing yet.'
            : 'Nothing open — everything has been dealt with.'}
        </p>
      )}

      {nav}
      <ul>
        {shown.map((item) => (
          <FeedbackRow
            key={item.id}
            item={item}
            canTriage={canTriage}
            onChanged={refresh}
          />
        ))}
      </ul>
    </section>
  )
}
