import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Check, Eraser, Loader2, Undo2 } from 'lucide-react'
import {
  assessWriting,
  getWritePrompts,
  getWriteStatus,
} from '../../api/write'
import type { TutorAllowance } from '../../api/tutor'
import type { WriteAssessment, WriteKind, WriteStyle } from '../../api/write'
import { getLanguages } from '../../api/profile'
import { usePrefsStore } from '../../stores/prefsStore'
import AiDisclaimer from '../../components/AiDisclaimer'
import LanguageWrapper from '../../components/LanguageWrapper'
import SectionHeader from '../../components/SectionHeader'
import UsageMeter from '../../components/UsageMeter'
import { PAGE_WIDE } from '../../lib/layout'
import InkCanvas from './InkCanvas'
import { hasInk } from './ink'
import type { Stroke } from './ink'
import { renderInkToPng } from './inkExport'
import { neatness } from './neatness'
import type { Verdict } from './neatness'
import { defaultStyle, ensureHandFont, handFontFor, hasCursiveToggle } from './handFont'

/** What the learner is writing against. `own` is text they typed
 * themselves; `free` is nothing at all. */
type PromptKind = 'sentence' | 'word' | 'own' | 'free'

const RTL = new Set(['ar', 'fa', 'he'])

function shuffle<T>(xs: T[]): T[] {
  const out = [...xs]
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[out[i], out[j]] = [out[j], out[i]]
  }
  return out
}

/**
 * Write — Free write (docs/plans/handwriting.md, Phase 1).
 *
 * The learner writes by hand — a sentence to translate, one of their own
 * words, text they typed, or anything — and taps Check. The ink is read
 * by a vision model (transcription first, always shown), the neatness
 * panel is measured on this device from the strokes, and the expected
 * text is shown in a written hand to compare shapes against. Nothing here
 * needs authored strokes; the guided letter and word modes of later
 * phases sit beside this, not in front of it.
 */
