import { Fragment } from 'react'

/**
 * Human-readable typography for grammar explanations (§3b layout standard).
 *
 * Explanations are stored as plain text in short paragraphs. This renderer
 * recognizes the recurring shapes inside them and typesets each one:
 *
 *  - term (gloss) enumerations   → a two-column mini table
 *    "Eu (I), tu (you, informal), el/ea (he/she), …"
 *  - arrow derivations           → a from → to table
 *    "falaram → falar, quiseram → quiser, fizeram → fizer"
 *  - labeled form runs           → label chip + emphasized forms
 *    "-ar: falei, falou, falamos, falaram."
 *  - plain sentences             → paragraph with 'quoted glosses' dimmed
 *
 * Detection is conservative: anything ambiguous falls through to a plain
 * paragraph, so no content is ever lost — only better typeset.
 */

/** Split on commas that sit OUTSIDE parentheses ("tu (you, informal)" stays whole). */
function splitTopLevel(text: string): string[] {
  const parts: string[] = []
  let depth = 0
  let cur = ''
  for (const ch of text) {
    if (ch === '(') depth++
    if (ch === ')') depth = Math.max(0, depth - 1)
    if (ch === ',' && depth === 0) {
      parts.push(cur.trim())
      cur = ''
    } else {
      cur += ch
    }
  }
  if (cur.trim()) parts.push(cur.trim())
  return parts
}

const TERM_GLOSS = /^(.{1,40}?)\s*\(([^()]{1,60})\)\.?$/

interface Parsed {
  kind: 'terms' | 'arrows' | 'forms' | 'text'
  intro?: string
  rows?: string[][]
  label?: string
  body?: string
  note?: string
  /** prose that followed a table inside the same paragraph */
  tail?: string
}

/** First sentence + the rest ("…dumneavoastră. The verb ending…"). */
function splitFirstSentence(p: string): [string, string] {
  // the next sentence may open with a quoted term ('Ni' is …)
  const m = p.match(/^(.+?[.!?])\s+(?=['‘"“]?[A-ZÀ-ÞΑ-ΩА-Я])/su)
  if (!m) return [p, '']
  return [m[1], p.slice(m[0].length)]
}

function parseParagraph(p: string): Parsed {
  // Arrow derivations, optionally after an intro colon:
  // "Build it from the eles-perfeito minus -am: falaram → falar, …"
  if ((p.match(/→/g) ?? []).length >= 2) {
    const firstArrow = p.indexOf('→')
    const colon = p.lastIndexOf(':', firstArrow)
    const intro = colon > 0 ? p.slice(0, colon + 1).trim() : undefined
    const list = colon > 0 ? p.slice(colon + 1) : p
    const rows: string[][] = []
    const leftovers: string[] = []
    for (const seg of splitTopLevel(list.replace(/\.$/, ''))) {
      const m = seg.split('→')
      if (m.length === 2) rows.push([m[0].trim(), m[1].trim()])
      else if (seg.trim()) leftovers.push(seg.trim())
    }
    if (rows.length >= 2) {
      return { kind: 'arrows', intro, rows, note: leftovers.join(', ') || undefined }
    }
  }

  // term (gloss) enumerations: "Eu (I), tu (you, informal), …" — the
  // enumeration is usually one sentence with ordinary prose following in
  // the same paragraph, so parse the first sentence and carry the rest.
  {
    const [first, tail] = splitFirstSentence(p)
    const segs = splitTopLevel(first.replace(/\.$/, ''))
    const rows: string[][] = []
    const leftovers: string[] = []
    for (const seg of segs) {
      const m = seg.match(TERM_GLOSS)
      if (m) rows.push([m[1].trim(), m[2].trim()])
      else if (seg.trim()) leftovers.push(seg.trim())
    }
    // strictly enumeration-shaped: it must LEAD with pairs and be mostly pairs
    if (rows.length >= 3 && segs[0].match(TERM_GLOSS) && leftovers.length <= 1) {
      // "The independent pronouns are mimi (I), …" — the first pair often
      // carries the sentence's intro; peel it off so the table starts at
      // the actual term and the intro renders as text above it.
      let intro: string | undefined
      const firstTermWords = rows[0][0].split(/\s+/)
      if (firstTermWords.length >= 3) {
        intro = firstTermWords.slice(0, -1).join(' ')
        rows[0] = [firstTermWords[firstTermWords.length - 1], rows[0][1]]
      }
      return {
        kind: 'terms',
        intro,
        rows,
        note: leftovers.join(', ') || undefined,
        tail: tail || undefined,
      }
    }
  }

  // labeled form run: "-ar: falei, falou, falamos, falaram."
  {
    const m = p.match(/^([^\s:]{1,14}):\s+(.{2,120})$/s)
    if (m && (m[2].match(/,/g) ?? []).length >= 2 && !m[2].includes('. ')) {
      return { kind: 'forms', label: m[1], body: m[2].replace(/\.$/, '') }
    }
  }

  return { kind: 'text', body: p }
}

/** Dim 'quoted glosses' inside running text (word-internal apostrophes are safe:
 * the opening quote must follow a space/start and the closing must precede a
 * boundary, so l'hôtel and it's never match). */
function renderInline(text: string) {
  const re = /(^|[\s(—])['‘]([^'’]{1,80}?)['’](?=[\s,.;:)!?—]|$)/g
  const out: React.ReactNode[] = []
  let last = 0
  let match: RegExpExecArray | null
  let key = 0
  while ((match = re.exec(text)) !== null) {
    out.push(text.slice(last, match.index) + match[1])
    out.push(
      <span key={key++} className="text-gray-500 italic">
        ‘{match[2]}’
      </span>,
    )
    last = match.index + match[0].length
  }
  out.push(text.slice(last))
  return out
}

export default function ExplanationView({
  text,
  className = 'text-gray-800',
}: {
  text: string
  className?: string
}) {
  const paragraphs = text.split(/\n{2,}|\n/).map((p) => p.trim()).filter(Boolean)
  return (
    <div className={`space-y-2.5 ${className}`} data-testid="explanation">
      {paragraphs.map((p, i) => {
        const parsed = parseParagraph(p)
        if (parsed.kind === 'terms' || parsed.kind === 'arrows') {
          return (
            <Fragment key={i}>
              {parsed.intro && <p>{renderInline(parsed.intro)}</p>}
              <table className="text-sm border border-gray-100 rounded-lg overflow-hidden">
                <tbody>
                  {parsed.rows!.map((row, j) => (
                    <tr key={j} className="odd:bg-gray-50">
                      <td className="px-2.5 py-1 font-medium text-lang-dark whitespace-nowrap">
                        {row[0]}
                      </td>
                      <td className="px-2.5 py-1 text-gray-600">
                        {parsed.kind === 'arrows' ? <>→ {row[1]}</> : row[1]}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {parsed.note && <p className="text-sm text-gray-500">{renderInline(parsed.note)}</p>}
              {parsed.tail && <p>{renderInline(parsed.tail)}</p>}
            </Fragment>
          )
        }
        if (parsed.kind === 'forms') {
          return (
            <p key={i} className="flex items-baseline gap-2">
              <span className="shrink-0 rounded bg-lang-soft px-1.5 py-0.5 text-xs font-semibold text-lang-dark">
                {parsed.label}
              </span>
              <span className="font-medium">{renderInline(parsed.body!)}</span>
            </p>
          )
        }
        return <p key={i}>{renderInline(parsed.body!)}</p>
      })}
    </div>
  )
}
