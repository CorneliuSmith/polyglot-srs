/**
 * Turning a browser text selection into something a reviewer's colleague can
 * act on. Pure helpers, kept out of the component so the fiddly offset maths
 * is testable without a DOM harness around it.
 */

export interface QuotedSpan {
  /** Exactly what was selected. */
  quote: string
  /** Character offsets into the region's full text. */
  start: number
  end: number
  /** The whole region, so the board can show the quote in context. */
  sourceText: string
}

/** Selections shorter than this are almost always a stray tap, not a claim
 *  about the text. */
const MIN_QUOTE_CHARS = 1
/** The column is capped at 2000; trim well before that so a runaway
 *  select-all still produces a usable record instead of a 422. */
const MAX_QUOTE_CHARS = 2000

/**
 * The current selection, if it lies inside *container*, expressed as offsets
 * into that container's text.
 *
 * Returns null for a collapsed caret, a selection that starts or ends outside
 * the region, or whitespace only — all of which happen constantly during
 * ordinary reading and must not pop a flag dialog.
 */
export function selectionWithin(container: HTMLElement | null): QuotedSpan | null {
  if (!container) return null
  const selection = window.getSelection()
  if (!selection || selection.isCollapsed || selection.rangeCount === 0) return null

  const range = selection.getRangeAt(0)
  // Both ends must be ours. A drag that starts in the sentence and ends in
  // the translation below belongs to neither region cleanly.
  if (
    !container.contains(range.startContainer) ||
    !container.contains(range.endContainer)
  ) {
    return null
  }

  const quote = range.toString().trim()
  if (quote.length < MIN_QUOTE_CHARS) return null

  const sourceText = container.textContent ?? ''
  // Offset = length of everything from the region's start up to the
  // selection's start.
  const prefix = range.cloneRange()
  prefix.selectNodeContents(container)
  prefix.setEnd(range.startContainer, range.startOffset)
  const rawStart = prefix.toString().length
  // toString() above is untrimmed; realign to where the trimmed quote
  // actually begins so start/end bracket the quote we send.
  const lead = range.toString().length - range.toString().trimStart().length
  const start = rawStart + lead

  return {
    quote: quote.slice(0, MAX_QUOTE_CHARS),
    start,
    end: start + Math.min(quote.length, MAX_QUOTE_CHARS),
    sourceText: sourceText.slice(0, MAX_QUOTE_CHARS),
  }
}

/** Clear the selection after acting on it, so the popover doesn't reopen on
 *  the next tap and the highlight doesn't linger over stale text. */
export function clearSelection(): void {
  window.getSelection()?.removeAllRanges()
}

/**
 * One-tap reasons. A dropdown of six fields plus a prose box was the old
 * friction; these cover what reviewers actually report, and tapping one IS
 * the submit — a note is optional on top.
 */
export const FLAG_REASONS = [
  { id: 'wrong', label: 'Wrong', issue: 'Incorrect' },
  { id: 'unnatural', label: 'Unnatural', issue: 'Grammatical but not idiomatic' },
  { id: 'typo', label: 'Typo', issue: 'Spelling or punctuation' },
  { id: 'translation', label: 'Translation', issue: "Translation doesn't match" },
  { id: 'level', label: 'Wrong level', issue: 'Too hard or too easy for this level' },
] as const

export type FlagReasonId = (typeof FLAG_REASONS)[number]['id']

/** The `issue` text a reason chip sends, with the reviewer's note appended
 *  when they wrote one. Keeps the board readable whichever path was used. */
export function issueText(reasonId: FlagReasonId | null, note: string): string {
  const reason = FLAG_REASONS.find((r) => r.id === reasonId)
  const trimmed = note.trim()
  if (!reason) return trimmed
  return trimmed ? `${reason.issue} — ${trimmed}` : reason.issue
}
