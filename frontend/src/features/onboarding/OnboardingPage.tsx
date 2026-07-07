import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { getLanguages } from '../../api/profile'
import {
  completeOnboarding,
  getOnboardingStatus,
  getPlacement,
  scorePlacement,
} from '../../api/onboarding'
import type { PlacementItem } from '../../api/onboarding'
import { usePrefsStore } from '../../stores/prefsStore'
import LanguageWrapper from '../../components/LanguageWrapper'
import { convertTranslit, finalizeInput, isTranslitEnabled } from '../keyboards/translit'
import type { Language } from '../../api/types'

type Step = 'language' | 'method' | 'placement' | 'confirm'

const CEFR_LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'] as const

export default function OnboardingPage() {
  const navigate = useNavigate()
  const setActiveLanguageId = usePrefsStore((s) => s.setActiveLanguageId)
  const qwertyTranslit = usePrefsStore((s) => s.qwertyTranslit)

  const [step, setStep] = useState<Step>('language')
  const [language, setLanguage] = useState<Language | null>(null)
  const [items, setItems] = useState<PlacementItem[]>([])
  const [responses, setResponses] = useState<Record<string, string>>({})
  const [level, setLevel] = useState('A1')

  const { data: languages = [] } = useQuery({ queryKey: ['languages'], queryFn: getLanguages })

  // Skip onboarding entirely if the user has already finished it.
  const { data: statusData } = useQuery({ queryKey: ['onboarding-status'], queryFn: getOnboardingStatus })
  if (statusData?.onboarded) {
    navigate('/', { replace: true })
  }

  const placementMutation = useMutation({
    mutationFn: () => getPlacement(language!.id),
    onSuccess: (res) => {
      if (res.available) {
        setItems(res.items)
        setStep('placement')
      } else {
        // Not enough graded content to test — let the learner self-report.
        setStep('confirm')
      }
    },
  })

  const scoreMutation = useMutation({
    mutationFn: () =>
      scorePlacement(
        language!.id,
        items.map((it) => ({
          id: it.id,
          input: finalizeInput(language!.code, responses[it.id] ?? '', qwertyTranslit),
        })),
      ),
    onSuccess: (res) => {
      setLevel(res.estimated_level)
      setStep('confirm')
    },
  })

  const finishMutation = useMutation({
    mutationFn: () => completeOnboarding({ languageId: language!.id, level }),
    onSuccess: () => {
      setActiveLanguageId(language!.id)
      navigate('/', { replace: true })
    },
  })

  function pickLanguage(lang: Language) {
    setLanguage(lang)
    setStep('method')
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-xl mx-auto px-4 py-10 space-y-6">
        <header>
          <h1 className="text-2xl font-bold text-gray-900">Welcome — let's set you up</h1>
          <p className="text-sm text-gray-500">A minute now and your reviews are ready to go.</p>
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
                  className="rounded-xl border border-gray-200 bg-white px-4 py-3 text-left text-sm font-medium text-gray-800 hover:border-indigo-400 hover:bg-indigo-50"
                  style={{ minHeight: '44px' }}
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
            <button
              type="button"
              onClick={() => {
                setLevel('A1')
                setStep('confirm')
              }}
              className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-left hover:border-indigo-400 hover:bg-indigo-50"
            >
              <span className="block text-sm font-semibold text-gray-800">I'm new to it</span>
              <span className="block text-xs text-gray-500">Start from the beginning (A1)</span>
            </button>
            <button
              type="button"
              onClick={() => placementMutation.mutate()}
              disabled={placementMutation.isPending}
              className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-left hover:border-indigo-400 hover:bg-indigo-50 disabled:opacity-50"
            >
              <span className="block text-sm font-semibold text-gray-800">
                {placementMutation.isPending ? 'Loading…' : 'Take a quick placement check'}
              </span>
              <span className="block text-xs text-gray-500">
                Answer a few words so we start you at the right level
              </span>
            </button>
          </section>
        )}

        {step === 'placement' && language && (
          <section className="space-y-4">
            <h2 className="font-semibold text-gray-800">
              Fill in each answer in {language.name}. Skip any you don't know.
            </h2>
            <div className="space-y-3">
              {items.map((item) => (
                <div key={item.id} className="rounded-xl border border-gray-100 bg-white p-3">
                  {item.kind === 'grammar' ? (
                    <LanguageWrapper languageCode={language.code}>
                      <p className="text-sm text-gray-800">{item.prompt}</p>
                    </LanguageWrapper>
                  ) : (
                    <p className="text-sm text-gray-700">{item.prompt}</p>
                  )}
                  {item.translation && (
                    <p className="text-xs text-gray-400">{item.translation}</p>
                  )}
                  <LanguageWrapper languageCode={language.code}>
                    <input
                      value={responses[item.id] ?? ''}
                      onChange={(e) => {
                        const v = isTranslitEnabled(language.code, qwertyTranslit)
                          ? convertTranslit(language.code, e.target.value)
                          : e.target.value
                        setResponses((r) => ({ ...r, [item.id]: v }))
                      }}
                      aria-label={item.prompt}
                      className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                    />
                  </LanguageWrapper>
                </div>
              ))}
            </div>
            <button
              type="button"
              onClick={() => scoreMutation.mutate()}
              disabled={scoreMutation.isPending}
              className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold rounded-xl px-5 py-2.5 text-sm"
            >
              {scoreMutation.isPending ? 'Scoring…' : 'See my level'}
            </button>
          </section>
        )}

        {step === 'confirm' && language && (
          <section className="space-y-4">
            <h2 className="font-semibold text-gray-800">Start {language.name} at this level</h2>
            <p className="text-sm text-gray-500">
              We'll queue grammar and vocabulary at this level and below. You can change it later.
            </p>
            <select
              value={level}
              onChange={(e) => setLevel(e.target.value)}
              aria-label="Starting level"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm bg-white"
            >
              {CEFR_LEVELS.map((l) => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => finishMutation.mutate()}
              disabled={finishMutation.isPending}
              className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold rounded-xl px-6 py-3 text-sm"
              style={{ minHeight: '44px' }}
            >
              {finishMutation.isPending ? 'Setting up…' : 'Start learning'}
            </button>
          </section>
        )}
      </div>
    </div>
  )
}
