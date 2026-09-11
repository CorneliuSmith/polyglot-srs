import { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, ChevronLeft, ChevronRight } from 'lucide-react'
import { getWritePrompts } from '../../api/write'
import type { WritePrompt } from '../../api/write'
import { recordLetterAttempts } from '../../api/strokes'
import type { Glyph } from '../../api/strokes'
import LanguageWrapper from '../../components/LanguageWrapper'
import InkCanvas from './InkCanvas'
import StrokePreview from './StrokePreview'
import { cells, compose, fitComposed } from './composer'
import type { Composed } from './composer'
import type { Stroke } from './ink'
import { matchComposed } from './matcher'
import type { ComposedMatch, LetterReason } from './matcher'

const CANVAS = 220
const TRACE_TOLERANCE = 0.18
const WRITE_TOLERANCE = 0.13

type Step = 'learn' | 'trace' | 'write'
type Source = 'word' | 'sentence'

/** A sentence broken into lines a canvas can hold: whole words, at most
 * `maxCells` letters a line; a longer word stands alone and shrinks. */
export function lines(text: string, maxCells: number): string[] {
  const out: string[] = []
  let cur = ''
  for (const w of text.trim().split(/\s+/).filter(Boolean)) {
    const next = cur ? `${cur} ${w}` : w
    if (cur && cells(next).length > maxCells) {
      out.push(cur)
      cur = w
    } else {
      cur = next
    }
  }
  if (cur) out.push(cur)
  return out
}

/**
 * Traced words and sentences (docs/plans/handwriting.md, Phase 4): the
 * same Learn → Trace → Write as the letters, over a template composed
 * from the reviewed letter forms — so the supply is every word on the
 * learner's cards and every example line. A sentence is worked line by
 * line. The Write step's verdict is per letter, and each letter form
 * written counts toward "known" exactly as in the Letters mode.
 */
