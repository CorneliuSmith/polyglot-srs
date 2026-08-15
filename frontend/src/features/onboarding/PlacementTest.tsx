import { useEffect, useRef, useState } from 'react'
import { Trans, useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  assessWritingSample,
  getWritingAvailability,
  placementNext,
  setLearnerLevel,
} from '../../api/onboarding'
import { getSchemaHealth, pendingMigrationNote } from '../../api/health'
import type {
  PlacementBreakdownItem,
  PlacementItem,
  WritingAssessment,
} from '../../api/onboarding'
import LanguageWrapper from '../../components/LanguageWrapper'
import { usePrefsStore } from '../../stores/prefsStore'
import { languageDisplayName } from '../../lib/languages'
import {
  backspaceUnit,
  composeScript,
  convertTranslit,
  deleteLastUnit,
  finalizeInput,
  isTranslitEnabled,
} from '../keyboards/translit'
import OnScreenKeyboard, { hasKeyboardLayout } from '../keyboards/OnScreenKeyboard'
import type { KeyboardLanguage } from '../keyboards/OnScreenKeyboard'
import type { Language } from '../../api/types'

const CEFR_ORDER = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']

/** "up two levels" / "the same level" / "down one" — how a retake compares
 * to the last one, which is the whole reason the retake exists. */
function movement(
  t: TFunction,
  previous: string | null | undefined,
  now: string,
): string | null {
  if (!previous) return null
  const from = CEFR_ORDER.indexOf(previous)
  const to = CEFR_ORDER.indexOf(now)
  if (from < 0 || to < 0) return null
  const step = to - from
  if (step === 0) return t('placement.sameAsLast', { previous })
  const n = Math.abs(step)
  const levels = t('placement.levelCount', { count: n })
  return step > 0
    ? t('placement.movedUp', { levels, previous })
    : t('placement.movedDown', { levels, previous })
}

/**
 * The adaptive placement test, extracted from onboarding so it can run at any
 * point in a language's life: the first time a learner opens a language, or as
 * a retake from settings. Same server staircase either way; the server varies
 * WHICH items it asks based on how many attempts came before, so a retake
 * measures the learner rather than their memory of the last test.
 *
 * Applying the result is a separate, explicit step — a test that silently
 * re-seated somebody's decks would be a nasty surprise for a learner who was
 * only curious.
 */
