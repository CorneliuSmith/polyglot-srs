import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Trans, useTranslation } from 'react-i18next'
import { useQuery, useMutation } from '@tanstack/react-query'
import { getLanguages } from '../../api/profile'
import {
  assessWritingSample,
  completeOnboarding,
  getOnboardingStatus,
  getWritingAvailability,
  placementNext,
} from '../../api/onboarding'
import type { PlacementItem, WritingAssessment } from '../../api/onboarding'
import { chooseActiveLanguage } from '../../lib/activeLanguage'
import { usePrefsStore } from '../../stores/prefsStore'
import AiDisclaimer from '../../components/AiDisclaimer'
import DirArrow from '../../components/DirArrow'
import LanguageWrapper from '../../components/LanguageWrapper'
import {
  getPlanPrices,
  optionPurchasable,
  startPlanCheckout,
  type PlanOption,
} from '../../api/billing'
import PlanPicker, { DEFAULT_OPTION } from '../billing/PlanPicker'
import { languageDisplayName, visibleLanguages } from '../../lib/languages'
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
  const { t, i18n } = useTranslation()
  const qwertyTranslit = usePrefsStore((s) => s.qwertyTranslit)
  const dismissPlacementOffer = usePrefsStore((s) => s.dismissPlacementOffer)

  const [step, setStep] = useState<Step>('language')
  const [language, setLanguage] = useState<Language | null>(null)
  // Adaptive placement: the answered history so far, the item on screen,
  // and the input being typed. The server re-walks the history each round.
  const [history, setHistory] = useState<{ id: string; input: string }[]>([])
  const [currentItem, setCurrentItem] = useState<PlacementItem | null>(null)
  const [curInput, setCurInput] = useState('')
  const [maxItems, setMaxItems] = useState(12)
  const [level, setLevel] = useState('A1')
  // The four options, recommended one preselected (owner: "Single language
  // with AI should be the default").
  const [option, setOption] = useState<PlanOption>(DEFAULT_OPTION)
  // Optional writing baseline (owner request): write a sentence or two "to
  // the best of your ability" and one small model call suggests the level.
  // Offered only when the server says so (entitled accounts / testing).
  const [sample, setSample] = useState('')
  const [assessment, setAssessment] = useState<WritingAssessment | null>(null)
  const { data: writingOffer } = useQuery({
    queryKey: ['writing-availability', language?.id],
    queryFn: () => getWritingAvailability(language!.id),
    enabled: !!language,
    retry: false,
  })
  const assessMutation = useMutation({
    mutationFn: () =>
      assessWritingSample(language!.id, language!.code, sample.trim()),
    onSuccess: (res) => setAssessment(res),
  })
  // Live Stripe prices (never hardcoded); null until billing is configured.
  const { data: planPrices } = useQuery({
    queryKey: ['plan-prices'],
    queryFn: getPlanPrices,
    staleTime: Infinity,
  })
  // Monetization off: the step is a pure SCOPE choice (which languages you
  // want) — prices already come back null, and the billing note is hidden
  // so nothing on the screen mentions payment.
  const monetization = planPrices?.monetization === true

  const { data: allLanguages = [] } = useQuery({ queryKey: ['languages'], queryFn: getLanguages })
  // A language an admin has hidden doesn't offer itself to new learners.
  const languages = visibleLanguages(allLanguages)

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

  // Turning the test down here counts as an answer: the dashboard's
  // first-time-in-this-language offer must not pop up seconds later asking
  // the same question.
  const declineTest = () => {
    if (language) dismissPlacementOffer(language.id)
    setLevel('A1')
    setStep('confirm')
  }

  const finishMutation = useMutation({
    mutationFn: async () => {
      await completeOnboarding({
        languageId: language!.id, level, planScope: option.scope,
      })
      // Money on and this option priced: the plan is BOUGHT, not declared.
      // The server records only what the webhook confirms (an abandoned
      // Checkout leaves nothing behind); dev-mock grants at once and
      // returns no URL, so the flow continues into the app.
      if (optionPurchasable(planPrices, option)) {
        const res = await startPlanCheckout(option.scope, language!.id, option.ai)
        if (res.url) return res.url
      }
      return null
    },
    onSuccess: (checkoutUrl) => {
      // completeOnboarding already wrote the course to the account; this
      // sets the device AND opens the grace window, so a profile read that
      // started before the write can't bounce an existing user who just
      // onboarded a second course back to their old one.
      chooseActiveLanguage(language!.id)
      if (checkoutUrl) {
        window.location.assign(checkoutUrl)
        return
      }
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
              aria-label={t('onboarding.back')}
              className="shrink-0 w-9 h-9 flex items-center justify-center rounded-full border border-gray-200 text-gray-500 disabled:opacity-0 hover:bg-gray-50 active:bg-gray-100"
            >
              <DirArrow dir="back" />
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
              {t('onboarding.title')}
            </h1>
            <p className="text-sm text-gray-500">
              {t('onboarding.subtitle')}
            </p>
          </div>
        </header>

        {step === 'language' && (
          <section className="space-y-3">
            <h2 className="font-semibold text-gray-800">{t('onboarding.whichLanguage')}</h2>
            <div className="grid grid-cols-2 gap-3">
              {languages.map((lang) => (
                <button
                  key={lang.id}
                  type="button"
                  onClick={() => pickLanguage(lang)}
                  className="min-h-12 rounded-xl border border-gray-200 bg-white px-4 py-3 text-start text-sm font-medium text-gray-800 break-words hover:border-lang/50 hover:bg-lang-soft active:bg-lang-soft"
                >
                  {languageDisplayName(lang.code, lang.name, i18n.language)}
                </button>
              ))}
            </div>
          </section>
        )}

        {step === 'method' && language && (
          <section className="space-y-3">
            <h2 className="font-semibold text-gray-800">
              {t('onboarding.howMuch', { language: languageDisplayName(language.code, language.name, i18n.language) })}
            </h2>
            {/* Three clear paths — the test is one option, never a gate. */}
            <button
              type="button"
              onClick={declineTest}
              className="w-full min-h-12 rounded-xl border border-gray-200 bg-white px-4 py-3 text-start hover:border-lang/50 hover:bg-lang-soft active:bg-lang-soft"
            >
              <span className="block text-sm font-semibold text-gray-800">{t('onboarding.brandNew')}</span>
              <span className="block text-xs text-gray-500">{t('onboarding.brandNewSub')}</span>
            </button>
            <button
              type="button"
              onClick={declineTest}
              className="w-full min-h-12 rounded-xl border border-gray-200 bg-white px-4 py-3 text-start hover:border-lang/50 hover:bg-lang-soft active:bg-lang-soft"
            >
              <span className="block text-sm font-semibold text-gray-800">
                {t('onboarding.knowSome')}
              </span>
              <span className="block text-xs text-gray-500">
                {t('onboarding.knowSomeSub')}
              </span>
            </button>
            <button
              type="button"
              onClick={startPlacement}
              disabled={nextMutation.isPending}
              className="w-full min-h-12 rounded-xl border border-gray-200 bg-white px-4 py-3 text-start hover:border-lang/50 hover:bg-lang-soft active:bg-lang-soft disabled:opacity-50"
            >
              <span className="block text-sm font-semibold text-gray-800">
                {nextMutation.isPending ? t('common.loading') : t('onboarding.testMyLevel')}
              </span>
              <span className="block text-xs text-gray-500">
                {t('onboarding.testMyLevelSub')}
              </span>
            </button>
          </section>
        )}

        {step === 'placement' && language && currentItem && (
          <section className="space-y-4">
            <div className="flex items-center justify-between gap-2">
              <h2 className="font-semibold text-gray-800">
                {t('placement.answerIn', { language: languageDisplayName(language.code, language.name, i18n.language) })}
              </h2>
              <span className="shrink-0 text-xs text-gray-500 tabular-nums">
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
                <p className="text-xs text-gray-500">{currentItem.translation}</p>
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
                {nextMutation.isPending ? t('placement.checking') : t('placement.next')}
              </button>
              <button
                type="button"
                onClick={() => submitAnswer('')}
                disabled={nextMutation.isPending}
                className="min-h-12 rounded-xl border border-gray-300 px-5 text-sm text-gray-600 hover:bg-gray-50 active:bg-gray-100 disabled:opacity-50"
              >
                {t('placement.dontKnow')}
              </button>
            </div>
            {/* Escape hatch: the test is never a trap. */}
            <button
              type="button"
              onClick={declineTest}
              className="block w-full text-center text-xs text-gray-500 hover:text-lang"
            >
              {t('onboarding.skipTest')}
            </button>
          </section>
        )}

        {step === 'confirm' && language && (
          <section className="space-y-4">
            <h2 className="font-semibold text-gray-800">{t('onboarding.startAtLevel', { language: languageDisplayName(language.code, language.name, i18n.language) })}</h2>
            <p className="text-sm text-gray-500">
              {t('onboarding.confirmHelp')}
            </p>
            <select
              value={level}
              onChange={(e) => setLevel(e.target.value)}
              aria-label={t('onboarding.startingLevelLabel')}
              className="w-full min-h-12 rounded-lg border border-gray-300 px-3 py-2 text-base bg-white"
            >
              {CEFR_LEVELS.map((l) => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>

            {/* Optional writing baseline: a sentence of real production beats
                multiple choice. Only offered when the server allows the model
                call (entitled accounts / testing) — the token guard. */}
            {writingOffer?.available && (
              <div
                className="rounded-xl border border-gray-200 bg-white p-3 space-y-2"
                data-testid="writing-baseline"
              >
                <p className="text-sm font-medium text-gray-800">
                  {t('onboarding.writingTitle', { language: languageDisplayName(language.code, language.name, i18n.language) })}
                </p>
                <p className="text-xs text-gray-500">
                  {t('onboarding.writingHelp')}
                </p>
                <LanguageWrapper languageCode={language.code}>
                  <textarea
                    value={sample}
                    onChange={(e) => setSample(e.target.value)}
                    maxLength={500}
                    rows={3}
                    aria-label={t('onboarding.writingSampleLabel')}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-base"
                  />
                </LanguageWrapper>
                <button
                  type="button"
                  onClick={() => assessMutation.mutate()}
                  disabled={!sample.trim() || assessMutation.isPending}
                  className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                  style={{ minHeight: '44px' }}
                >
                  {assessMutation.isPending ? t('placement.readingIt') : t('onboarding.suggestMyLevel')}
                </button>
                {assessMutation.isError && (
                  <p className="text-xs text-red-500">
                    {t('onboarding.assessError')}
                  </p>
                )}
                {assessment && (
                  <div
                    className="rounded-lg bg-lang-soft p-3 space-y-1.5"
                    data-testid="writing-verdict"
                  >
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
                    <AiDisclaimer />
                    {assessment.level !== level && (
                      <button
                        type="button"
                        onClick={() => setLevel(assessment.level)}
                        className="rounded-lg bg-lang hover:bg-lang-dark text-lang-on px-3 py-1.5 text-xs font-semibold"
                      >
                        {t('onboarding.startAtSuggested', { level: assessment.level })}
                      </button>
                    )}
                  </div>
                )}
              </div>
            )}

            <button
              type="button"
              onClick={() => setStep('plan')}
              className="w-full min-h-12 bg-lang hover:bg-lang-dark active:bg-lang-dark disabled:opacity-50 text-lang-on font-semibold rounded-xl px-6 text-sm"
            >
              {t('onboarding.continue')}
            </button>
          </section>
        )}

        {step === 'plan' && language && (
          <section className="space-y-4">
            <h2 className="font-semibold text-gray-800">{t('plans.title')}</h2>
            <p className="text-sm text-gray-500">{t('plans.help')}</p>
            <PlanPicker
              languageName={languageDisplayName(language.code, language.name, i18n.language)}
              prices={planPrices}
              value={option}
              onChange={setOption}
            />
            <p className="text-xs text-gray-500">{t('plans.changeHint')}</p>
            {monetization && !optionPurchasable(planPrices, option) && (
              <p className="text-xs text-gray-500">
                {t('onboarding.billingNote')}
              </p>
            )}
            <button
              type="button"
              onClick={() => finishMutation.mutate()}
              disabled={finishMutation.isPending}
              className="w-full min-h-12 bg-lang hover:bg-lang-dark active:bg-lang-dark disabled:opacity-50 text-lang-on font-semibold rounded-xl px-6 text-sm"
            >
              {finishMutation.isPending ? t('placement.settingUp') : t('onboarding.startLearning')}
            </button>
          </section>
        )}
      </div>
    </div>
  )
}