export default function WritePage() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)

  const { data: languages = [] } = useQuery({
    queryKey: ['languages'],
    queryFn: getLanguages,
  })
  const language = languages.find((l) => l.id === activeLanguageId)
  const code = language?.code
  const rtl = !!code && RTL.has(code)

  const { data: status } = useQuery({
    queryKey: ['write-status', activeLanguageId],
    queryFn: () => getWriteStatus(activeLanguageId!),
    enabled: !!activeLanguageId,
    retry: false,
  })

  const [kind, setKind] = useState<PromptKind>('sentence')
  const [index, setIndex] = useState(0)
  const [ownText, setOwnText] = useState('')
  const [style, setStyle] = useState<WriteStyle>('print')
  const [strokes, setStrokes] = useState<Stroke[]>([])
  const [result, setResult] = useState<WriteAssessment | null>(null)
  const [allowance, setAllowance] = useState<TutorAllowance | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setStyle(defaultStyle(code))
  }, [code])

  const font = useMemo(() => handFontFor(code), [code])
  useEffect(() => {
    ensureHandFont(font)
  }, [font])

  const promptKind = kind === 'sentence' || kind === 'word' ? kind : null
  const { data: prompts = [], isLoading: promptsLoading } = useQuery({
    queryKey: ['write-prompts', activeLanguageId, promptKind],
    queryFn: () => getWritePrompts(activeLanguageId!, promptKind!),
    enabled: !!activeLanguageId && !!promptKind,
    select: shuffle,
    staleTime: 5 * 60 * 1000,
  })
  const current = promptKind ? prompts[index % Math.max(1, prompts.length)] : undefined
  const expected =
    kind === 'own' ? ownText.trim() || null
    : kind === 'free' ? null
    : (current?.answer ?? null)

  const report = useMemo(() => neatness(strokes), [strokes])
  const inked = hasInk(strokes)
  const meter = allowance ?? status?.allowance ?? null

  const check = useMutation({
    mutationFn: async () => {
      const image = await renderInkToPng(strokes)
      if (!image) throw new Error('no-canvas')
      const apiKind: WriteKind =
        kind === 'word' ? 'word' : kind === 'free' ? 'free' : 'sentence'
      return assessWriting({
        languageId: activeLanguageId!,
        image,
        expected,
        kind: apiKind,
        style: hasCursiveToggle(code) ? style : null,
      })
    },
    onMutate: () => {
      setError(null)
    },
    onSuccess: (data) => {
      setResult(data)
      setAllowance(data.allowance)
    },
    onError: () => {
      setError(t('write.checkFailed'))
    },
  })

  const reset = () => {
    setStrokes([])
    setResult(null)
    setError(null)
  }

  const next = () => {
    setIndex((i) => i + 1)
    reset()
  }

  const changeKind = (k: PromptKind) => {
    setKind(k)
    setIndex(0)
    reset()
  }

  const kinds: { key: PromptKind; label: string }[] = [
    { key: 'sentence', label: t('write.kindSentence') },
    { key: 'word', label: t('write.kindWord') },
    { key: 'own', label: t('write.kindOwn') },
    { key: 'free', label: t('write.kindFree') },
  ]

  return (
    <div className="min-h-screen bg-gray-50 overflow-x-hidden">
      <div className={`${PAGE_WIDE} mx-auto px-4 py-6 space-y-4 pb-24 md:pb-6`}>
        <SectionHeader title={t('write.title')} />
        <button
          type="button"
          onClick={() => navigate('/practice')}
          className="text-sm text-lang hover:underline"
        >
          {t('write.backToPractice')}
        </button>
        <p className="text-sm text-gray-600">{t('write.intro')}</p>
        {status && !status.available && (
          <p data-testid="write-unavailable" className="text-sm text-amber-700">
            {t('write.unavailable')}
          </p>
        )}

        {/* What to write */}
        <div className="flex flex-wrap items-center gap-2" role="tablist">
          {kinds.map((k) => (
            <button
              key={k.key}
              type="button"
              role="tab"
              aria-selected={kind === k.key}
              data-testid={`kind-${k.key}`}
              onClick={() => changeKind(k.key)}
              className={`rounded-full px-3 py-1.5 text-sm font-semibold border transition-colors ${
                kind === k.key
                  ? 'bg-lang text-lang-on border-lang'
                  : 'bg-white text-gray-700 border-gray-200 hover:border-lang'
              }`}
              style={{ minHeight: '36px' }}
            >
              {k.label}
            </button>
          ))}
          {hasCursiveToggle(code) && (
            <div className="ms-auto flex rounded-full border border-gray-200 bg-white p-0.5 text-xs font-semibold">
              {(['print', 'cursive'] as WriteStyle[]).map((s) => (
                <button
                  key={s}
                  type="button"
                  data-testid={`style-${s}`}
                  aria-pressed={style === s}
                  onClick={() => setStyle(s)}
                  className={`rounded-full px-3 py-1 ${
                    style === s ? 'bg-lang text-lang-on' : 'text-gray-600'
                  }`}
                >
                  {s === 'print' ? t('write.stylePrint') : t('write.styleCursive')}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-2xl border border-gray-200 bg-white p-4">
          {promptKind && (
            promptsLoading ? (
              <p className="text-sm text-gray-500">{t('common.loading')}</p>
            ) : current ? (
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-xs uppercase tracking-wide text-gray-500">
                    {t('write.writeThis')}
                  </p>
                  <p data-testid="write-prompt" className="text-lg font-semibold text-gray-900">
                    {current.prompt || current.answer}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={next}
                  data-testid="write-next"
                  className="flex-none text-sm font-semibold text-lang hover:underline"
                  style={{ minHeight: '36px' }}
                >
                  {t('write.next')}
                </button>
              </div>
            ) : (
              <p data-testid="write-no-prompts" className="text-sm text-gray-500">
                {t('write.noPrompts')}
              </p>
            )
          )}
          {kind === 'own' && (
            <label className="block">
              <span className="text-xs uppercase tracking-wide text-gray-500">
                {t('write.writeThis')}
              </span>
              <input
                type="text"
                value={ownText}
                onChange={(e) => {
                  setOwnText(e.target.value)
                  setResult(null)
                }}
                placeholder={t('write.ownPlaceholder')}
                data-testid="write-own"
                dir={rtl ? 'rtl' : 'ltr'}
                className="mt-1 w-full rounded-xl border border-gray-200 px-3 py-2 text-base"
              />
            </label>
          )}
          {kind === 'free' && (
            <p className="text-sm text-gray-500">{t('write.freeHint')}</p>
          )}
        </div>

        {/* The surface */}
        <div className="space-y-2">
          <InkCanvas strokes={strokes} onChange={setStrokes} rtl={rtl} disabled={check.isPending} />
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs text-gray-500">{t('write.canvasHint')}</p>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setStrokes((s) => s.slice(0, -1))}
                disabled={strokes.length === 0 || check.isPending}
                data-testid="write-undo"
                className="inline-flex items-center gap-1 rounded-xl border border-gray-200 bg-white px-3 py-1.5 text-sm text-gray-700 disabled:opacity-50"
                style={{ minHeight: '36px' }}
              >
                <Undo2 className="h-4 w-4" aria-hidden /> {t('write.undo')}
              </button>
              <button
                type="button"
                onClick={reset}
                disabled={strokes.length === 0 || check.isPending}
                data-testid="write-clear"
                className="inline-flex items-center gap-1 rounded-xl border border-gray-200 bg-white px-3 py-1.5 text-sm text-gray-700 disabled:opacity-50"
                style={{ minHeight: '36px' }}
              >
                <Eraser className="h-4 w-4" aria-hidden /> {t('write.clear')}
              </button>
            </div>
          </div>
        </div>

        <button
          type="button"
          onClick={() => check.mutate()}
          disabled={!inked || !activeLanguageId || check.isPending || status?.available === false}
          data-testid="write-check"
          className="w-full rounded-2xl bg-lang text-lang-on font-bold px-4 py-3 disabled:opacity-50 inline-flex items-center justify-center gap-2"
          style={{ minHeight: '44px' }}
        >
          {check.isPending ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" aria-hidden /> {t('write.checking')}
            </>
          ) : (
            <>
              <Check className="h-5 w-5" aria-hidden /> {t('write.check')}
            </>
          )}
        </button>
        {error && (
          <p role="alert" className="text-sm text-red-700">
            {error}
          </p>
        )}

        {/* Neatness — from the strokes, on this device */}
        <NeatnessPanel report={report} inked={inked} />

        {result && (
          <ResultPanel result={result} code={code} rtl={rtl} fontFamily={font.family} />
        )}

        {meter && <UsageMeter allowance={meter} />}
        <AiDisclaimer />
      </div>
    </div>
  )
}

function NeatnessPanel({
  report,
  inked,
}: {
  report: ReturnType<typeof neatness>
  inked: boolean
}) {
  const { t } = useTranslation()
  if (!inked) return null
  const rows: { key: string; label: string; verdict: Verdict }[] = [
    { key: 'baseline', label: t('write.neatBaseline'), verdict: report.baseline },
    { key: 'size', label: t('write.neatSize'), verdict: report.size },
    { key: 'slant', label: t('write.neatSlant'), verdict: report.slant },
    { key: 'spacing', label: t('write.neatSpacing'), verdict: report.spacing },
  ]
  const word = (v: Verdict) =>
    v === 'good' ? t('write.neatGood')
    : v === 'ok' ? t('write.neatOk')
    : v === 'poor' ? t('write.neatPoor')
    : t('write.neatNa')
  const tone = (v: Verdict) =>
    v === 'good' ? 'text-green-700'
    : v === 'ok' ? 'text-amber-700'
    : v === 'poor' ? 'text-red-700'
    : 'text-gray-400'
  return (
    <div data-testid="neatness" className="rounded-2xl border border-gray-200 bg-white p-4">
      <p className="text-xs uppercase tracking-wide text-gray-500">{t('write.neatness')}</p>
      <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-sm sm:grid-cols-4">
        {rows.map((r) => (
          <div key={r.key} className="flex items-baseline justify-between gap-2">
            <dt className="text-gray-600">{r.label}</dt>
            <dd data-testid={`neat-${r.key}`} className={`font-semibold ${tone(r.verdict)}`}>
              {word(r.verdict)}
            </dd>
          </div>
        ))}
      </dl>
      <p className="mt-2 text-[11px] leading-snug text-gray-400">{t('write.neatHint')}</p>
    </div>
  )
}

function ResultPanel({
  result,
  code,
  rtl,
  fontFamily,
}: {
  result: WriteAssessment
  code: string | undefined
  rtl: boolean
  fontFamily: string
}) {
  const { t } = useTranslation()
  const nothing = !result.transcription
  const unsure = result.confidence === 'low'
  const badge = nothing
    ? null
    : unsure
      ? { text: t('write.unsure'), cls: 'bg-amber-50 text-amber-800 border-amber-200' }
      : result.matches_target
        ? { text: t('write.correct'), cls: 'bg-green-50 text-green-800 border-green-200' }
        : { text: t('write.incorrect'), cls: 'bg-red-50 text-red-800 border-red-200' }
  return (
    <div data-testid="write-result" className="rounded-2xl border border-gray-200 bg-white p-4 space-y-3">
      <div>
        <p className="text-xs uppercase tracking-wide text-gray-500">{t('write.readAs')}</p>
        {nothing ? (
          <p className="text-sm text-gray-600">{t('write.nothingRead')}</p>
        ) : (
          <LanguageWrapper languageCode={code ?? 'en'}>
            <p data-testid="write-read-as" className="text-xl font-semibold text-gray-900">
              {result.transcription}
            </p>
          </LanguageWrapper>
        )}
      </div>
      {badge && (
        <p
          data-testid="write-verdict"
          className={`inline-block rounded-full border px-3 py-1 text-sm font-semibold ${badge.cls}`}
        >
          {badge.text}
        </p>
      )}
      {!nothing && (
        <div className="flex items-center gap-2 text-sm">
          <span className="text-gray-600">{t('write.legibility')}</span>
          <span data-testid="write-legibility" aria-label={`${result.legibility}/5`} className="tracking-widest text-lang">
            {'●'.repeat(result.legibility)}
            <span className="text-gray-300">{'●'.repeat(5 - result.legibility)}</span>
          </span>
        </div>
      )}
      {result.word_diffs.length > 0 && (
        <div>
          <p className="text-xs uppercase tracking-wide text-gray-500">{t('write.diffs')}</p>
          <ul className="mt-1 space-y-1 text-sm">
            {result.word_diffs.map((d, i) => (
              <li key={i} className="flex flex-wrap items-baseline gap-x-2">
                <LanguageWrapper languageCode={code ?? 'en'} inline>
                  <span className="line-through text-red-700">{d.written}</span>
                </LanguageWrapper>
                <LanguageWrapper languageCode={code ?? 'en'} inline>
                  <span className="font-semibold text-gray-900">{d.expected}</span>
                </LanguageWrapper>
                {d.note && <span className="text-gray-600">— {d.note}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}
      {result.letterform_notes.length > 0 && (
        <div>
          <p className="text-xs uppercase tracking-wide text-gray-500">{t('write.notes')}</p>
          <ul className="mt-1 space-y-1 text-sm text-gray-700">
            {result.letterform_notes.map((n, i) => (
              <li key={i}>
                {n.letter && (
                  <LanguageWrapper languageCode={code ?? 'en'} inline>
                    <span className="font-semibold text-gray-900 me-1">{n.letter}</span>
                  </LanguageWrapper>
                )}
                {n.note}
              </li>
            ))}
          </ul>
        </div>
      )}
      {result.expected && (
        <div>
          <p className="text-xs uppercase tracking-wide text-gray-500">{t('write.compare')}</p>
          <p
            data-testid="write-compare"
            dir={rtl ? 'rtl' : 'ltr'}
            className="mt-1 text-3xl leading-relaxed text-gray-800"
            style={{ fontFamily: `${fontFamily}, cursive` }}
          >
            {result.expected}
          </p>
          <p className="text-[11px] text-gray-400">{t('write.compareHint')}</p>
        </div>
      )}
    </div>
  )
}
