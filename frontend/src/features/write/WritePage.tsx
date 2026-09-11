import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Eraser, Loader2, Undo2 } from 'lucide-react'
import {
  assessWriting,
  confirmWriting,
  finishWriteBaseline,
  getHandProfile,
  getWriteBaseline,
  getWritePrompts,
  getWriteStatus,
} from '../../api/write'
import type { TutorAllowance } from '../../api/tutor'
import type { ConfirmResult, Misread, WriteAssessment, WriteBaseline, WriteKind, WriteStyle } from '../../api/write'
import { getLanguages } from '../../api/profile'
import { getStrokeManifest } from '../../api/strokes'
import LettersMode from './LettersMode'
import { usePrefsStore } from '../../stores/prefsStore'
import AiDisclaimer from '../../components/AiDisclaimer'
import LanguageWrapper from '../../components/LanguageWrapper'
import SectionHeader from '../../components/SectionHeader'
import UsageMeter from '../../components/UsageMeter'
import { PAGE_WIDE } from '../../lib/layout'
import InkCanvas from './InkCanvas'
import { compactStrokes, hasInk } from './ink'
import type { Stroke } from './ink'
import { renderInkToPng } from './inkExport'
import { averageMeasures, measures, neatness, neatnessRelative } from './neatness'
import type { NeatnessMeasures, Verdict } from './neatness'
import { defaultStyle, ensureHandFont, handFontFor, hasCursiveToggle } from './handFont'

/** What the learner is writing against. `own` is text they typed
 * themselves; `free` is nothing at all. */
type PromptKind = 'sentence' | 'word' | 'own' | 'free' | 'letters'

/** A baseline session in progress (§12.2): the eight prompts, where the
 * writer is, and each line's verdict so the end can sum them. */
