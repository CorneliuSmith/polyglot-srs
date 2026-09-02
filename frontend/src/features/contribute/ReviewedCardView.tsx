import { useEffect, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { editReviewedCard, type ReviewedCard } from '../../api/contribute'

/**
 * The card a review queue row is about — shown in full, and fixable in
 * place.
 *
 * Two owner reports, one component. First: a board carrying a bare label
 * and a complaint cannot be judged ("it is hard to decide when you don't
 * see the full card") — whether a hint gives the answer away is a question
 * about the hint AND the sentence AND the answer. Second: seeing it is only
 * half the job ("I need to be able to view and EDIT the cards referenced
 * easily to actually decide if the student is right or wrong"), because the
 * usual verdict on a learner report is "yes, and here is the correction" —
 * and that used to mean leaving the queue, finding the same card by search
 * in the content editor, and coming back to a complaint you had to
 * remember.
 *
 * The FIELD a request names is highlighted, because the next question after
 * "what is this card" is always "which part of it".
 */

/** What each kind lets a reviewer change, and what the box is called there.
 *  Mirrors CARD_EDIT_FIELDS on the server — the server is the authority and
 *  rejects anything else, this decides what to draw. */
const EDITABLE: Record<string, Partial<Record<CardField, string>>> = {
  drill: {
    sentence: 'Sentence',
    answer: 'Answer',
    hint: 'Hint',
    translation: 'Translation',
  },
  example_sentence: { sentence: 'Sentence', translation: 'Translation' },
  // A word's own text is not editable: every user card, clip and example
  // points at that row, so renaming it in place would re-target all of
  // them silently. The reading and the English definition are the card.
  vocabulary: { hint: 'Reading', translation: 'Definition (English)' },
  grammar_point: { sentence: 'Title', translation: 'Explanation' },
}

type CardField = 'sentence' | 'answer' | 'hint' | 'translation'

const ROWS: [CardField, string][] = [
  ['sentence', 'Sentence'],
  ['answer', 'Answer'],
  ['hint', 'Hint'],
  ['translation', 'Translation'],
]

export default function ReviewedCardView({
  card,
  field,
  targetType,
  targetId,
  canEdit = false,
  onSaved,
  testId = 'reviewed-card',
}: {
  card: ReviewedCard
  /** The field the complaint names, highlighted. */
  field?: string
  targetType?: string | null
  targetId?: string | null
  /** Whether to offer the editor at all — the caller knows the viewer's role. */
  canEdit?: boolean
  /** Called after a successful save, to refetch the queue behind it. */
  onSaved?: () => void
  testId?: string
}) {
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState<Record<string, string>>({})
  const boxes = (targetType && EDITABLE[targetType]) || null
  const editable = canEdit && !!boxes && !!targetId

  // A queue that refetches under the editor (a poll, a sibling resolve)
  // must not overwrite half-typed text, so the draft is seeded once per
  // opening rather than tracking the card.
  useEffect(() => {
    if (!editing || !boxes) return
    setDraft(
      Object.fromEntries(
        (Object.keys(boxes) as CardField[]).map((f) => [f, card[f] ?? '']),
      ),
    )
  }, [editing]) // eslint-disable-line react-hooks/exhaustive-deps

  const save = useMutation({
    mutationFn: () =>
      editReviewedCard(targetType as string, targetId as string, draft),
    onSuccess: () => {
      setEditing(false)
      // Every queue shows some slice of the same content, so a correction
      // made in one has to land in the others too.
      queryClient.invalidateQueries({ queryKey: ['change-requests'] })
      queryClient.invalidateQueries({ queryKey: ['feedback'] })
      queryClient.invalidateQueries({ queryKey: ['translation-reviews'] })
      onSaved?.()
    },
  })

  if (editing && boxes) {
    return (
      <div
        className="rounded-lg border border-lang bg-white px-2.5 py-2 space-y-2"
        data-testid={`${testId}-editor`}
      >
        {(Object.entries(boxes) as [CardField, string][]).map(([key, label]) => (
          <label key={key} className="block">
            <span className="text-[11px] uppercase tracking-wide text-gray-500">
              {label}
            </span>
            <textarea
              value={draft[key] ?? ''}
              onChange={(e) =>
                setDraft((d) => ({ ...d, [key]: e.target.value }))
              }
              rows={key === 'translation' && targetType === 'grammar_point' ? 5 : 2}
              aria-label={label}
              className="mt-0.5 w-full rounded border border-gray-300 px-2 py-1 text-sm"
            />
          </label>
        ))}
        {/* The blank is part of a drill's text, and deleting it breaks the
            card in a way that is invisible until a learner meets it. */}
        {targetType === 'drill' && !(draft.sentence ?? '').includes('{{answer}}') && (
          <p className="text-[11px] text-amber-700" data-testid="drill-blank-warning">
            The sentence no longer contains {'{{answer}}'} — the drill will
            show no blank to fill in.
          </p>
        )}
        {save.isError && (
          <p className="text-[11px] text-red-600">
            Couldn’t save that — you may not have a contributor role for this
            language, or the card has been deleted.
          </p>
        )}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => save.mutate()}
            disabled={save.isPending}
            data-testid={`${testId}-save`}
            className="rounded-lg bg-lang px-2.5 py-1 text-xs font-semibold text-lang-on disabled:opacity-40"
          >
            {save.isPending ? 'Saving…' : 'Save card'}
          </button>
          <button
            type="button"
            onClick={() => setEditing(false)}
            className="text-xs text-gray-500 hover:underline"
          >
            Cancel
          </button>
          <span className="text-[11px] text-gray-400">
            Saved edits are logged and can be rolled back.
          </span>
        </div>
      </div>
    )
  }

  return (
    <div
      className="rounded-lg border border-gray-200 bg-gray-50 px-2.5 py-2"
      data-testid={testId}
    >
      <div className="flex items-start justify-between gap-2">
        {(card.context || card.level) && (
          <p className="mb-1 text-[10px] uppercase tracking-wide text-gray-500">
            {card.context}
            {card.context && card.level && ' · '}
            {card.level}
          </p>
        )}
        {editable && (
          <button
            type="button"
            onClick={() => setEditing(true)}
            data-testid={`${testId}-edit`}
            className="ms-auto shrink-0 text-xs font-semibold text-lang hover:underline"
          >
            Edit card
          </button>
        )}
      </div>
      <dl className="space-y-0.5">
        {ROWS.map(([key, label]) =>
          card[key] ? (
            <div
              key={key}
              className={`flex gap-2 rounded px-1 text-sm ${
                key === field ? 'bg-amber-100' : ''
              }`}
            >
              <dt className="w-20 shrink-0 text-[11px] uppercase tracking-wide text-gray-500">
                {label}
              </dt>
              <dd className="min-w-0 flex-1 text-gray-800">
                {/* The blank is what the learner sees; filling it in is the
                    only way to tell whether the hint gives it away. */}
                {key === 'sentence' && card.answer
                  ? (card[key] as string).replace('{{answer}}', `【${card.answer}】`)
                  : card[key]}
              </dd>
            </div>
          ) : null,
        )}
      </dl>
    </div>
  )
}
