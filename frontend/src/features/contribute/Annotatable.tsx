import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Flag } from 'lucide-react'
import {
  canSuggestForLanguage,
  createChangeRequest,
  getMyRoles,
} from '../../api/contribute'
import { useReviewModeStore } from '../../stores/reviewModeStore'
import {
  FLAG_REASONS,
  clearSelection,
  issueText,
  selectionWithin,
  type FlagReasonId,
  type QuotedSpan,
} from './selection'
import { useViewAsKey } from '../../stores/viewAsStore'

/**
 * Where to hang the popover: just under the selection when the browser can
 * measure it, otherwise null and the popover pins to the bottom of the
 * screen. Range.getBoundingClientRect is absent in jsdom and has historically
 * been patchy on mobile Safari, and a missing rect is a layout detail — it
 * must never cost the reviewer their flag.
 */
function anchorForSelection(): { top: number; left: number } | null {
  try {
    const sel = window.getSelection()
    if (!sel || sel.rangeCount === 0) return null
    const rect = sel.getRangeAt(0).getBoundingClientRect?.()
    if (!rect || (rect.top === 0 && rect.left === 0)) return null
    return { top: rect.bottom + 6, left: Math.max(8, rect.left) }
  } catch {
    return null
  }
}

export type AnnotatableTarget =
  | 'grammar_point'
  | 'drill'
  | 'vocabulary'
  | 'example_sentence'
  | 'tutor_message'
  | 'reading'
  | 'other'

/**
 * Makes any block of text flaggable by staff, in place.
 *
 * The friction this removes (owner: reviewers are volunteers): raising a
 * change request used to mean opening a form, picking a field from a
 * dropdown, and describing in prose which part was wrong. Now a reviewer
 * selects the words and taps a reason — two taps, and the board gets the
 * exact span instead of "the sentence is off".
 *
 * Two ways in, because they suit different moments:
 *   - SELECT a span → popover anchored to it. Precision, for "this clause".
 *   - Tap the flag in the corner → the whole region is the quote. One tap,
 *     and it works where touch selection is awkward.
 *
 * Renders as a plain wrapper for everyone else: learners, and staff with
 * Review Mode off, see no chrome and no behaviour change. The endpoint
 * re-checks the caller's role server-side, so this is only ever an
 * affordance — never the permission itself.
 */
export default function Annotatable({
  languageId,
  targetType,
  targetId = null,
  targetLabel = null,
  field = 'sentence',
  source,
  className,
  children,
}: {
  languageId: string | null
  targetType: AnnotatableTarget
  targetId?: string | null
  targetLabel?: string | null
  field?: string
  /** Free-form note of where this sat, for the board: 'learn', 'tutor'… */
  source: string
  className?: string
  children: React.ReactNode
}) {
  const reviewMode = useReviewModeStore((s) => s.reviewMode)
  const ref = useRef<HTMLDivElement>(null)
  const [span, setSpan] = useState<QuotedSpan | null>(null)
  const [anchor, setAnchor] = useState<{ top: number; left: number } | null>(null)
  const [sent, setSent] = useState(false)

  const { data: rolesData } = useQuery({
    queryKey: ['my-roles', useViewAsKey()],
    queryFn: getMyRoles,
    staleTime: 5 * 60 * 1000,
    enabled: reviewMode,
  })
  const staff =
    reviewMode &&
    !!languageId &&
    !!rolesData &&
    canSuggestForLanguage(rolesData.roles, languageId)

  // Selection is a document-level event: a drag can end outside the element
  // it started in, so listening on the wrapper alone drops selections.
  useEffect(() => {
    if (!staff) return
    const onUp = () => {
      const found = selectionWithin(ref.current)
      if (!found) return
      setSpan(found)
      setAnchor(anchorForSelection())
    }
    document.addEventListener('mouseup', onUp)
    document.addEventListener('touchend', onUp)
    return () => {
      document.removeEventListener('mouseup', onUp)
      document.removeEventListener('touchend', onUp)
    }
  }, [staff])

  const close = () => {
    setSpan(null)
    setAnchor(null)
    clearSelection()
  }

  if (!staff) {
    return <div className={className}>{children}</div>
  }

  return (
    <>
      <div
        ref={ref}
        data-testid="annotatable"
        className={
          (className ?? '') +
          // A dashed rule is the only always-on chrome: enough to say "this
          // is flaggable" without competing with the card itself.
          ' relative rounded-md ring-1 ring-dashed ring-amber-300/70'
        }
      >
        {children}
        <button
          type="button"
          aria-label="Flag this text for review"
          onClick={() => {
            // No selection: the learner is flagging the whole item, not a
            // span. Quoting the entire region back was actively unhelpful —
            // textContent has no separators, so a card came out as
            // "…subject–object–verbHow it worksHindi sentences…". The
            // target's own label is what the board should show instead.
            setSpan({ quote: '', start: 0, end: 0, sourceText: '' })
            setAnchor(null)
          }}
          className="absolute -top-2 -end-2 rounded-full bg-amber-500 p-1 text-white shadow hover:bg-amber-600"
        >
          <Flag aria-hidden className="h-3 w-3" />
        </button>
      </div>
      {sent && (
        <p className="mt-1 text-center text-xs text-gray-500" role="status">
          ✓ Sent to the review board
        </p>
      )}
      {span && (
        <FlagPopover
          span={span}
          anchor={anchor}
          languageId={languageId!}
          targetType={targetType}
          targetId={targetId}
          targetLabel={targetLabel}
          field={field}
          source={source}
          onDone={() => {
            setSent(true)
            close()
          }}
          onCancel={close}
        />
      )}
    </>
  )
}

