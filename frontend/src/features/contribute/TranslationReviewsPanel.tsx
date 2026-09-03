import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  approveTranslationReview,
  approveTranslationReviewItem,
  getTranslationReviews,
  rejectTranslationReview,
  rejectTranslationReviewItem,
  type ReviewedCard,
  type TranslationReviewItemKind,
} from '../../api/contribute'
import QueueStatus from './QueueStatus'

/** The AI maker-checker's "not sure" pile: renderings it refused to
 * auto-apply. Lives in the REVIEW workspace with the other queues (owner:
 * "these should go into the review section, marked as AI generated"),
 * scoped to the working language, each row badged with the review type.
 * An admin approves (applies to the card) or rejects (dismisses).
 *
 * Two sources, one list: word glosses (`translation_reviews`, 'en-hint'
 * rows being flagged English definitions) and, since 3 Sep 2026, every
 * other layer the checker can reject — drill lines and hints, grammar
 * explanations, titles and notes, example-sentence meanings
 * (`translation_review_items`). Until then those were simply not written
 * and waited for the retry backoff where nobody could see them. The rows
 * render grouped by kind so a reviewer can clear one layer at a time. */
import QueueHelp, { QUEUE_HELP } from './QueueHelp'
import ReviewedCardView from './ReviewedCardView'
import { useFocusList } from './useFocusList'

type Kind = 'vocabulary' | TranslationReviewItemKind

/** One row of either source, in the shape the list renders. `id` is unique
 * across both sources (prefixed); `rawId` is what the API wants back. */
interface Row {
  id: string
  rawId: string
  kind: Kind
  /** Which text of the card this is, for the non-gloss kinds. */
  field?: string
  locale: string
  heading: string
  /** The text on the card now: the English definition for a gloss, the
   * English source being rendered for everything else. */
  current: string | null
  currentLabel: string
  proposed: string | null
  reason: string | null
  target_type?: string | null
  target_id?: string | null
  card?: ReviewedCard | null
}

const KIND_ORDER: Kind[] = [
  'vocabulary', 'drill', 'explanation', 'grammar_meta', 'example',
]
const KIND_LABELS: Record<Kind, string> = {
  vocabulary: 'Word glosses',
  drill: 'Drill lines and hints',
  explanation: 'Grammar explanations',
  grammar_meta: 'Grammar titles and notes',
  example: 'Example-sentence meanings',
}
const FIELD_LABELS: Record<string, string> = {
  translation: 'translation',
  hint: 'hint',
  explanation: 'explanation',
  title: 'title',
  culture_note: 'culture note',
  function_note: 'function note',
}

