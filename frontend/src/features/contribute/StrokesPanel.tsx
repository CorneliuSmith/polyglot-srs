import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Trash2 } from 'lucide-react'
import {
  deleteExemplar,
  deleteGlyph,
  getAlphabet,
  listStrokes,
  reviewExemplar,
  reviewGlyph,
  saveExemplar,
  saveGlyph,
} from '../../api/strokes'
import type { Exemplar, Glyph } from '../../api/strokes'
import InkCanvas from '../write/InkCanvas'
import StrokePreview from '../write/StrokePreview'
import { fromGlyphBox, toGlyphBox } from '../write/glyphBox'
import { handFontFor } from '../write/handFont'
import type { Stroke } from '../write/ink'

/** Arabic positional forms are shaped by the font when a joiner sits on
 * the joining side — no presentation-form tables (the Letters page's
 * trick). */
const ZWJ = '‍'
function shaped(script: string, glyph: string, form: string): string {
  if (script !== 'arabic') return glyph
  if (form === 'initial') return glyph + ZWJ
  if (form === 'medial') return ZWJ + glyph + ZWJ
  if (form === 'final') return ZWJ + glyph
  return glyph
}
function cased(glyph: string, form: string): string {
  return form === 'upper' ? glyph.toUpperCase() : glyph
}

/**
 * The Strokes panel (docs/plans/handwriting.md, §5): a speaker traces how
 * each letter form is written — over a faint font glyph, in order, with a
 * hint per stroke — and a reviewer signs it off. The grid shows what is
 * authored and what is reviewed; a form is live for learners only once
 * reviewed. Exemplar sentences, written whole in one flow, are authored
 * below the grid.
 *
 * Workspace panels are not translated (DEBT.md) — English throughout.
 */