export default function PlacementTest({
  language,
  onClose,
}: {
  language: Language
  onClose: () => void
}) {
  const qc = useQueryClient()
  const { t, i18n } = useTranslation()
  const qwertyTranslit = usePrefsStore((s) => s.qwertyTranslit)

  const [history, setHistory] = useState<{ id: string; input: string }[]>([])
  const [item, setItem] = useState<PlacementItem | null>(null)
  const [input, setInput] = useState('')
  const [maxItems, setMaxItems] = useState(12)
  const [result, setResult] = useState<{
    level: string | null
    previous: string | null
    asked: number
    perLevel: Record<string, { correct: number; total: number }>
    breakdown: PlacementBreakdownItem[]
    threshold: number
  } | null>(null)
  // Whether the learner has asked to see the per-question evidence. Folded
  // away by default — the answer to "what level am I" is the level; the
  // working belongs one tap behind it.
  const [showWorking, setShowWorking] = useState(false)
  const [unavailable, setUnavailable] = useState(false)
  // When the start fails, ask the server WHY rather than shrugging. A schema
  // that is behind the build is the commonest cause and the app can already
  // detect it — it just never told anyone.
  const [cause, setCause] = useState<string | null>(null)
  // Learn and Review both offer the on-screen keyboard; placement did not,
  // which meant a learner being asked to TYPE Persian had no way to produce
  // the script at all on a phone. That doesn't measure their Persian — it
  // measures whether they happen to have the keyboard installed, and marks
  // them down for the difference. Open by default here, unlike in Learn: a
  // first-time learner has no reason to know the button exists.
  const [showKeyboard, setShowKeyboard] = useState(true)
  const inputRef = useRef<HTMLInputElement>(null)

  // The written route. The typed staircase measures recall item by item; a
  // paragraph measures what the learner can actually BUILD — subordination,
  // tense contrast, register — which is the only way a genuine C1 shows up.
  // Offered here rather than only in signup, so it reaches every language a
  // learner adds and every retake.
  const [writing, setWriting] = useState(false)
  // Set when the learner waves off the FINAL writing question. Kept apart
  // from `writing` because that flag also drives the "I'd rather write"
  // side door, which is a different thing entirely.
  const [skippedWriting, setSkippedWriting] = useState(false)
  const [sample, setSample] = useState('')
  const [assessment, setAssessment] = useState<WritingAssessment | null>(null)
  const { data: writingOffer } = useQuery({
    queryKey: ['writing-availability', language.id],
    queryFn: () => getWritingAvailability(language.id),
    retry: false,
  })
  const assess = useMutation({
    mutationFn: () =>
      assessWritingSample(
        language.id, language.code, sample.trim(), result?.level ?? null,
      ),
    onSuccess: setAssessment,
  })

  const next = useMutation({
    mutationFn: (h: { id: string; input: string }[]) =>
      placementNext(language.id, h),
    onSuccess: (res) => {
      if (!res.available) {
        setUnavailable(true)
        return
      }
      if (res.done) {
        setResult({
          level: res.estimated_level ?? null,
          previous: res.previous_level ?? null,
          asked: res.asked,
          perLevel: res.per_level ?? {},
          breakdown: res.breakdown ?? [],
          threshold: res.threshold ?? 0.6,
        })
        // The attempt is recorded server-side on completion — the offer
        // shouldn't come back the next time this language loads.
        qc.invalidateQueries({ queryKey: ['placement-history', language.id] })
        return
      }
      setItem(res.item ?? null)
      setInput('')
      if (res.max_items) setMaxItems(res.max_items)
    },
    onError: async () => {
      setCause(pendingMigrationNote(await getSchemaHealth()))
    },
  })

  const apply = useMutation({
    mutationFn: (level: string) => setLearnerLevel(language.id, level),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['learn-decks'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
      onClose()
    },
  })

  // Kick off the first item on mount.
  const start = next.mutate
  useEffect(() => {
    start([])
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [language.id])

  // What to place them at. A written sample outranks the staircase (the
  // server clamps it to one band) — production is what a level describes.
  const finalLevel =
    assessment?.blended_level ?? assessment?.level ?? result?.level ?? 'A1'

  // The final question, for accounts that have the writing assessment
  // (owner: a sample "is the best way to determine placement"). The
  // staircase measures what they recognize; a paragraph measures what they
  // can build. DERIVED rather than latched when the quiz finishes: the
  // availability query and the last staircase round race, and a learner
  // whose quiz landed first would silently never be asked.
  const finalWritingStep =
    !!result && !!writingOffer?.available && !assessment && !skippedWriting
  const showWriting = writing || finalWritingStep

  // The writing prompt, pitched at whatever the quiz just found: asking a
  // near-beginner to argue a position measures nothing, and giving a C1 "what
  // did you do yesterday" gives them no room to show what they have.
  const promptBand = (() => {
    const idx = CEFR_ORDER.indexOf(result?.level ?? 'A1')
    return idx >= 4 ? 'advanced' : idx >= 2 ? 'intermediate' : 'beginner'
  })()

  const submit = (raw: string) => {
    if (!item || next.isPending) return
    const finalized = finalizeInput(language.code, raw.trim(), qwertyTranslit)
    const h = [...history, { id: item.id, input: finalized }]
    setHistory(h)
    next.mutate(h)
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
      role="dialog"
      aria-modal="true"
      aria-label={t('placement.dialogLabel', { language: languageDisplayName(language.code, language.name, i18n.language) })}
      data-testid="placement-test"
    >
      <div className="w-full max-w-md rounded-2xl bg-white p-5 shadow-xl space-y-4">
        {unavailable ? (
          <div className="space-y-3">
            <p className="text-sm font-semibold text-gray-800">
              {t('placement.unavailableTitle', { language: languageDisplayName(language.code, language.name, i18n.language) })}
            </p>
            <p className="text-xs text-gray-500">
              {t('placement.unavailableHelp')}
            </p>
            <button
              type="button"
              onClick={onClose}
              className="w-full rounded-xl bg-lang text-lang-on px-4 py-2.5 text-sm font-semibold hover:bg-lang-dark"
              style={{ minHeight: '44px' }}
            >
              {t('placement.close')}
            </button>
          </div>
        ) : result && !showWriting ? (
          <div className="space-y-3" data-testid="placement-result">
            <p className="text-sm text-gray-800">
              <Trans
                i18nKey="placement.resultSummary"
                values={{
                  language: languageDisplayName(language.code, language.name, i18n.language),
                  level: finalLevel,
                  questions: t('placement.questionCount', { count: result.asked }),
                }}
                components={{ b: <b /> }}
              />
            </p>
            {movement(t, result.previous, finalLevel) && (
              <p className="text-xs text-lang-dark font-medium">
                {movement(t, result.previous, finalLevel)}
              </p>
            )}

            {/* Why this level, in one sentence: the rule that decided it. */}
            <p className="text-xs text-gray-500">
              {assessment
                ? t('placement.whyWithWriting', {
                    quiz: result.level ?? 'A1',
                    writing: assessment.level,
                    level: finalLevel,
                  })
                : t('placement.whyFromQuiz', {
                    level: finalLevel,
                    percent: Math.round(result.threshold * 100),
                  })}
            </p>

            {/* Per-level tally: the arithmetic behind that sentence. */}
            {Object.keys(result.perLevel).length > 0 && (
              <ul className="space-y-1" data-testid="placement-tally">
                {CEFR_ORDER.filter((lvl) => result.perLevel[lvl]).map((lvl) => {
                  const { correct, total } = result.perLevel[lvl]
                  const passed = total > 0 && correct / total >= result.threshold
                  return (
                    <li key={lvl} className="flex items-center gap-2 text-xs">
                      <span className="w-7 font-semibold text-gray-600">{lvl}</span>
                      <span className="flex-1 h-1.5 rounded-full bg-gray-100 overflow-hidden">
                        <span
                          className={`block h-full rounded-full ${passed ? 'bg-lang' : 'bg-gray-300'}`}
                          style={{ width: `${total ? (correct / total) * 100 : 0}%` }}
                        />
                      </span>
                      <span className="tabular-nums text-gray-500">
                        {correct}/{total}
                      </span>
                    </li>
                  )
                })}
              </ul>
            )}

            {/* And the questions themselves, one tap away. */}
            {result.breakdown.length > 0 && (
              <div>
                <button
                  type="button"
                  data-testid="placement-show-working"
                  onClick={() => setShowWorking((v) => !v)}
                  className="text-xs font-medium text-lang hover:underline"
                >
                  {showWorking
                    ? t('placement.hideAnswers')
                    : t('placement.showAnswers')}
                </button>
                {showWorking && (
                  <ul
                    className="mt-2 max-h-56 space-y-2 overflow-y-auto"
                    data-testid="placement-breakdown"
                  >
                    {result.breakdown.map((b, i) => (
                      <li
                        key={i}
                        className="rounded-lg border border-gray-100 bg-gray-50 p-2 text-xs"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <span className="text-gray-700">{b.prompt}</span>
                          <span className="shrink-0 text-[10px] text-gray-500">
                            {b.level}
                          </span>
                        </div>
                        <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1">
                          <span className={b.correct ? 'text-green-700' : 'text-red-600'}>
                            {b.correct ? '✓' : '✗'}
                          </span>
                          <LanguageWrapper languageCode={language.code}>
                            <span className="text-gray-800">
                              {b.typed || t('placement.noAnswer')}
                            </span>
                          </LanguageWrapper>
                          {/* Only correct an answer that was actually wrong —
                              telling somebody the "right" word when theirs was
                              also right is how a synonym reads as a mistake. */}
                          {!b.correct && b.verdict !== 'skipped' && (
                            <span className="text-gray-500">
                              {t('placement.expected', { answer: b.expected })}
                            </span>
                          )}
                          {b.verdict === 'synonym' && (
                            <span className="rounded bg-lang-soft px-1.5 py-0.5 text-[10px] text-lang-dark">
                              {t('placement.acceptedSynonym')}
                            </span>
                          )}
                          {b.verdict === 'typo' && (
                            <span className="rounded bg-lang-soft px-1.5 py-0.5 text-[10px] text-lang-dark">
                              {t('placement.acceptedTypo')}
                            </span>
                          )}
                          {b.verdict === 'skipped' && (
                            <span className="text-[10px] text-gray-500">
                              {t('placement.skipped')}
                            </span>
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            <p className="text-xs text-gray-500">
              {t('placement.applyHelp')}
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => apply.mutate(finalLevel)}
                disabled={apply.isPending}
                className="flex-1 rounded-xl bg-lang text-lang-on px-4 py-2.5 text-sm font-semibold hover:bg-lang-dark disabled:opacity-50"
                style={{ minHeight: '44px' }}
              >
                {apply.isPending
                  ? t('placement.settingUp')
                  : t('placement.setMeTo', { level: finalLevel })}
              </button>
              <button
                type="button"
                onClick={onClose}
                className="rounded-xl border border-gray-300 px-4 py-2.5 text-sm text-gray-600 hover:bg-gray-50"
                style={{ minHeight: '44px' }}
              >
                {t('placement.keepMyLevel')}
              </button>
            </div>
            {apply.isError && (
              <p className="text-xs text-red-500">
                {t('placement.applyError')}
              </p>
            )}
          </div>
        ) : showWriting ? (
          <div className="space-y-3" data-testid="placement-writing">
            <p className="text-sm font-semibold text-gray-800">
              {result
                ? t('placement.finalQuestion')
                : t('placement.writeParagraph', { language: languageDisplayName(language.code, language.name, i18n.language) })}
            </p>
            {/* An actual topic to write about (owner: "give a prompt and ask
                for a writing sample") — a blank box gets a blank answer. */}
            <p className="rounded-lg border border-lang/20 bg-lang-soft/50 px-3 py-2 text-sm text-gray-800">
              {t(`placement.prompts.${promptBand}`)}
            </p>
            <p className="text-xs text-gray-500">
              {t('placement.writingHelp')}
            </p>
            <LanguageWrapper languageCode={language.code}>
              <textarea
                value={sample}
                onChange={(e) => setSample(e.target.value)}
                maxLength={1500}
                rows={7}
                aria-label={t('placement.writingLabel', { language: languageDisplayName(language.code, language.name, i18n.language) })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-base"
              />
            </LanguageWrapper>
            <p className="text-end text-[11px] text-gray-500">
              {t('placement.wordCount', {
                count: sample.trim().split(/\s+/).filter(Boolean).length,
              })}
            </p>
            {assessment ? (
              <div className="rounded-lg bg-lang-soft p-3 space-y-2">
                <p className="text-sm text-gray-800">
                  <Trans
                    i18nKey="placement.writingVerdict"
                    values={{ level: assessment.level }}
                    components={{ b: <b /> }}
                  />
                </p>
                {assessment.notes && (
                  <p className="text-xs text-gray-600">{assessment.notes}</p>
                )}
                {assessment.focus.length > 0 && (
                  <p className="text-xs text-gray-600">
                    {t('placement.focusNext', { focus: assessment.focus.join('; ') })}
                  </p>
                )}
                <div className="flex gap-2 pt-1">
                  <button
                    type="button"
                    onClick={() => apply.mutate(assessment.level)}
                    disabled={apply.isPending}
                    className="flex-1 rounded-xl bg-lang px-4 py-2.5 text-sm font-semibold text-lang-on hover:bg-lang-dark disabled:opacity-50"
                    style={{ minHeight: '44px' }}
                  >
                    {apply.isPending
                      ? t('placement.settingUp')
                      : t('placement.setMeTo', { level: assessment.level })}
                  </button>
                  <button
                    type="button"
                    onClick={onClose}
                    className="rounded-xl border border-gray-300 px-4 py-2.5 text-sm text-gray-600 hover:bg-gray-50"
                    style={{ minHeight: '44px' }}
                  >
                    {t('placement.keepMyLevel')}
                  </button>
                </div>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => assess.mutate()}
                disabled={!sample.trim() || assess.isPending}
                className="w-full rounded-xl bg-lang px-4 py-2.5 text-sm font-semibold text-lang-on hover:bg-lang-dark disabled:opacity-40"
                style={{ minHeight: '44px' }}
              >
                {assess.isPending ? t('placement.readingIt') : t('placement.assessWriting')}
              </button>
            )}
            {assess.isError && (
              <p className="text-xs text-red-500">
                {t('placement.assessError')}
              </p>
            )}
            <button
              type="button"
              onClick={() =>
                result ? setSkippedWriting(true) : setWriting(false)
              }
              className="block w-full text-center text-xs text-gray-500 hover:text-lang"
            >
              {result
                ? t('placement.skipWriting')
                : t('placement.backToQuestions')}
            </button>
          </div>
        ) : item ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between gap-2">
              <h2 className="font-semibold text-gray-800">
                {t('placement.answerIn', { language: languageDisplayName(language.code, language.name, i18n.language) })}
              </h2>
              <span className="shrink-0 text-xs text-gray-500 tabular-nums">
                {history.length + 1} / {maxItems}
              </span>
            </div>
            <div className="rounded-xl border border-gray-100 bg-gray-50 p-3 space-y-2">
              {item.kind === 'grammar' ? (
                <LanguageWrapper languageCode={language.code}>
                  <p className="text-base text-gray-800">{item.prompt}</p>
                </LanguageWrapper>
              ) : (
                <p className="text-base text-gray-700">{item.prompt}</p>
              )}
              {item.translation && (
                <p className="text-xs text-gray-500">{item.translation}</p>
              )}
              <LanguageWrapper languageCode={language.code}>
                <form
                  onSubmit={(e) => {
                    e.preventDefault()
                    if (input.trim()) submit(input)
                  }}
                >
                  <input
                    ref={inputRef}
                    autoCapitalize="none"
                    autoCorrect="off"
                    autoComplete="off"
                    spellCheck={false}
                    enterKeyHint="go"
                    value={input}
                    onChange={(e) => {
                      const v = isTranslitEnabled(language.code, qwertyTranslit)
                        ? convertTranslit(language.code, e.target.value)
                        : e.target.value
                      setInput(v)
                    }}
                    onKeyDown={(e) => {
                      // IME-style Backspace: peel one jamo off a Hangul
                      // syllable (한 → 하) instead of deleting the block.
                      if (e.key !== 'Backspace' || e.nativeEvent.isComposing) return
                      const el = e.currentTarget
                      const peeled = backspaceUnit(
                        language.code,
                        input,
                        el.selectionStart ?? input.length,
                        el.selectionEnd ?? input.length,
                      )
                      if (peeled) {
                        e.preventDefault()
                        setInput(peeled.text)
                        requestAnimationFrame(() =>
                          el.setSelectionRange(peeled.caret, peeled.caret),
                        )
                      }
                    }}
                    aria-label={item.prompt}
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2.5 text-base"
                  />
                </form>
              </LanguageWrapper>
            </div>
            {hasKeyboardLayout(language.code) && (
              <div className="space-y-2">
                <div className="flex justify-end">
                  <button
                    type="button"
                    onClick={() => setShowKeyboard((v) => !v)}
                    className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs text-gray-500 hover:text-gray-700"
                    style={{ minHeight: '44px' }}
                  >
                    {showKeyboard ? t('placement.hideKeyboard') : t('placement.showKeyboard')}
                  </button>
                </div>
                {showKeyboard && (
                  <OnScreenKeyboard
                    languageCode={language.code as KeyboardLanguage}
                    // composeScript fuses Hangul jamo into blocks (ᄒ+ᅡ → 하);
                    // raw appends left the jamo sitting loose beside each
                    // other. Backspace peels one jamo, IME-style.
                    onKeyPress={(key) =>
                      setInput((v) => composeScript(language.code, v + key))
                    }
                    onEnter={() => input.trim() && submit(input)}
                    onBackspace={() =>
                      setInput((v) => deleteLastUnit(language.code, v))
                    }
                  />
                )}
              </div>
            )}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => submit(input)}
                disabled={!input.trim() || next.isPending}
                className="flex-1 rounded-xl bg-lang text-lang-on px-5 py-2.5 text-sm font-semibold hover:bg-lang-dark disabled:opacity-50"
                style={{ minHeight: '44px' }}
              >
                {next.isPending ? t('placement.checking') : t('placement.next')}
              </button>
              <button
                type="button"
                onClick={() => submit('')}
                disabled={next.isPending}
                className="rounded-xl border border-gray-300 px-4 py-2.5 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-50"
                style={{ minHeight: '44px' }}
              >
                {t('placement.dontKnow')}
              </button>
            </div>
            {writingOffer?.available && (
              <button
                type="button"
                onClick={() => setWriting(true)}
                className="block w-full text-center text-xs text-lang hover:underline"
              >
                {t('placement.ratherWrite')}
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              className="block w-full text-center text-xs text-gray-500 hover:text-lang"
            >
              {t('placement.stopTest')}
            </button>
          </div>
        ) : next.isError ? (
          // A modal with no way out is a trap. The first version rendered
          // this message alone, so a failed start left the learner stuck
          // behind an overlay with nothing to press (owner report).
          <div className="space-y-3">
            <p className="text-sm font-semibold text-gray-800">
              {t('placement.startErrorTitle')}
            </p>
            <p className="text-xs text-gray-500">
              {cause ?? t('placement.startErrorHelp')}
            </p>
            {cause && (
              <p className="text-[11px] text-gray-500">
                {t('placement.migrationNote')}
              </p>
            )}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => next.mutate([])}
                className="flex-1 rounded-xl bg-lang px-4 py-2.5 text-sm font-semibold text-lang-on hover:bg-lang-dark"
                style={{ minHeight: '44px' }}
              >
                {t('placement.tryAgain')}
              </button>
              <button
                type="button"
                onClick={onClose}
                className="rounded-xl border border-gray-300 px-4 py-2.5 text-sm text-gray-600 hover:bg-gray-50"
                style={{ minHeight: '44px' }}
              >
                {t('placement.close')}
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="py-4 text-center text-sm text-gray-500">{t('common.loading')}</p>
            {/* Escapable while loading too — a hung request must not trap. */}
            <button
              type="button"
              onClick={onClose}
              className="block w-full text-center text-xs text-gray-500 hover:text-lang"
            >
              {t('placement.cancel')}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