export default function TranslationReviewsPanel({
  languageId,
  awaiting,
  focus = false,
}: {
  languageId?: string
  /** What the Review Inbox counts for this queue, passed ONLY when the
   * viewer can open it (admins). Left undefined the panel keeps its old
   * self-hiding behaviour — reviewers whose GET 403s shouldn't be shown an
   * error about a queue that isn't theirs. */
  awaiting?: number
  /** One at a time with ‹ › instead of the whole list. */
  focus?: boolean
}) {
  const queryClient = useQueryClient()
  const { data, isError } = useQuery({
    queryKey: ['translation-reviews', languageId ?? 'all'],
    queryFn: () => getTranslationReviews(languageId),
    retry: false,
  })
  const refresh = () =>
    queryClient.invalidateQueries({ queryKey: ['translation-reviews'] })
  const approve = useMutation({
    mutationFn: (row: Row) =>
      row.kind === 'vocabulary'
        ? approveTranslationReview(row.rawId)
        : approveTranslationReviewItem(row.rawId),
    onSuccess: refresh,
  })
  const reject = useMutation({
    mutationFn: (row: Row) =>
      row.kind === 'vocabulary'
        ? rejectTranslationReview(row.rawId)
        : rejectTranslationReviewItem(row.rawId),
    onSuccess: refresh,
  })

  const rows: Row[] = [
    ...(data?.reviews ?? []).map<Row>((r) => ({
      id: `review:${r.id}`,
      rawId: r.id,
      kind: 'vocabulary',
      locale: r.locale,
      heading: r.word,
      current: r.current_definition,
      currentLabel: 'now:',
      proposed: r.proposed,
      reason: r.reason,
      target_type: r.target_type,
      target_id: r.target_id,
      card: r.card,
    })),
    ...(data?.items ?? []).map<Row>((i) => ({
      id: `item:${i.id}`,
      rawId: i.id,
      kind: i.kind,
      field: i.field,
      locale: i.locale,
      heading: i.label ?? i.source_text,
      current: i.source_text,
      currentLabel: 'English:',
      proposed: i.proposed,
      reason: i.reason,
      target_type: i.target_type,
      target_id: i.target_id,
      card: i.card,
    })),
  ].sort((a, b) => KIND_ORDER.indexOf(a.kind) - KIND_ORDER.indexOf(b.kind))

  const busy = approve.isPending || reject.isPending
  const { shown, nav } = useFocusList(rows, focus, 'translation', (r) => [
    ...(r.proposed
      ? [{ key: 'a', label: 'Approve', run: () => approve.mutate(r), disabled: busy }]
      : []),
    { key: 'r', label: r.proposed ? 'Reject' : 'Dismiss', run: () => reject.mutate(r),
      disabled: busy },
  ])

  if (!data || rows.length === 0) {
    if (awaiting === undefined) return null
    return (
      <QueueStatus
        title="AI translations"
        isError={isError}
        awaiting={awaiting}
        testId="translation-reviews-status"
      />
    )
  }

  const groups = KIND_ORDER
    .map((kind) => ({ kind, rows: shown.filter((r) => r.kind === kind) }))
    .filter((g) => g.rows.length > 0)

  return (
    <div
      className="bg-white rounded-2xl border border-gray-100 p-4 text-sm"
      data-testid="translation-reviews"
    >
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-sm font-semibold text-gray-800">
          AI translations
          <QueueHelp
            title="AI translations"
            help={QUEUE_HELP['translation-reviews']}
            testId="help-translation-reviews"
          />
        </h2>
        <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-700">
          AI generated · awaiting review
        </span>
      </div>
      <p className="text-xs text-gray-500 mb-3">
        The maker–checker wasn’t confident enough to apply these. Approve
        puts the proposed text on the card. Reject or Dismiss clears the row
        — the card keeps what it shows now, nothing else changes. Rows where
        the checker saw a problem but had no fix offer only Dismiss; each
        one says so, and carries the card so you can correct it here.
      </p>
      {nav}
      {groups.map((g) => (
        <section key={g.kind} data-testid={`translation-kind-${g.kind}`}>
          {/* One heading per layer, so a reviewer can clear "all the drill
              lines" without reading the badge on every row. */}
          <h3 className="mt-2 flex items-baseline justify-between text-[11px] uppercase tracking-wide text-gray-500">
            <span>{KIND_LABELS[g.kind]}</span>
            <span className="font-semibold tabular-nums">{g.rows.length}</span>
          </h3>
          <ul className="divide-y divide-gray-50">
            {g.rows.map((r) => (
              <li key={r.id} className="py-2 flex items-start gap-3">
                <span className="text-[10px] font-mono uppercase rounded bg-gray-100 text-gray-500 px-1.5 py-0.5 mt-0.5">
                  {r.locale}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-gray-800">
                    {r.heading}
                    {r.field && r.kind !== 'explanation' && (
                      <span className="ml-1.5 text-[10px] font-normal uppercase tracking-wide text-gray-400">
                        {FIELD_LABELS[r.field] ?? r.field}
                      </span>
                    )}
                  </div>
                  {/* The decision is current-vs-proposed, so both are shown
                      as a pair. Proposals used to be dropped on the way in
                      (see maker_check_batch) and every row rendered as a
                      reason with a Reject button — a bin, not a review. */}
                  {r.current && (
                    <div className="text-xs text-gray-500">
                      <span className="text-gray-500">{r.currentLabel}</span>{' '}
                      {r.current}
                    </div>
                  )}
                  {r.proposed ? (
                    <div className="text-xs text-gray-700">
                      <span className="text-gray-500">proposed:</span>{' '}
                      <b className="text-gray-900">{r.proposed}</b>
                    </div>
                  ) : (
                    /* Why this row has one button and its neighbour has
                       two. The old copy said what had happened ("rejected
                       it outright") and left the consequence to be
                       inferred from the missing button — the owner read
                       the result as a bug: "on some i only get the option
                       to dismiss and not understand why". Say the
                       consequence first, then the cause, then the way
                       out. */
                    <div
                      className="text-xs text-gray-500 italic"
                      data-testid={`no-proposal-${r.rawId}`}
                    >
                      Nothing to approve: the checker rejected this
                      {r.kind === 'vocabulary' ? ' gloss' : ' rendering'} without
                      offering a replacement, so Dismiss is the only action. If
                      the current text is wrong, edit the card below.
                    </div>
                  )}
                  {r.reason && (
                    <div className="text-[11px] text-amber-700">{r.reason}</div>
                  )}
                  {/* The card itself, and the way to correct it: a row with
                      no proposal is otherwise a dead end that hands the
                      reviewer a problem and no means to fix it. */}
                  {r.card && (
                    <div className="mt-1.5">
                      <ReviewedCardView
                        card={r.card}
                        targetType={r.target_type}
                        targetId={r.target_id}
                        canEdit
                        testId={`translation-card-${r.rawId}`}
                      />
                    </div>
                  )}
                </div>
                <div className="flex gap-1 shrink-0">
                  {/* A row with no proposal used to show a DISABLED Approve
                      next to Reject — which read as "the only thing I can
                      do is reject", with no hint of what rejecting did
                      (owner). There is genuinely one action on such a row,
                      so show one button, named for what it does. */}
                  {r.proposed ? (
                    <>
                      <button
                        type="button"
                        onClick={() => approve.mutate(r)}
                        disabled={busy}
                        title="Put the proposed text on the card"
                        className="rounded-lg bg-lang px-2.5 py-1 text-xs font-semibold text-lang-on disabled:opacity-40"
                      >
                        Approve
                      </button>
                      <button
                        type="button"
                        onClick={() => reject.mutate(r)}
                        disabled={busy}
                        title="Clear this row; the card keeps what it shows now"
                        className="rounded-lg border border-gray-200 px-2.5 py-1 text-xs text-gray-500 hover:text-red-600 disabled:opacity-50"
                      >
                        Reject
                      </button>
                    </>
                  ) : (
                    <button
                      type="button"
                      onClick={() => reject.mutate(r)}
                      disabled={busy}
                      title="Clear this row; the card keeps what it shows now"
                      data-testid={`dismiss-review-${r.rawId}`}
                      className="rounded-lg border border-gray-200 px-2.5 py-1 text-xs text-gray-500 hover:text-red-600 disabled:opacity-50"
                    >
                      Dismiss
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  )
}
