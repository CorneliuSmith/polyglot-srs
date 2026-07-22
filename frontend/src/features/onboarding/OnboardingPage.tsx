import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { getLanguages } from '../../api/profile'
import {
  completeOnboarding,
  getOnboardingStatus,
  placementNext,
} from '../../api/onboarding'
import type { PlacementItem } from '../../api/onboarding'
import { usePrefsStore } from '../../stores/prefsStore'
import LanguageWrapper from '../../components/LanguageWrapper'
import { formatPrice, getPlanPrices } from '../../api/billing'
import { convertTranslit, finalizeInput, isTranslitEnabled } from '../keyboards/translit'
import type { Language } from '../../api/types'

type Step = 'language' | 'method' | 'placement' | 'confirm' | 'plan'

const CEFR_LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'] as const

// Four visible stages for the progress bar (placement and confirm share the
// "level" stage — the learner is settling on a level either way).
const STAGE_OF: Record<Step, number> = {
  language: 0,
  method: 1,
  placement: 2,
  confirm: 2,
  plan: 3,
}
const STAGES = 4

export default function OnboardingPage() {
  const navigate = useNavigate()
  const setActiveLanguageId = usePrefsStore((s) => s.setActiveLanguageId)
  const qwertyTranslit = usePrefsStore((s) => s.qwertyTranslit)

  const [step, setStep] = useState<Step>('language')
  const [language, setLanguage] = useState<Language | null>(null)
  // Adaptive placement: the answered history so far, the item on screen,
  // and the input being typed. The server re-walks the history each round.
  const [history, setHistory] = useState<{ id: string; input: string }[]>([])
  const [currentItem, setCurrentItem] = useState<PlacementItem | null>(null)
  const [curInput, setCurInput] = useState('')
  const [maxItems, setMaxItems] = useState(12)
  const [level, setLevel] = useState('A1')
  const [planScope, setPlanScope] = useState<'single' | 'all'>('single')
  // Live Stripe prices (never hardcoded); null until billing is configured.
  const { data: planPrices } = useQuery({
    queryKey: ['plan-prices'],
    queryFn: getPlanPrices,
    staleTime: Infinity,
  })
  const singlePrice = formatPrice(planPrices?.single ?? null)
  const allPrice = formatPrice(planPrices?.all ?? null)

  const { data: languages = [] } = useQuery({ queryKey: ['languages'], queryFn: getLanguages })

  // Skip onboarding entirely if the user has already finished it. Done in an
  // effect, never during render — navigating mid-render warns and can wedge
  // the page (part of the "options not working" report).
  const { data: statusData } = useQuery({ queryKey: ['onboarding-status'], queryFn: getOnboardingStatus })
  useEffect(() => {
    if (statusData?.onboarded) navigate('/', { replace: true })
  }, [statusData?.onboarded, navigate])

  const nextMutation = useMutation({
    mutationFn: (h: { id: string; input: string }[]) =>
      placementNext(language!.id, h),
    onSuccess: (res) => {
      if (!res.available) {
        // Not enough graded content to test — let the learner self-report.
        setStep('confirm')
        return
      }
      if (res.done) {
        setLevel(res.estimated_level ?? 'A1')
        setStep('confirm')
        return
      }
      setCurrentItem(res.item ?? null)
      setCurInput('')
      if (res.max_items) setMaxItems(res.max_items)
      setStep('placement')
    },
  })

  const submitAnswer = (input: string) => {
    if (!currentItem || !language || nextMutation.isPending) return
    const finalized = finalizeInput(language.code, input.trim(), qwertyTranslit)
    const newHistory = [...history, { id: currentItem.id, input: finalized }]
    setHistory(newHistory)
    nextMutation.mutate(newHistory)
  }

  const startPlacement = () => {
    setHistory([])
    setCurrentItem(null)
    nextMutation.mutate([])
  }

  const finishMutation = useMutation({
    mutationFn: () =>
      completeOnboarding({ languageId: language!.id, level, planScope }),
    onSuccess: () => {
      setActiveLanguageId(language!.id)
      // Land on the toolkit walkthrough, not the bare dashboard — new
      // accounts had no idea the tutor/reader/letters existed.
      navigate('/welcome', { replace: true })
    },
  })

  function pickLanguage(lang: Language) {
    setLanguage(lang)
    setStep('method')
  }

  // Back always walks one stage toward the start, so the flow never feels
  // like a one-way trap.
  const goBack = () => {
    if (step === 'method') setStep('language')
    else if (step === 'placement' || step === 'confirm') setStep('method')
    else if (step === 'plan') setStep('confirm')
  }

  const stage = STAGE_OF[step]

  return (
    <div className="min-h-screen bg-gray-50 overflow-x-hidden">
      <div className="max-w-xl mx-auto px-4 py-8 space-y-6">
        <header className="space-y-4">
          {/* Back + progress: a clear way out of every step. */}
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={goBack}
              disabled={step === 'language'}
              aria-label="Back"
              className="shrink-0 w-9 h-9 flex items-center justify-center rounded-full border border-gray-200 text-gray-500 disabled:opacity-0 hover:bg-gray-50 active:bg-gray-100"
            >
              <span aria-hidden>←</span>
            </button>
            <div
              className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden"
              role="progressbar"
              aria-valuenow={stage + 1}
              aria-valuemin={1}
              aria-valuemax={STAGES}
            >
              <div
                className="h-full bg-lang rounded-full transition-[width] duration-300"
                style={{ width: `${((stage + 1) / STAGES) * 100}%` }}
              />
            </div>
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Welcome — let&apos;s set you up
            </h1>
            <p className="text-sm text-gray-500">
              A minute now and your reviews are ready to go.
            </p>
          </div>
        </header>

        {step === 'language' && (
          <section className="space-y-3">
            <h2 className="font-semibold text-gray-800">Which language do you want to learn?</h2>
            <div className="grid grid-cols-2 gap-3">
              {languages.map((lang) => (
                <button
                  key={lang.id}
                  type="button"
                  onClick={() => pickLanguage(lang)}
                  className="min-h-12 rounded-xl border border-gray-200 bg-white px-4 py-3 text-left text-sm font-medium text-gray-800 break-words hover:border-lang/50 hover:bg-lang-soft active:bg-lang-soft"
                >
                  {lang.name}
                </button>
              ))}
            </div>
          </section>
        )}

        {step === 'method' && language && (
          <section className="space-y-3">
            <h2 className="font-semibold text-gray-800">
              How much {language.name} do you already know?
            </h2>
            {/* Three clear paths — the test is one option, never a gate. */}
            <button
              type="button"
              onClick={() => {
                setLevel('A1')
                setStep('confirm')
              }}
              className="w-full min-h-12 rounded-xl border border-gray-200 bg-white px-4 py-3 text-left hover:border-lang/50 hover:bg-lang-soft active:bg-lang-soft"
            >
              <span className="block text-sm font-semibold text-gray-800">I&apos;m brand new</span>
              <span className="block text-xs text-gray-500">Start from the beginning (A1)</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setLevel('A1')
                setStep('confirm')
              }}
              className="w-full min-h-12 rounded-xl border border-gray-200 bg-white px-4 py-3 text-left hover:border-lang/50 hover:bg-lang-soft active:bg-lang-soft"
            >
              <span className="block text-sm font-semibold text-gray-800">
                I know some — I&apos;ll pick my level
              </span>
              <span className="block text-xs text-gray-500">
                Choose your starting level yourself, no test
              </span>
            </button>
            <button
              type="button"
              onClick={startPlacement}
              disabled={nextMutation.isPending}
              className="w-full min-h-12 rounded-xl border border-gray-200 bg-white px-4 py-3 text-left hover:border-lang/50 hover:bg-lang-soft active:bg-lang-soft disabled:opacity-50"
            >
              <span className="block text-sm font-semibold text-gray-800">
                {nextMutation.isPending ? 'Loading…' : 'Test my level (optional)'}
              </span>
              <span className="block text-xs text-gray-500">
                A few questions that adapt to your answers — most finish in 5–8
              </span>
            </button>
          </section>
        )}

        {step === 'placement' && language && currentItem && (
          <section className="space-y-4">
            <div className="flex items-center justify-between gap-2">
              <h2 className="font-semibold text-gray-800">
                Answer in {language.name}
              </h2>
              <span className="shrink-0 text-xs text-gray-400 tabular-nums">
                {history.length + 1} / {maxItems}
              </span>
            </div>
            <div className="rounded-xl border border-gray-100 bg-white p-4 space-y-2">
              {currentItem.kind === 'grammar' ? (
                <LanguageWrapper languageCode={language.code}>
                  <p className="text-base text-gray-800">{currentItem.prompt}</p>
                </LanguageWrapper>
              ) : (
                <p className="text-base text-gray-700">{currentItem.prompt}</p>
              )}
              {currentItem.translation && (
                <p className="text-xs text-gray-400">{currentItem.translation}</p>
              )}
              <LanguageWrapper languageCode={language.code}>
                {/* Real form: some Android IMEs never emit a usable Enter
                    keydown, but the action key always submits a form. No
                    autoFocus — on phones it springs the keyboard open and
                    scrolls the page out from under the learner. */}
                <form
                  onSubmit={(e) => {
                    e.preventDefault()
                    if (curInput.trim()) submitAnswer(curInput)
                  }}
                >
                  <input
                    autoCapitalize="none"
                    autoCorrect="off"
                    autoComplete="off"
                    spellCheck={false}
                    enterKeyHint="go"
                    value={curInput}
                    onChange={(e) => {
                      const v = isTranslitEnabled(language.code, qwertyTranslit)
                        ? convertTranslit(language.code, e.target.value)
                        : e.target.value
                      setCurInput(v)
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.nativeEvent.isComposing && curInput.trim()) {
                        e.preventDefault()
                        submitAnswer(curInput)
                      }
                    }}
                    aria-label={currentItem.prompt}
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2.5 text-base"
                  />
                </form>
              </LanguageWrapper>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => submitAnswer(curInput)}
                disabled={!curInput.trim() || nextMutation.isPending}
                className="flex-1 min-h-12 bg-lang hover:bg-lang-dark active:bg-lang-dark disabled:opacity-50 text-lang-on font-semibold rounded-xl px-5 text-sm"
              >
                {nextMutation.isPending ? 'Checking…' : 'Next'}
              </button>
              <button
                type="button"
                onClick={() => submitAnswer('')}
                disabled={nextMutation.isPending}
                className="min-h-12 rounded-xl border border-gray-300 px-5 text-sm text-gray-600 hover:bg-gray-50 active:bg-gray-100 disabled:opacity-50"
              >
                I don&apos;t know
              </button>
            </div>
            {/* Escape hatch: the test is never a trap. */}
            <button
              type="button"
              onClick={() => {
                setLevel('A1')
                setStep('confirm')
              }}
              className="block w-full text-center text-xs text-gray-400 hover:text-lang"
            >
              Skip the test — I&apos;ll pick my level
            </button>
          </section>
        )}

        {step === 'confirm' && language && (
          <section className="space-y-4">
            <h2 className="font-semibold text-gray-800">Start {language.name} at this level</h2>
            <p className="text-sm text-gray-500">
              We&apos;ll queue grammar and vocabulary at this level and below. You can change it later.
            </p>
            <select
              value={level}
              onChange={(e) => setLevel(e.target.value)}
              aria-label="Starting level"
              className="w-full min-h-12 rounded-lg border border-gray-300 px-3 py-2 text-base bg-white"
            >
              {CEFR_LEVELS.map((l) => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => setStep('plan')}
              className="w-full min-h-12 bg-lang hover:bg-lang-dark active:bg-lang-dark disabled:opacity-50 text-lang-on font-semibold rounded-xl px-6 text-sm"
            >
              Continue
            </button>
          </section>
        )}

        {step === 'plan' && language && (
          <section className="space-y-4">
            <h2 className="font-semibold text-gray-800">Choose your plan</h2>
            <p className="text-sm text-gray-500">
              Study just {language.name}, or unlock every language. You can
              upgrade any time in Settings.
            </p>
            <button
              type="button"
              onClick={() => setPlanScope('single')}
              aria-pressed={planScope === 'single'}
              className={
                'w-full min-h-12 rounded-xl border px-4 py-3 text-left active:bg-lang-soft ' +
                (planScope === 'single'
                  ? 'border-lang bg-lang-soft'
                  : 'border-gray-200 bg-white hover:border-lang/50')
              }
            >
              <span className="block text-sm font-semibold text-gray-800">
                {language.name} only
              </span>
              <span className="block text-xs text-gray-500">
                {singlePrice
                  ? `One language — ${singlePrice}`
                  : 'One language at the lower price'}
              </span>
            </button>
            <button
              type="button"
              onClick={() => setPlanScope('all')}
              aria-pressed={planScope === 'all'}
              className={
                'w-full min-h-12 rounded-xl border px-4 py-3 text-left active:bg-lang-soft ' +
                (planScope === 'all'
                  ? 'border-lang bg-lang-soft'
                  : 'border-gray-200 bg-white hover:border-lang/50')
              }
            >
              <span className="block text-sm font-semibold text-gray-800">
                All languages
              </span>
              <span className="block text-xs text-gray-500">
                {allPrice
                  ? `Every language we offer — ${allPrice}`
                  : 'Every language we offer, one price'}
              </span>
            </button>
            <p className="text-xs text-gray-400">
              Billing hasn&apos;t launched yet — early accounts keep full access to
              their choice for free, and keep their price when plans go live.
            </p>
            <button
              type="button"
              onClick={() => finishMutation.mutate()}
              disabled={finishMutation.isPending}
              className="w-full min-h-12 bg-lang hover:bg-lang-dark active:bg-lang-dark disabled:opacity-50 text-lang-on font-semibold rounded-xl px-6 text-sm"
            >
              {finishMutation.isPending ? 'Setting up…' : 'Start learning'}
            </button>
          </section>
        )}
      </div>
    </div>
  )
}
