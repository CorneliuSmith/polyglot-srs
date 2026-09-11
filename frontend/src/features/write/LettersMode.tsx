import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, ChevronLeft, ChevronRight } from 'lucide-react'
import { getAlphabet, getGlyphs, getLettersProgress, recordLetterAttempt } from '../../api/strokes'
import type { Glyph } from '../../api/strokes'
import LanguageWrapper from '../../components/LanguageWrapper'
import InkCanvas from './InkCanvas'
import StrokePreview from './StrokePreview'
import { fromGlyphBox } from './glyphBox'
import type { Stroke } from './ink'
import { matchStrokes } from './matcher'
import type { MatchResult, Reason } from './matcher'

const CANVAS = 260
const TRACE_TOLERANCE = 0.16
const WRITE_TOLERANCE = 0.1

type Step = 'learn' | 'trace' | 'write'

/**
 * Guided Letters (docs/plans/handwriting.md, Phase 3): Learn → Trace →
 * Write for every reviewed form of the script, in alphabet order, with
 * the forms of one letter as steps within it. Everything here is on the
 * device against the authored templates — no model, no spend — and only
 * the Write step counts toward "known" (three clean writes).
 */
export default function LettersMode({
  languageId,
  code,
  style,
}: {
  languageId: string
  code: string | undefined
  style: string
}) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const { data: alphabet } = useQuery({
    queryKey: ['write-alphabet', languageId],
    queryFn: () => getAlphabet(languageId),
    retry: false,
  })
  const { data: library } = useQuery({
    queryKey: ['write-glyphs', languageId, style],
    queryFn: () => getGlyphs(languageId, style),
    retry: false,
  })
  const { data: progress = [] } = useQuery({
    queryKey: ['write-progress', languageId, style],
    queryFn: () => getLettersProgress(languageId, style),
    retry: false,
  })

  // Reviewed forms in alphabet order: letter by letter, then the letter's
  // forms in the order the alphabet names them.
  const forms = useMemo(() => {
    if (!alphabet || !library) return [] as Glyph[]
    const byKey = new Map(library.glyphs.map((g) => [`${g.glyph}|${g.form}`, g]))
    const out: Glyph[] = []
    for (const l of alphabet.letters) {
      for (const f of l.forms) {
        const g = byKey.get(`${l.glyph}|${f}`)
        if (g) out.push(g)
      }
    }
    return out
  }, [alphabet, library])
  const known = useMemo(() => new Set(progress.filter((p) => p.known).map((p) => p.glyph_id)), [progress])

  const [index, setIndex] = useState(0)
  const [step, setStep] = useState<Step>('learn')
  const [strokes, setStrokes] = useState<Stroke[]>([])
  const [verdict, setVerdict] = useState<MatchResult | null>(null)
  const current = forms[index]
  const template = useMemo(() => (current ? fromGlyphBox(current.strokes, CANVAS) : []), [current])

  useEffect(() => {
    setStrokes([])
    setVerdict(null)
  }, [index, step])

  // Trace: each stroke is judged as it lands against the template prefix,
  // loosely; matched ones snap solid on the guide.
  const traceDone = useMemo(() => {
    if (step !== 'trace' || !current || strokes.length === 0) return []
    const res = matchStrokes(strokes, current.strokes.slice(0, strokes.length), { tolerance: TRACE_TOLERANCE })
    return res.strokes.filter((v) => v.ok).map((v) => v.index)
  }, [strokes, step, current])
  const traceComplete = step === 'trace' && current && traceDone.length === current.strokes.length

  const record = useMutation({
    mutationFn: (args: { passed: boolean; score: number }) =>
      recordLetterAttempt({ languageId, glyphId: current!.id, ...args }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['write-progress'] }),
  })

  const check = () => {
    if (!current) return
    const res = matchStrokes(strokes, current.strokes, { tolerance: WRITE_TOLERANCE })
    setVerdict(res)
    record.mutate({ passed: res.ok, score: res.score })
  }

  const next = () => {
    if (step === 'learn') setStep('trace')
    else if (step === 'trace') setStep('write')
    else {
      setIndex((i) => Math.min(forms.length - 1, i + 1))
      setStep('learn')
    }
  }

  if (!alphabet || !library) return <p className="text-sm text-gray-500">{t('common.loading')}</p>
  if (forms.length === 0) {
    return (
      <p data-testid="letters-empty" className="text-sm text-gray-500">
        {t('write.lettersEmpty')}
      </p>
    )
  }

  const reason = (r: Reason | undefined) =>
    r === 'missing' ? t('write.strokeMissing')
    : r === 'extra' ? t('write.strokeExtra')
    : r === 'direction' ? t('write.strokeDirection')
    : r === 'shape' ? t('write.strokeShape')
    : r === 'order' ? t('write.strokeOrder')
    : ''

  return (
    <div data-testid="letters-mode" className="space-y-3">
      {/* The strip: every reviewed form, filled in as it becomes known. */}
      <div className="flex flex-wrap gap-1" data-testid="letters-strip">
        {forms.map((g, i) => (
          <button
            key={g.id}
            type="button"
            onClick={() => {
              setIndex(i)
              setStep('learn')
            }}
            aria-current={i === index}
            title={`${g.glyph} · ${g.form}`}
            className={`h-8 min-w-8 rounded-lg border px-1.5 text-sm ${
              i === index ? 'border-lang bg-lang text-lang-on'
              : known.has(g.id) ? 'border-green-200 bg-green-50 text-green-800'
              : 'border-gray-200 bg-white text-gray-700'
            }`}
          >
            {g.form === 'upper' ? g.glyph.toUpperCase() : g.glyph}
          </button>
        ))}
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white p-4 space-y-3">
        <div className="flex items-center justify-between gap-2">
          <div>
            <LanguageWrapper languageCode={code ?? 'en'} inline>
              <span className="text-3xl font-semibold text-gray-900 me-2">
                {current.form === 'upper' ? current.glyph.toUpperCase() : current.glyph}
              </span>
            </LanguageWrapper>
            <span className="text-sm text-gray-500">
              {t(`write.form_${current.form}`, { defaultValue: current.form })} · {index + 1}/{forms.length}
            </span>
          </div>
          <div className="flex rounded-full border border-gray-200 bg-white p-0.5 text-xs font-semibold" role="tablist">
            {(['learn', 'trace', 'write'] as Step[]).map((s) => (
              <button
                key={s}
                type="button"
                role="tab"
                aria-selected={step === s}
                data-testid={`step-${s}`}
                onClick={() => setStep(s)}
                className={`rounded-full px-3 py-1 ${step === s ? 'bg-lang text-lang-on' : 'text-gray-600'}`}
              >
                {t(`write.step_${s}`)}
              </button>
            ))}
          </div>
        </div>

        {step === 'learn' && (
          <div className="flex flex-wrap items-start gap-4" data-testid="letters-learn">
            <StrokePreview strokes={current.strokes} size={200} />
            <ol className="space-y-1 text-sm text-gray-700">
              {current.strokes.map((_, i) => (
                <li key={i}>
                  <span className="me-1 font-semibold">{i + 1}.</span>
                  {current.hints[i] || t('write.strokeNoHint')}
                </li>
              ))}
              <li className="pt-1 text-xs text-gray-500">{t('write.learnHint')}</li>
            </ol>
          </div>
        )}

        {step !== 'learn' && (
          <div className="space-y-2">
            <InkCanvas
              strokes={strokes}
              onChange={(s) => {
                setStrokes(s)
                setVerdict(null)
              }}
              height={CANVAS}
              baseline={false}
              guideStrokes={step === 'trace' ? template : undefined}
              guideDone={traceDone}
            />
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs text-gray-500">
                {step === 'trace' ? t('write.traceHint') : t('write.writeHint')}
              </p>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setStrokes((s) => s.slice(0, -1))}
                  disabled={strokes.length === 0}
                  className="rounded-xl border border-gray-200 px-3 py-1.5 text-sm text-gray-700 disabled:opacity-50"
                >
                  {t('write.undo')}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setStrokes([])
                    setVerdict(null)
                  }}
                  disabled={strokes.length === 0}
                  className="rounded-xl border border-gray-200 px-3 py-1.5 text-sm text-gray-700 disabled:opacity-50"
                >
                  {t('write.clear')}
                </button>
                {step === 'write' && (
                  <button
                    type="button"
                    onClick={check}
                    disabled={strokes.length === 0}
                    data-testid="letters-check"
                    className="inline-flex items-center gap-1 rounded-xl bg-lang px-3 py-1.5 text-sm font-bold text-lang-on disabled:opacity-50"
                  >
                    <Check className="h-4 w-4" aria-hidden /> {t('write.check')}
                  </button>
                )}
              </div>
            </div>
            {traceComplete && (
              <p data-testid="trace-complete" className="text-sm text-green-800">{t('write.traceDone')}</p>
            )}
            {verdict && (
              <div data-testid="letters-verdict" className={`rounded-xl border p-3 text-sm ${verdict.ok ? 'border-green-200 bg-green-50 text-green-900' : 'border-amber-200 bg-amber-50 text-amber-900'}`}>
                <p className="font-semibold">
                  {verdict.ok ? t('write.letterOk') : t('write.letterNotYet')}
                </p>
                {!verdict.ok && (
                  <ul className="mt-1 space-y-0.5">
                    {verdict.strokes.filter((v) => !v.ok).map((v) => (
                      <li key={v.index}>
                        {t('write.strokeN', { n: v.index + 1 })}: {reason(v.reason)}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        )}

        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={() => {
              setIndex((i) => Math.max(0, i - 1))
              setStep('learn')
            }}
            disabled={index === 0}
            className="inline-flex items-center gap-1 text-sm text-gray-600 disabled:opacity-40"
          >
            <ChevronLeft className="h-4 w-4" aria-hidden /> {t('write.prevLetter')}
          </button>
          <button
            type="button"
            onClick={next}
            data-testid="letters-next"
            className="inline-flex items-center gap-1 rounded-xl border border-lang px-3 py-1.5 text-sm font-semibold text-lang"
          >
            {step === 'write' ? t('write.nextLetter') : t('write.nextStep')}
            <ChevronRight className="h-4 w-4" aria-hidden />
          </button>
        </div>
      </div>
    </div>
  )
}