export default function StrokesPanel({
  languageId,
  languageCode,
  canReview,
}: {
  languageId: string
  languageCode: string | undefined
  canReview: boolean
}) {
  const queryClient = useQueryClient()
  const { data: alphabet } = useQuery({
    queryKey: ['write-alphabet', languageId],
    queryFn: () => getAlphabet(languageId),
    retry: false,
  })
  const [style, setStyle] = useState<string | null>(null)
  const activeStyle = style ?? alphabet?.styles[0] ?? 'print'
  const { data: library, isError } = useQuery({
    queryKey: ['strokes', languageId, activeStyle],
    queryFn: () => listStrokes(languageId, activeStyle),
    retry: false,
  })
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['strokes', languageId] })

  const byKey = useMemo(() => {
    const m = new Map<string, Glyph>()
    for (const g of library?.glyphs ?? []) m.set(`${g.glyph}|${g.form}`, g)
    return m
  }, [library])

  const [selected, setSelected] = useState<{ glyph: string; form: string } | null>(null)
  const [strokes, setStrokes] = useState<Stroke[]>([])
  const [hints, setHints] = useState<string[]>([])
  const [message, setMessage] = useState<string | null>(null)
  const existing = selected ? byKey.get(`${selected.glyph}|${selected.form}`) : undefined
  const script = alphabet?.script ?? 'latin'
  const font = handFontFor(languageCode)
  const guideFont = script === 'arabic' ? "'Noto Naskh Arabic', serif" : `${font.family}, serif`

  const select = (glyph: string, form: string) => {
    setSelected({ glyph, form })
    setMessage(null)
    const g = byKey.get(`${glyph}|${form}`)
    // An existing form opens with its strokes, so an author can adjust
    // rather than start over; the canvas is 240 px tall, so scale to it.
    setStrokes(g ? fromGlyphBox(g.strokes, 240) : [])
    setHints(g?.hints ?? [])
  }

  const save = useMutation({
    mutationFn: () =>
      saveGlyph({
        languageId, glyph: selected!.glyph, form: selected!.form, style: activeStyle,
        strokes: toGlyphBox(strokes), hints: hints.slice(0, strokes.length),
      }),
    onSuccess: () => {
      setMessage('Saved as a draft — a reviewer signs it off.')
      invalidate()
    },
    onError: () => setMessage('That did not save — check there is at least one stroke.'),
  })
  const review = useMutation({
    mutationFn: (args: { id: string; reviewed: boolean }) => reviewGlyph(args.id, languageId, args.reviewed),
    onSuccess: invalidate,
  })
  const remove = useMutation({
    mutationFn: (id: string) => deleteGlyph(id, languageId),
    onSuccess: () => {
      setStrokes([])
      setHints([])
      invalidate()
    },
  })

  // Exemplars: one sentence, one flow.
  const [exText, setExText] = useState('')
  const [exStrokes, setExStrokes] = useState<Stroke[]>([])
  const addExemplar = useMutation({
    mutationFn: () => saveExemplar({ languageId, style: activeStyle, text: exText, strokes: toGlyphBox(exStrokes) }),
    onSuccess: () => {
      setExText('')
      setExStrokes([])
      invalidate()
    },
  })
  const reviewEx = useMutation({
    mutationFn: (args: { id: string; reviewed: boolean }) => reviewExemplar(args.id, languageId, args.reviewed),
    onSuccess: invalidate,
  })
  const removeEx = useMutation({
    mutationFn: (id: string) => deleteExemplar(id, languageId),
    onSuccess: invalidate,
  })

  if (!alphabet) return null
  const letters = alphabet.letters
  const authored = library?.glyphs.length ?? 0
  const reviewed = library?.glyphs.filter((g) => g.reviewed).length ?? 0
  const expected = letters.reduce((n, l) => n + l.forms.length, 0)

  return (
    <div data-testid="strokes-panel" className="space-y-4">
      <div className="rounded-2xl border border-gray-200 bg-white p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="font-semibold text-gray-800">Strokes · {alphabet.script}</h2>
            <p className="text-xs text-gray-500">
              How each letter is written, traced by a speaker. {reviewed} of {expected} forms reviewed
              ({authored} authored) in this style.
            </p>
          </div>
          {alphabet.styles.length > 1 && (
            <div className="flex rounded-full border border-gray-200 bg-white p-0.5 text-xs font-semibold">
              {alphabet.styles.map((s) => (
                <button
                  key={s}
                  type="button"
                  aria-pressed={activeStyle === s}
                  onClick={() => {
                    setStyle(s)
                    setSelected(null)
                    setStrokes([])
                  }}
                  className={`rounded-full px-3 py-1 ${activeStyle === s ? 'bg-lang text-lang-on' : 'text-gray-600'}`}
                >
                  {s}
                </button>
              ))}
            </div>
          )}
        </div>
        {isError && (
          <p className="text-sm text-amber-700">
            The stroke library is not set up on this server yet (migration 20261020).
          </p>
        )}

        {/* The grid: every letter, every form, with its status. */}
        <div className="overflow-x-auto">
          <table className="text-sm whitespace-nowrap" data-testid="strokes-grid">
            <tbody>
              {letters.map((l) => (
                <tr key={l.glyph} className="border-t border-gray-50">
                  <th className="py-1 pe-3 text-start font-semibold text-gray-800">
                    <span className="text-lg">{l.glyph}</span>
                    {l.romanization && <span className="ms-1 text-xs text-gray-400">{l.romanization}</span>}
                  </th>
                  {l.forms.map((form) => {
                    const g = byKey.get(`${l.glyph}|${form}`)
                    const isSel = selected?.glyph === l.glyph && selected?.form === form
                    return (
                      <td key={form} className="py-1 pe-1">
                        <button
                          type="button"
                          onClick={() => select(l.glyph, form)}
                          data-testid={`form-${l.glyph}-${form}`}
                          aria-pressed={isSel}
                          className={`rounded-lg border px-2 py-1 text-xs ${
                            isSel ? 'border-lang bg-lang-soft/40 text-gray-900'
                            : g?.reviewed ? 'border-green-200 bg-green-50 text-green-800'
                            : g ? 'border-amber-200 bg-amber-50 text-amber-800'
                            : 'border-gray-200 bg-white text-gray-500'
                          }`}
                          title={g?.reviewed ? 'reviewed' : g ? 'draft' : 'not yet authored'}
                        >
                          {form}
                          {g && <span className="ms-1">{g.reviewed ? '✓' : '·'}</span>}
                        </button>
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {selected && (
        <div className="rounded-2xl border border-gray-200 bg-white p-4 space-y-3" data-testid="strokes-editor">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="font-semibold text-gray-800">
                <span className="text-2xl me-2">{cased(shaped(script, selected.glyph, selected.form), selected.form)}</span>
                {selected.form} · {activeStyle}
                {existing && (
                  <span className={`ms-2 rounded-full px-2 py-0.5 text-[11px] ${existing.reviewed ? 'bg-green-50 text-green-800' : 'bg-amber-50 text-amber-800'}`}>
                    {existing.reviewed ? 'reviewed' : 'draft'}
                  </span>
                )}
              </h3>
              <p className="text-xs text-gray-500">
                Trace over the faint letter, one stroke at a time, in the order a native writer draws
                them. Lift the pen between strokes; a joined run is one stroke.
              </p>
            </div>
            {strokes.length > 0 && <StrokePreview strokes={toGlyphBox(strokes)} size={120} />}
          </div>
          <InkCanvas
            strokes={strokes}
            onChange={setStrokes}
            rtl={script === 'arabic' || script === 'hebrew'}
            guide={{
              text: cased(shaped(script, selected.glyph, selected.form), selected.form),
              fontFamily: guideFont,
              scale: 0.72,
            }}
            baseline={false}
          />
          {strokes.length > 0 && (
            <ol className="space-y-1 text-sm" data-testid="stroke-list">
              {strokes.map((s, i) => (
                <li key={i} className="flex items-center gap-2">
                  <span className="w-5 text-gray-500">{i + 1}.</span>
                  <input
                    type="text"
                    value={hints[i] ?? ''}
                    onChange={(e) => {
                      const next = [...hints]
                      next[i] = e.target.value
                      setHints(next)
                    }}
                    placeholder="Hint for this stroke, e.g. start at the top"
                    className="flex-1 rounded-lg border border-gray-200 px-2 py-1 text-sm"
                  />
                  <span className="text-xs text-gray-400">{s.length} pts</span>
                  <button
                    type="button"
                    onClick={() => {
                      setStrokes(strokes.filter((_, k) => k !== i))
                      setHints(hints.filter((_, k) => k !== i))
                    }}
                    aria-label={`Delete stroke ${i + 1}`}
                    className="text-gray-400 hover:text-red-600"
                  >
                    <Trash2 className="h-4 w-4" aria-hidden />
                  </button>
                </li>
              ))}
            </ol>
          )}
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => save.mutate()}
              disabled={strokes.length === 0 || save.isPending}
              data-testid="strokes-save"
              className="rounded-xl bg-lang px-4 py-2 text-sm font-bold text-lang-on disabled:opacity-50"
            >
              {save.isPending ? 'Saving…' : existing ? 'Save changes' : 'Save'}
            </button>
            <button
              type="button"
              onClick={() => {
                setStrokes([])
                setHints([])
              }}
              disabled={strokes.length === 0}
              className="rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 disabled:opacity-50"
            >
              Clear
            </button>
            {existing && canReview && (
              <button
                type="button"
                onClick={() => review.mutate({ id: existing.id, reviewed: !existing.reviewed })}
                disabled={review.isPending}
                data-testid="strokes-review"
                className="inline-flex items-center gap-1 rounded-xl border border-green-300 px-3 py-2 text-sm font-semibold text-green-800"
              >
                <Check className="h-4 w-4" aria-hidden />
                {existing.reviewed ? 'Un-review' : 'Mark reviewed'}
              </button>
            )}
            {existing && (
              <button
                type="button"
                onClick={() => {
                  if (window.confirm("Delete this form's strokes?")) remove.mutate(existing.id)
                }}
                disabled={remove.isPending}
                className="ms-auto text-sm text-gray-500 hover:text-red-700"
              >
                Delete
              </button>
            )}
          </div>
          {message && <p className="text-sm text-gray-600" data-testid="strokes-message">{message}</p>}
        </div>
      )}

      {/* Exemplar sentences: written whole, in one flow. */}
      <div className="rounded-2xl border border-gray-200 bg-white p-4 space-y-3" data-testid="exemplars">
        <div>
          <h3 className="font-semibold text-gray-800">Exemplar sentences · {activeStyle}</h3>
          <p className="text-xs text-gray-500">
            A sentence as you would write it on paper, in one flow — the model a learner watches, and
            the yardstick the word composer is tuned against. A dozen per script, covering every letter.
          </p>
        </div>
        <input
          type="text"
          value={exText}
          onChange={(e) => setExText(e.target.value)}
          placeholder="The sentence, typed"
          data-testid="exemplar-text"
          dir={script === 'arabic' || script === 'hebrew' ? 'rtl' : 'ltr'}
          className="w-full rounded-xl border border-gray-200 px-3 py-2 text-base"
        />
        <InkCanvas strokes={exStrokes} onChange={setExStrokes} rtl={script === 'arabic' || script === 'hebrew'} height={200} />
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => addExemplar.mutate()}
            disabled={!exText.trim() || exStrokes.length === 0 || addExemplar.isPending}
            data-testid="exemplar-save"
            className="rounded-xl bg-lang px-4 py-2 text-sm font-bold text-lang-on disabled:opacity-50"
          >
            Save exemplar
          </button>
          <button
            type="button"
            onClick={() => setExStrokes([])}
            disabled={exStrokes.length === 0}
            className="rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 disabled:opacity-50"
          >
            Clear
          </button>
        </div>
        {(library?.exemplars.length ?? 0) > 0 && (
          <ul className="divide-y divide-gray-50 text-sm">
            {library!.exemplars.map((e: Exemplar) => (
              <li key={e.id} className="flex items-center justify-between gap-2 py-2">
                <span className="min-w-0 truncate">
                  {e.text}
                  <span className={`ms-2 rounded-full px-2 py-0.5 text-[11px] ${e.reviewed ? 'bg-green-50 text-green-800' : 'bg-amber-50 text-amber-800'}`}>
                    {e.reviewed ? 'reviewed' : 'draft'}
                  </span>
                </span>
                <span className="flex flex-none gap-2">
                  {canReview && (
                    <button
                      type="button"
                      onClick={() => reviewEx.mutate({ id: e.id, reviewed: !e.reviewed })}
                      className="text-xs font-semibold text-green-800"
                    >
                      {e.reviewed ? 'Un-review' : 'Mark reviewed'}
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => {
                      if (window.confirm('Delete this exemplar?')) removeEx.mutate(e.id)
                    }}
                    aria-label={`Delete exemplar ${e.text}`}
                    className="text-gray-400 hover:text-red-600"
                  >
                    <Trash2 className="h-4 w-4" aria-hidden />
                  </button>
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