/** The two-tap flag: pick a reason, or open a note for something specific. */
function FlagPopover({
  span,
  anchor,
  languageId,
  targetType,
  targetId,
  targetLabel,
  field,
  source,
  onDone,
  onCancel,
}: {
  span: QuotedSpan
  anchor: { top: number; left: number } | null
  languageId: string
  targetType: AnnotatableTarget
  targetId: string | null
  targetLabel: string | null
  field: string
  source: string
  onDone: () => void
  onCancel: () => void
}) {
  const [note, setNote] = useState('')
  const [fix, setFix] = useState('')
  const [expanded, setExpanded] = useState(false)

  const send = useMutation({
    mutationFn: (reason: FlagReasonId | null) =>
      createChangeRequest({
        language_id: languageId,
        target_type: targetType,
        target_id: targetId,
        target_label: targetLabel,
        field,
        issue: issueText(reason, note) || 'Flagged in review mode',
        suggestion: fix.trim() || null,
        // Empty quote = the whole item was flagged, not a span. The board
        // falls back to target_label, which is already a clean one-liner.
        quote: span.quote || null,
        quote_context: {
          source,
          whole: !span.quote,
          ...(span.quote
            ? { start: span.start, end: span.end, source_text: span.sourceText }
            : {}),
        },
      }),
    onSuccess: onDone,
  })

  return (
    <div
      role="dialog"
      aria-label="Flag this text"
      data-testid="flag-popover"
      className="fixed z-50 w-[min(20rem,calc(100vw-1rem))] rounded-xl border border-gray-200 bg-white p-3 shadow-xl"
      style={
        anchor
          ? { top: anchor.top, left: anchor.left }
          : { bottom: 16, left: '50%', transform: 'translateX(-50%)' }
      }
    >
      <p className="mb-2 line-clamp-2 rounded bg-amber-50 px-2 py-1 text-xs text-gray-700">
        {span.quote
          ? `“${span.quote}”`
          : targetLabel
            ? `This whole item — “${targetLabel}”`
            : 'This whole item'}
      </p>
      <div className="flex flex-wrap gap-1.5">
        {FLAG_REASONS.map((r) => (
          <button
            key={r.id}
            type="button"
            onClick={() => send.mutate(r.id)}
            disabled={send.isPending}
            className="rounded-full border border-gray-300 px-2.5 py-1 text-xs font-medium text-gray-700 hover:border-lang hover:bg-lang-soft disabled:opacity-50"
          >
            {r.label}
          </button>
        ))}
      </div>
      {expanded ? (
        <div className="mt-2 space-y-2">
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="What's wrong?"
            rows={2}
            maxLength={2000}
            aria-label="What's wrong?"
            className="w-full rounded-lg border border-gray-200 px-2 py-1.5 text-sm"
          />
          <textarea
            value={fix}
            onChange={(e) => setFix(e.target.value)}
            placeholder="Suggested fix (optional)"
            rows={2}
            maxLength={2000}
            aria-label="Suggested fix"
            className="w-full rounded-lg border border-gray-200 px-2 py-1.5 text-sm"
          />
          <button
            type="button"
            onClick={() => send.mutate(null)}
            disabled={!note.trim() || send.isPending}
            className="w-full rounded-lg bg-lang px-3 py-1.5 text-xs font-semibold text-lang-on hover:bg-lang-dark disabled:opacity-40"
          >
            {send.isPending ? 'Sending…' : 'Send to review board'}
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setExpanded(true)}
          className="mt-2 text-xs text-gray-500 hover:text-lang"
        >
          Add a note or a fix…
        </button>
      )}
      {send.isError && (
        <p className="mt-1 text-xs text-red-600" role="alert">
          Couldn&apos;t send — try again.
        </p>
      )}
      <button
        type="button"
        onClick={onCancel}
        className="mt-2 block w-full text-center text-xs text-gray-500 hover:text-gray-600"
      >
        Cancel
      </button>
    </div>
  )
}