interface BaselineRun {
  info: WriteBaseline
  index: number
  results: { right: boolean; misread: Misread[] }[]
  /** Each confirmed line's raw neatness — averaged into the writer's usual. */
  measures: NeatnessMeasures[]
  done: boolean
}

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
  const location = useLocation()
  const { t } = useTranslation()
  const queryClient = useQueryClient()
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
  // The stroke library decides whether guided Letters is offered: a
  // style is live once any of its forms is reviewed (Phase 3).
  const { data: strokeManifest } = useQuery({
    queryKey: ['write-manifest', activeLanguageId],
    queryFn: () => getStrokeManifest(activeLanguageId!),
    enabled: !!activeLanguageId,
    retry: false,
  })
  const letterStyles = Object.entries(strokeManifest?.styles ?? {})
    .filter(([, v]) => v.reviewed > 0)
    .map(([k]) => k)
  const [letterStyle, setLetterStyle] = useState<string | null>(null)
  const activeLetterStyle = letterStyle ?? letterStyles[0] ?? null
  // The hand profile decides whether "Set up my hand" is offered — it
  // needs the toggle on and the migration present.
  const { data: profile } = useQuery({
    queryKey: ['hand-profile', activeLanguageId],
    queryFn: () => getHandProfile(activeLanguageId!),
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
  // "I wrote this": the reader's reading, editable, and what happened when
  // the writer confirmed it.
  const [reading, setReading] = useState('')
  const [learned, setLearned] = useState<ConfirmResult | null>(null)
  // Free writing: "is this what you wrote?" — No opens the reading to edit.
  const [editing, setEditing] = useState(false)
  // The baseline session, when one is running.
  const [baseline, setBaseline] = useState<BaselineRun | null>(null)
  const [baselineError, setBaselineError] = useState<string | null>(null)

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
  const baselinePrompt = baseline && !baseline.done ? baseline.info.prompts[baseline.index] : undefined
  const expected =
    baselinePrompt ? baselinePrompt.answer
    : kind === 'own' ? ownText.trim() || null
    : kind === 'free' ? null
    : (current?.answer ?? null)

  // Against the writer's own usual once a baseline exists; fixed bars
  // before that (§12 D).
  const usual = profile?.readout?.baseline_neatness ?? null
  const report = useMemo(
    () => (usual ? neatnessRelative(strokes, usual) : neatness(strokes)),
    [strokes, usual],
  )
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
        strokes: compactStrokes(strokes),
      })
    },
    onMutate: () => {
      setError(null)
      setLearned(null)
    },
    onSuccess: (data) => {
      setResult(data)
      setAllowance(data.allowance)
      // In a baseline the writer wrote the line shown, so that is what a
      // "yes" confirms — the diff against the reading is the verdict.
      setReading(data.expected ?? data.transcription)
      setEditing(false)
    },
    onError: () => {
      setError(t('write.checkFailed'))
    },
  })

  // The writer's word over the reader's: the canvas becomes a confirmed
  // sample of their hand, and the letters the reader flagged stop being
  // flagged. Free, and the single most useful thing they can tap after
  // a misread.
  const confirm = useMutation({
    mutationFn: async () => {
      const image = await renderInkToPng(strokes)
      if (!image) throw new Error('no-canvas')
      return confirmWriting({
        languageId: activeLanguageId!,
        image,
        text: reading.trim(),
        letters: (result?.letterform_notes ?? []).map((n) => n.letter).filter(Boolean),
        strokes: compactStrokes(strokes),
        read: result?.transcription ?? '',
        source: baselinePrompt ? 'baseline' : 'confirm',
      })
    },
    onSuccess: (data) => {
      setLearned(data)
      if (baseline && !baseline.done) advanceBaseline({ right: !!data.right, misread: data.misread ?? [] })
    },
    onError: () => {
      setError(t('write.confirmFailed'))
    },
  })

  const reset = () => {
    setStrokes([])
    setResult(null)
    setError(null)
    setLearned(null)
  }

  // --- The baseline session (§12.2) ---------------------------------------
  const startBaseline = useMutation({
    mutationFn: () => getWriteBaseline(activeLanguageId!),
    onMutate: () => setBaselineError(null),
    onSuccess: (info) => {
      if (!info.allowed) {
        setBaselineError(t('write.baselineNotToday'))
        return
      }
      if (info.prompts.length === 0) {
        setBaselineError(t('write.baselineEmpty'))
        return
      }
      setBaseline({ info, index: 0, results: [], measures: [], done: false })
      reset()
    },
    onError: () => setBaselineError(t('write.checkFailed')),
  })
  const finishBaseline = useMutation({
    mutationFn: (run: BaselineRun) =>
      finishWriteBaseline({
        languageId: activeLanguageId!, covered: run.info.covered, total: run.info.total,
        neatness: averageMeasures(run.measures),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['hand-profile'] }),
  })
  const advanceBaseline = (verdict: { right: boolean; misread: Misread[] }, skipped = false) => {
    // A confirmed line's measures are the writer's usual; a skipped one is not.
    const m = skipped ? null : measures(strokes)
    setBaseline((b) => {
      if (!b) return b
      const results = [...b.results, verdict]
      const last = b.index + 1 >= b.info.prompts.length
      const next = {
        ...b, results, index: b.index + 1, done: last,
        measures: m ? [...b.measures, m] : b.measures,
      }
      if (last) finishBaseline.mutate(next)
      return next
    })
    // The next line gets a clean canvas; the summary reads the results.
    setStrokes([])
    setResult(null)
    setLearned(null)
    setError(null)
  }
  const skipBaseline = () => advanceBaseline({ right: false, misread: [] }, true)
  const leaveBaseline = () => {
    setBaseline(null)
    reset()
  }
  // Account's "Set up my hand" lands here with ?baseline=1.
  const wantsBaseline = new URLSearchParams(location.search).get('baseline') === '1'
  const baselineOffered = !!profile?.available && profile.adapt && status?.available !== false
  useEffect(() => {
    if (wantsBaseline && baselineOffered && !baseline && !startBaseline.isPending) {
      startBaseline.mutate()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wantsBaseline, baselineOffered])

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
    ...(letterStyles.length > 0 ? [{ key: 'letters' as PromptKind, label: t('write.kindLetters') }] : []),
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

        {/* Set up my hand: eight lines in one sitting (§12.2). Offered when
            the reader may learn this hand; a redo when one already exists. */}
        {baselineOffered && !baseline && (
          <div
            data-testid="baseline-offer"
            className="rounded-2xl border border-lang/30 bg-lang-soft/30 p-4 flex flex-wrap items-center justify-between gap-3"
          >
            <div className="min-w-0">
              <p className="font-semibold text-gray-900">
                {profile?.stats && (profile.stats as { baseline_at?: string }).baseline_at
                  ? t('write.baselineRedo')
                  : t('write.baselineTitle')}
              </p>
              <p className="text-sm text-gray-600">{t('write.baselinePitch')}</p>
              {baselineError && (
                <p role="alert" className="mt-1 text-sm text-amber-700">{baselineError}</p>
              )}
            </div>
            <button
              type="button"
              onClick={() => startBaseline.mutate()}
              disabled={startBaseline.isPending}
              data-testid="baseline-start"
              className="rounded-xl bg-lang px-4 py-2 text-sm font-bold text-lang-on disabled:opacity-50"
              style={{ minHeight: '40px' }}
            >
              {t('write.baselineStart')}
            </button>
          </div>
        )}

        {baseline?.done && (
          <BaselineSummary run={baseline} code={code} onClose={leaveBaseline} />
        )}

        {baselinePrompt && (
          <div data-testid="baseline-prompt" className="rounded-2xl border border-lang/30 bg-white p-4 space-y-1">
            <div className="flex items-center justify-between gap-2">
              <p className="text-xs uppercase tracking-wide text-lang-label/80">
                {t('write.baselineTitle')} · {t('write.baselineStep', {
                  n: baseline!.index + 1, total: baseline!.info.prompts.length,
                })}
              </p>
              <button type="button" onClick={leaveBaseline} className="text-xs text-gray-500 hover:underline">
                {t('write.baselineLeave')}
              </button>
            </div>
            <p className="text-xs text-gray-500">{t('write.baselineWrite')}</p>
            <LanguageWrapper languageCode={code ?? 'en'}>
              <p data-testid="baseline-answer" className="text-2xl font-semibold text-gray-900">
                {baselinePrompt.answer}
              </p>
            </LanguageWrapper>
            {baselinePrompt.prompt && baselinePrompt.prompt !== baselinePrompt.answer && (
              <p className="text-sm text-gray-600">{baselinePrompt.prompt}</p>
            )}
          </div>
        )}

        {/* What to write */}
        {!baseline && (
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

        )}

        {kind === 'letters' && activeLetterStyle && activeLanguageId && (
          <div className="space-y-2">
            {letterStyles.length > 1 && (
              <div className="flex rounded-full border border-gray-200 bg-white p-0.5 text-xs font-semibold w-fit">
                {letterStyles.map((s) => (
                  <button
                    key={s}
                    type="button"
                    aria-pressed={activeLetterStyle === s}
                    onClick={() => setLetterStyle(s)}
                    className={`rounded-full px-3 py-1 ${activeLetterStyle === s ? 'bg-lang text-lang-on' : 'text-gray-600'}`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}
            <LettersMode languageId={activeLanguageId} code={code} style={activeLetterStyle} />
          </div>
        )}

        {!baseline && kind !== 'letters' && (
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
        )}

        {/* The surface */}
        {kind !== 'letters' && (
        <>
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
          <ResultPanel result={result} code={code} rtl={rtl} fontFamily={font.family}>
            {/* Offered when the reader could be wrong: a miss, an unsure
                read, or free writing with no expected text at all. A sure,
                matching read was already kept as a sample server-side. */}
            {baselinePrompt && result.adapt && inked && (
              <div data-testid="baseline-verdict" className="flex flex-wrap items-center gap-2 border-t border-gray-100 pt-3">
                <span className="text-sm text-gray-700">{t('write.baselineAsk')}</span>
                <button
                  type="button"
                  onClick={() => confirm.mutate()}
                  disabled={confirm.isPending}
                  data-testid="baseline-yes"
                  className="rounded-xl border border-lang bg-white px-3 py-2 text-sm font-semibold text-lang hover:bg-lang-soft/40 disabled:opacity-50"
                  style={{ minHeight: '40px' }}
                >
                  {confirm.isPending ? t('write.confirming') : t('write.baselineYes')}
                </button>
                <button
                  type="button"
                  onClick={skipBaseline}
                  disabled={confirm.isPending}
                  data-testid="baseline-skip"
                  className="rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-600"
                  style={{ minHeight: '40px' }}
                >
                  {t('write.baselineSkip')}
                </button>
              </div>
            )}
            {!baselinePrompt && result.adapt && inked && result.transcription &&
              (!result.matches_target || result.confidence === 'low' || !result.expected) && (
              <div data-testid="write-confirm-box" className="space-y-2 border-t border-gray-100 pt-3">
                {learned !== null ? (
                  <div className="space-y-1 text-sm">
                    <p data-testid="write-learned" className="text-green-800">
                      {!learned.kept ? t('write.adaptOff') : t('write.learned', { count: learned.samples })}
                    </p>
                    {learned.readout && learned.readout.total > 0 && (
                      <p data-testid="write-accuracy" className="text-gray-700">
                        {t('write.accuracy', { right: learned.readout.right, total: learned.readout.total })}
                      </p>
                    )}
                    {learned.misread && learned.misread.length > 0 && (
                      <p data-testid="write-misread" className="text-gray-700">
                        {t('write.trips')}{' '}
                        <LanguageWrapper languageCode={code ?? 'en'} inline>
                          <span className="font-semibold text-gray-900">
                            {learned.misread.map((m) => m.wrote || m.read).filter(Boolean).join(' ')}
                          </span>
                        </LanguageWrapper>
                      </p>
                    )}
                  </div>
                ) : !result.expected && !editing ? (
                  // The writer's verdict on the reading — the one signal
                  // the reader cannot produce itself.
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm text-gray-700">{t('write.isThisIt')}</span>
                    <button
                      type="button"
                      onClick={() => confirm.mutate()}
                      disabled={confirm.isPending || !reading.trim() || !result.transcription}
                      data-testid="write-confirm"
                      className="rounded-xl border border-lang bg-white px-3 py-2 text-sm font-semibold text-lang hover:bg-lang-soft/40 disabled:opacity-50"
                      style={{ minHeight: '40px' }}
                    >
                      {confirm.isPending ? t('write.confirming') : t('write.yesThatsIt')}
                    </button>
                    <button
                      type="button"
                      onClick={() => setEditing(true)}
                      disabled={confirm.isPending}
                      data-testid="write-not-it"
                      className="rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50"
                      style={{ minHeight: '40px' }}
                    >
                      {t('write.noIWrote')}
                    </button>
                  </div>
                ) : (
                  <>
                    {!result.expected && (
                      <input
                        type="text"
                        value={reading}
                        onChange={(e) => setReading(e.target.value)}
                        placeholder={t('write.confirmPlaceholder')}
                        data-testid="write-confirm-text"
                        dir={rtl ? 'rtl' : 'ltr'}
                        autoFocus
                        className="w-full rounded-xl border border-gray-200 px-3 py-2 text-base"
                      />
                    )}
                    <button
                      type="button"
                      onClick={() => confirm.mutate()}
                      disabled={confirm.isPending || !reading.trim()}
                      data-testid="write-confirm"
                      className="rounded-xl border border-lang bg-white px-3 py-2 text-sm font-semibold text-lang hover:bg-lang-soft/40 disabled:opacity-50"
                      style={{ minHeight: '40px' }}
                    >
                      {confirm.isPending
                        ? t('write.confirming')
                        : result.expected ? t('write.confirmExpected') : t('write.confirmReading')}
                    </button>
                  </>
                )}
              </div>
            )}
          </ResultPanel>
        )}

        {meter && <UsageMeter allowance={meter} />}
        <AiDisclaimer />
        </>
        )}
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
  const rel = !!report.relative
  const word = (v: Verdict) =>
    v === 'good' ? t(rel ? 'write.neatRelGood' : 'write.neatGood')
    : v === 'ok' ? t(rel ? 'write.neatRelOk' : 'write.neatOk')
    : v === 'poor' ? t(rel ? 'write.neatRelPoor' : 'write.neatPoor')
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
      <p className="mt-2 text-[11px] leading-snug text-gray-400">
        {rel ? t('write.neatRelHint') : t('write.neatHint')}
      </p>
    </div>
  )
}

function ResultPanel({
  result,
  code,
  rtl,
  fontFamily,
  children,
}: {
  result: WriteAssessment
  code: string | undefined
  rtl: boolean
  fontFamily: string
  children?: React.ReactNode
}) {
  const { t } = useTranslation()
  const nothing = !result.transcription
  const unsure = result.confidence === 'low'
  // With nothing expected, "correct" would be the reader grading the
  // spelling of its OWN reading — meaningless to the writer, who is the
  // only one who knows what was written. Free writing gets a spelling
  // line and the question "is this what you wrote?" (below), not a badge.
  const free = !result.expected
  const badge = nothing
    ? null
    : unsure
      ? { text: t('write.unsure'), cls: 'bg-amber-50 text-amber-800 border-amber-200' }
      : free
        ? { text: result.matches_target ? t('write.spellingOk') : t('write.spellingCheck'),
            cls: 'bg-gray-50 text-gray-700 border-gray-200' }
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
                {n.letter && result.again?.[n.letter] && (
                  <span data-testid="write-again" className="ms-1 text-xs text-amber-700">
                    {t('write.again', { count: result.again[n.letter] + 1 })}
                  </span>
                )}
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
      {children}
    </div>
  )
}

function BaselineSummary({
  run,
  code,
  onClose,
}: {
  run: BaselineRun
  code: string | undefined
  onClose: () => void
}) {
  const { t } = useTranslation()
  const right = run.results.filter((r) => r.right).length
  const counts = new Map<string, number>()
  for (const r of run.results) {
    for (const m of r.misread) {
      const letter = m.wrote || m.read
      if (letter) counts.set(letter, (counts.get(letter) ?? 0) + 1)
    }
  }
  const watch = [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5).map(([l]) => l)
  return (
    <div data-testid="baseline-summary" className="rounded-2xl border border-lang/30 bg-white p-4 space-y-2">
      <p className="font-semibold text-gray-900">{t('write.baselineDoneTitle')}</p>
      <p className="text-sm text-gray-700">
        {t('write.baselineSummary', { right, total: run.results.length })}
      </p>
      <p className="text-sm text-gray-600">
        {t('write.baselineCoverage', { covered: run.info.covered, total: run.info.total })}
      </p>
      {watch.length > 0 && (
        <p className="text-sm text-gray-700">
          {t('write.trips')}{' '}
          <LanguageWrapper languageCode={code ?? 'en'} inline>
            <span className="font-semibold text-gray-900">{watch.join(' ')}</span>
          </LanguageWrapper>
        </p>
      )}
      <button
        type="button"
        onClick={onClose}
        data-testid="baseline-finish"
        className="rounded-xl bg-lang px-4 py-2 text-sm font-bold text-lang-on"
        style={{ minHeight: '40px' }}
      >
        {t('write.baselineFinish')}
      </button>
    </div>
  )
}