export default function WordsMode({
  languageId,
  code,
  style,
  glyphs,
}: {
  languageId: string
  code: string | undefined
  style: string
  glyphs: Glyph[]
}) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [source, setSource] = useState<Source>('word')
  const { data: prompts = [], isLoading } = useQuery({
    queryKey: ['write-prompts', languageId, source],
    queryFn: () => getWritePrompts(languageId, source),
    staleTime: 5 * 60 * 1000,
  })
  const wrap = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(600)
  useEffect(() => {
    const measure = () => setWidth(wrap.current?.clientWidth || 600)
    measure()
    window.addEventListener('resize', measure)
    return () => window.removeEventListener('resize', measure)
  }, [])
  const maxCells = Math.max(6, Math.min(14, Math.floor(width / 60)))

  // Only what the library can compose in full.
  const traceable = useMemo(
    () => prompts.filter((p: WritePrompt) => compose(p.answer, code, style, glyphs).missing.length === 0),
    [prompts, code, style, glyphs],
  )
  const firstMissing = prompts.length > 0 && traceable.length === 0
    ? compose(prompts[0].answer, code, style, glyphs).missing
    : []

  const [index, setIndex] = useState(0)
  const [line, setLine] = useState(0)
  const [step, setStep] = useState<Step>('learn')
  const [strokes, setStrokes] = useState<Stroke[]>([])
  const [verdict, setVerdict] = useState<ComposedMatch | null>(null)
  const current = traceable[index % Math.max(1, traceable.length)]
  const pieces = useMemo(() => (current ? lines(current.answer, maxCells) : []), [current, maxCells])
  const text = pieces[Math.min(line, Math.max(0, pieces.length - 1))] ?? ''
  const composed: Composed | null = useMemo(
    () => (text ? compose(text, code, style, glyphs) : null),
    [text, code, style, glyphs],
  )
  const frame = useMemo(() => (composed ? fitComposed(composed, width, CANVAS) : null), [composed, width])

  useEffect(() => {
    setStrokes([])
    setVerdict(null)
  }, [index, line, step, source])
  useEffect(() => {
    setIndex(0)
    setLine(0)
    setStep('learn')
  }, [source])

  // Trace: the ink so far against the template's prefix; a letter snaps
  // when every point of it has been matched.
  const traced = useMemo(() => {
    if (step !== 'trace' || !composed || !frame || strokes.length === 0) return null
    return matchComposed(strokes, composed, { frame, tolerance: TRACE_TOLERANCE, openEnd: true })
  }, [strokes, step, composed, frame])
  const doneStrokes = useMemo(() => {
    if (!traced || !composed) return []
    const ok = new Set(traced.letters.filter((l) => l.ok).map((l) => l.index))
    return composed.owners.map((o, i) => (o.every((x) => ok.has(x)) ? i : -1)).filter((i) => i >= 0)
  }, [traced, composed])
  const traceComplete = !!traced && traced.ok

  const record = useMutation({
    mutationFn: (attempts: { glyphId: string; passed: boolean; score: number }[]) =>
      recordLetterAttempts({ languageId, attempts }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['write-progress'] }),
  })

  const check = () => {
    if (!composed) return
    const res = matchComposed(strokes, composed, { tolerance: WRITE_TOLERANCE })
    setVerdict(res)
    // One attempt per form: passed only if every instance of it passed.
    const byGlyph = new Map<string, { passed: boolean; score: number }>()
    res.letters.forEach((l) => {
      const g = composed.letters[l.index].glyph
      if (!g || l.reason === 'missing' && !l.covered) return
      const prev = byGlyph.get(g.id)
      byGlyph.set(g.id, {
        passed: (prev?.passed ?? true) && l.ok,
        score: Math.min(prev?.score ?? 1, l.score),
      })
    })
    const attempts = [...byGlyph.entries()].map(([glyphId, v]) => ({ glyphId, ...v }))
    if (attempts.length) record.mutate(attempts)
  }

  const next = () => {
    if (step === 'learn') setStep('trace')
    else if (step === 'trace') setStep('write')
    else if (line + 1 < pieces.length) {
      setLine(line + 1)
      setStep('learn')
    } else {
      setIndex((i) => i + 1)
      setLine(0)
      setStep('learn')
    }
  }

  const reason = (r: LetterReason | undefined) =>
    r === 'missing' ? t('write.letterMissing') : r === 'shape' ? t('write.letterShape') : ''

  const sourceTabs = (
    <div className="flex rounded-full border border-gray-200 bg-white p-0.5 text-xs font-semibold w-fit" role="tablist">
      {(['word', 'sentence'] as Source[]).map((s) => (
        <button
          key={s}
          type="button"
          role="tab"
          aria-selected={source === s}
          data-testid={`trace-source-${s}`}
          onClick={() => setSource(s)}
          className={`rounded-full px-3 py-1 ${source === s ? 'bg-lang text-lang-on' : 'text-gray-600'}`}
        >
          {s === 'word' ? t('write.kindWord') : t('write.kindSentence')}
        </button>
      ))}
    </div>
  )

  if (isLoading) return <p className="text-sm text-gray-500">{t('common.loading')}</p>
  if (!current || !composed || !frame) {
    return (
      <div className="space-y-2">
        {sourceTabs}
        <p data-testid="trace-empty" className="text-sm text-gray-500">
          {firstMissing.length > 0
            ? t('write.notTraceable', { letters: firstMissing.join(' ') })
            : t('write.noTraceable')}
        </p>
      </div>
    )
  }

  return (
    <div data-testid="words-mode" className="space-y-3" ref={wrap}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        {sourceTabs}
        <div className="flex gap-1 text-xs" role="tablist">
          {(['learn', 'trace', 'write'] as Step[]).map((s) => (
            <button
              key={s}
              type="button"
              role="tab"
              aria-selected={step === s}
              data-testid={`trace-step-${s}`}
              onClick={() => setStep(s)}
              className={`rounded-full px-3 py-1 ${step === s ? 'bg-lang text-lang-on' : 'text-gray-600'}`}
            >
              {t(`write.step_${s}`)}
            </button>
          ))}
        </div>
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white p-4 space-y-3">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <LanguageWrapper languageCode={code ?? 'en'}>
            <p data-testid="trace-text" className="text-xl font-semibold text-gray-900">
              {pieces.length > 1
                ? pieces.map((p, i) => (
                    <span key={i} className={i === line ? 'underline decoration-lang decoration-2' : 'text-gray-400'}>
                      {p}{' '}
                    </span>
                  ))
                : current.answer}
            </p>
          </LanguageWrapper>
          {current.prompt && current.prompt !== current.answer && (
            <p className="text-sm text-gray-600">{current.prompt}</p>
          )}
        </div>
        {pieces.length > 1 && (
          <p className="text-xs text-gray-500">{t('write.lineOf', { n: line + 1, total: pieces.length })}</p>
        )}

        {step === 'learn' && (
          <div className="space-y-1" data-testid="trace-learn">
            <StrokePreview strokes={[]} composed={composed} width={Math.min(width, 640)} height={CANVAS} />
            <p className="text-xs text-gray-500">{t('write.learnHint')}</p>
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
              rtl={composed.letters.length > 0 && composed.letters[0].x > composed.letters[composed.letters.length - 1].x}
              guideStrokes={step === 'trace' ? frame.strokes : undefined}
              guideDone={doneStrokes}
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
                    data-testid="trace-check"
                    className="inline-flex items-center gap-1 rounded-xl bg-lang px-3 py-1.5 text-sm font-bold text-lang-on disabled:opacity-50"
                  >
                    <Check className="h-4 w-4" aria-hidden /> {t('write.check')}
                  </button>
                )}
              </div>
            </div>
            {/* Letter by letter — live while tracing, on Check when writing. */}
            {(step === 'trace' ? traced : verdict) && (
              <LetterRow match={(step === 'trace' ? traced : verdict)!} composed={composed} reason={reason} live={step === 'trace'} />
            )}
            {traceComplete && (
              <p data-testid="trace-complete" className="text-sm text-green-800">{t('write.traceDone')}</p>
            )}
            {verdict && (
              <p
                data-testid="trace-verdict"
                className={`text-sm font-semibold ${verdict.ok ? 'text-green-800' : 'text-amber-800'}`}
              >
                {verdict.ok ? t('write.wordOk') : t('write.wordNotYet')}
              </p>
            )}
          </div>
        )}

        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={() => {
              if (line > 0) setLine(line - 1)
              else setIndex((i) => Math.max(0, i - 1))
              setStep('learn')
            }}
            disabled={index === 0 && line === 0}
            className="inline-flex items-center gap-1 text-sm text-gray-600 disabled:opacity-40"
          >
            <ChevronLeft className="h-4 w-4" aria-hidden /> {t('write.prevLetter')}
          </button>
          <button
            type="button"
            onClick={next}
            data-testid="trace-next"
            className="inline-flex items-center gap-1 rounded-xl border border-lang px-3 py-1.5 text-sm font-semibold text-lang"
          >
            {step === 'write' ? t('write.next') : t('write.nextStep')}
            <ChevronRight className="h-4 w-4" aria-hidden />
          </button>
        </div>
      </div>
    </div>
  )
}

