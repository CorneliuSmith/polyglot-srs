import { useEffect, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { placementNext, setLearnerLevel } from '../../api/onboarding'
import { getSchemaHealth, pendingMigrationNote } from '../../api/health'
import type { PlacementItem } from '../../api/onboarding'
import LanguageWrapper from '../../components/LanguageWrapper'
import { usePrefsStore } from '../../stores/prefsStore'
import { convertTranslit, finalizeInput, isTranslitEnabled } from '../keyboards/translit'
import OnScreenKeyboard, { hasKeyboardLayout } from '../keyboards/OnScreenKeyboard'
import type { KeyboardLanguage } from '../keyboards/OnScreenKeyboard'
import type { Language } from '../../api/types'

const CEFR_ORDER = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']

/** "up two levels" / "the same level" / "down one" — how a retake compares
 * to the last one, which is the whole reason the retake exists. */
function movement(previous: string | null | undefined, now: string): string | null {
  if (!previous) return null
  const from = CEFR_ORDER.indexOf(previous)
  const to = CEFR_ORDER.indexOf(now)
  if (from < 0 || to < 0) return null
  const step = to - from
  if (step === 0) return `Same as last time (${previous}).`
  const n = Math.abs(step)
  const levels = n === 1 ? 'one level' : `${n} levels`
  return step > 0
    ? `That's ${levels} up from ${previous} — nice work.`
    : `That's ${levels} below your last result (${previous}).`
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
  const qwertyTranslit = usePrefsStore((s) => s.qwertyTranslit)

  const [history, setHistory] = useState<{ id: string; input: string }[]>([])
  const [item, setItem] = useState<PlacementItem | null>(null)
  const [input, setInput] = useState('')
  const [maxItems, setMaxItems] = useState(12)
  const [result, setResult] = useState<
    { level: string | null; previous: string | null; asked: number } | null
  >(null)
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
      aria-label={`${language.name} placement test`}
      data-testid="placement-test"
    >
      <div className="w-full max-w-md rounded-2xl bg-white p-5 shadow-xl space-y-4">
        {unavailable ? (
          <div className="space-y-3">
            <p className="text-sm font-semibold text-gray-800">
              Not enough {language.name} content to test yet
            </p>
            <p className="text-xs text-gray-500">
              We&apos;ll offer this again once the course has grown. Pick your
              level in Settings &rarr; Your level in the meantime.
            </p>
            <button
              type="button"
              onClick={onClose}
              className="w-full rounded-xl bg-lang text-lang-on px-4 py-2.5 text-sm font-semibold hover:bg-lang-dark"
              style={{ minHeight: '44px' }}
            >
              Close
            </button>
          </div>
        ) : result ? (
          <div className="space-y-3" data-testid="placement-result">
            <p className="text-sm text-gray-800">
              Your {language.name} looks about{' '}
              <b>{result.level ?? 'A1'}</b>, from {result.asked}{' '}
              {result.asked === 1 ? 'question' : 'questions'}.
            </p>
            {result.level && movement(result.previous, result.level) && (
              <p className="text-xs text-lang-dark font-medium">
                {movement(result.previous, result.level)}
              </p>
            )}
            <p className="text-xs text-gray-500">
              Setting this queues grammar and vocabulary at that level and
              below. Cards you&apos;ve already learned are never removed.
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => apply.mutate(result.level ?? 'A1')}
                disabled={apply.isPending}
                className="flex-1 rounded-xl bg-lang text-lang-on px-4 py-2.5 text-sm font-semibold hover:bg-lang-dark disabled:opacity-50"
                style={{ minHeight: '44px' }}
              >
                {apply.isPending
                  ? 'Setting up…'
                  : `Set me to ${result.level ?? 'A1'}`}
              </button>
              <button
                type="button"
                onClick={onClose}
                className="rounded-xl border border-gray-300 px-4 py-2.5 text-sm text-gray-600 hover:bg-gray-50"
                style={{ minHeight: '44px' }}
              >
                Keep my level
              </button>
            </div>
            {apply.isError && (
              <p className="text-xs text-red-500">
                Couldn&apos;t change your level — try Settings &rarr; Your level.
              </p>
            )}
          </div>
        ) : item ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between gap-2">
              <h2 className="font-semibold text-gray-800">
                Answer in {language.name}
              </h2>
              <span className="shrink-0 text-xs text-gray-400 tabular-nums">
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
                <p className="text-xs text-gray-400">{item.translation}</p>
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
                    {showKeyboard ? 'Hide keyboard' : 'Show keyboard'}
                  </button>
                </div>
                {showKeyboard && (
                  <OnScreenKeyboard
                    languageCode={language.code as KeyboardLanguage}
                    onKeyPress={(key) => setInput((v) => v + key)}
                    onEnter={() => input.trim() && submit(input)}
                    onBackspace={() => setInput((v) => v.slice(0, -1))}
                    inputRef={inputRef}
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
                {next.isPending ? 'Checking…' : 'Next'}
              </button>
              <button
                type="button"
                onClick={() => submit('')}
                disabled={next.isPending}
                className="rounded-xl border border-gray-300 px-4 py-2.5 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-50"
                style={{ minHeight: '44px' }}
              >
                I don&apos;t know
              </button>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="block w-full text-center text-xs text-gray-400 hover:text-lang"
            >
              Stop the test
            </button>
          </div>
        ) : next.isError ? (
          // A modal with no way out is a trap. The first version rendered
          // this message alone, so a failed start left the learner stuck
          // behind an overlay with nothing to press (owner report).
          <div className="space-y-3">
            <p className="text-sm font-semibold text-gray-800">
              Couldn&apos;t start the test
            </p>
            <p className="text-xs text-gray-500">
              {cause ??
                'Something went wrong reaching the server. You can pick your level by hand above, and try the test again later.'}
            </p>
            {cause && (
              <p className="text-[11px] text-gray-400">
                Your level can still be set by hand above. This clears once the
                pending migrations are applied.
              </p>
            )}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => next.mutate([])}
                className="flex-1 rounded-xl bg-lang px-4 py-2.5 text-sm font-semibold text-lang-on hover:bg-lang-dark"
                style={{ minHeight: '44px' }}
              >
                Try again
              </button>
              <button
                type="button"
                onClick={onClose}
                className="rounded-xl border border-gray-300 px-4 py-2.5 text-sm text-gray-600 hover:bg-gray-50"
                style={{ minHeight: '44px' }}
              >
                Close
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="py-4 text-center text-sm text-gray-500">Loading…</p>
            {/* Escapable while loading too — a hung request must not trap. */}
            <button
              type="button"
              onClick={onClose}
              className="block w-full text-center text-xs text-gray-400 hover:text-lang"
            >
              Cancel
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
