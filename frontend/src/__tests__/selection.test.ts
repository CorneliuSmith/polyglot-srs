import { describe, it, expect, afterEach } from 'vitest'
import {
  FLAG_REASONS,
  clearSelection,
  issueText,
  selectionWithin,
} from '../features/contribute/selection'

/** Build a detached region and select a substring of its text. */
function selectIn(html: string, from: number, to: number) {
  const host = document.createElement('div')
  host.innerHTML = html
  document.body.appendChild(host)
  const textNode = host.firstChild as Text
  const range = document.createRange()
  range.setStart(textNode, from)
  range.setEnd(textNode, to)
  const sel = window.getSelection()!
  sel.removeAllRanges()
  sel.addRange(range)
  return host
}

afterEach(() => {
  document.body.innerHTML = ''
  window.getSelection()?.removeAllRanges()
})

describe('selectionWithin', () => {
  it('returns the selected span with offsets into the region', () => {
    const host = selectIn('El gato come pescado.', 3, 7)
    const span = selectionWithin(host)
    expect(span?.quote).toBe('gato')
    expect(span?.start).toBe(3)
    expect(span?.end).toBe(7)
    expect(span?.sourceText).toBe('El gato come pescado.')
  })

  it('ignores a collapsed caret', () => {
    const host = selectIn('El gato come pescado.', 4, 4)
    expect(selectionWithin(host)).toBeNull()
  })

  it('ignores a whitespace-only drag', () => {
    // Happens constantly while reading; must never pop a flag dialog.
    const host = selectIn('El gato come pescado.', 2, 3)
    expect(selectionWithin(host)).toBeNull()
  })

  it('ignores a selection outside the region', () => {
    selectIn('Somewhere else entirely', 0, 9)
    const other = document.createElement('div')
    other.textContent = 'El gato'
    document.body.appendChild(other)
    expect(selectionWithin(other)).toBeNull()
  })

  it('returns null for no region at all', () => {
    expect(selectionWithin(null)).toBeNull()
  })

  it('trims surrounding whitespace but keeps offsets aligned to the quote', () => {
    const host = selectIn('El gato come pescado.', 2, 8)
    const span = selectionWithin(host)
    expect(span?.quote).toBe('gato')
    // start points at the 'g', not at the leading space the drag included.
    expect(span?.sourceText.slice(span.start, span.end)).toBe('gato')
  })

  it('clearSelection empties the selection', () => {
    selectIn('El gato', 0, 2)
    clearSelection()
    expect(window.getSelection()?.isCollapsed ?? true).toBe(true)
  })
})

describe('issueText', () => {
  it('a reason chip alone is a complete, readable issue', () => {
    // The whole point of two-tap flagging: no typing required, but the board
    // still gets something meaningful.
    expect(issueText('unnatural', '')).toBe('Grammatical but not idiomatic')
  })

  it('appends the note when the reviewer wrote one', () => {
    expect(issueText('typo', 'missing accent')).toBe(
      'Spelling or punctuation — missing accent',
    )
  })

  it('a note with no chip stands on its own', () => {
    expect(issueText(null, 'the register is far too formal')).toBe(
      'the register is far too formal',
    )
  })

  it('every reason ships an issue string the board can display', () => {
    for (const r of FLAG_REASONS) {
      expect(r.issue.length, r.id).toBeGreaterThan(0)
    }
  })
})