/** The per-letter row: ✓ or ✗ under each letter, and on a miss the
 * expected form beside the reason. Shared with Free write's verdicts. */
export function LetterRow({
  match,
  composed,
  reason,
  live = false,
}: {
  match: ComposedMatch
  composed: Composed
  reason: (r: LetterReason | undefined) => string
  live?: boolean
}) {
  const { t } = useTranslation()
  const misses = match.letters.filter((l) => l.covered && !l.ok)
  return (
    <div data-testid="letter-row" className="space-y-2">
      <p className="text-xs uppercase tracking-wide text-gray-500">{t('write.letterByLetter')}</p>
      <div className="flex flex-wrap gap-1">
        {match.letters.map((l) => (
          <span
            key={l.index}
            data-testid={`letter-${l.index}`}
            data-state={l.ok ? 'ok' : l.covered ? 'miss' : 'pending'}
            className={`inline-flex min-w-[2rem] flex-col items-center rounded-lg border px-1.5 py-0.5 text-sm ${
              l.ok ? 'border-green-200 bg-green-50 text-green-900'
              : l.covered ? 'border-red-200 bg-red-50 text-red-900'
              : 'border-gray-200 bg-white text-gray-400'
            }`}
          >
            <span className="font-semibold">{l.char}</span>
            <span className="text-[10px]" aria-hidden>{l.ok ? '✓' : l.covered ? '✗' : '·'}</span>
          </span>
        ))}
      </div>
      {!live && misses.length > 0 && (
        <ul className="space-y-1">
          {misses.map((l) => {
            const g = composed.letters[l.index].glyph
            return (
              <li key={l.index} className="flex items-center gap-2 text-sm text-gray-700">
                {g && <StrokePreview strokes={g.strokes} size={44} playing={false} />}
                <span className="font-semibold">{l.char}</span>
                <span>{reason(l.reason)}</span>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
