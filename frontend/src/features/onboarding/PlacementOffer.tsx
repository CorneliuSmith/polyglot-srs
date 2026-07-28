import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getPlacementHistory } from '../../api/onboarding'
import { getLanguages } from '../../api/profile'
import { usePrefsStore } from '../../stores/prefsStore'
import PlacementTest from './PlacementTest'

/**
 * First time in a language, offer the placement test (owner request).
 *
 * "First time" is server truth — no recorded attempt in THIS language — so
 * adding a fourth language offers the test again even though the account is
 * years old, which is exactly when it's useful. Declining is remembered
 * client-side and the copy says out loud that it can be taken later, so
 * "Not now" is a real answer rather than a door closing.
 */
export default function PlacementOffer({
  languageId,
}: {
  languageId: string | null
}) {
  const dismissed = usePrefsStore((s) => s.placementOfferDismissed)
  const dismiss = usePrefsStore((s) => s.dismissPlacementOffer)
  const [testing, setTesting] = useState(false)

  const { data: languages = [] } = useQuery({
    queryKey: ['languages'],
    queryFn: getLanguages,
  })
  const alreadySaidNo = !!languageId && dismissed.includes(languageId)
  const { data } = useQuery({
    queryKey: ['placement-history', languageId],
    queryFn: () => getPlacementHistory(languageId!),
    // Don't spend a request on a learner who already waved it off.
    enabled: !!languageId && !alreadySaidNo,
    retry: false,
    staleTime: 5 * 60 * 1000,
  })

  const language = languages.find((l) => l.id === languageId)
  if (!languageId || !language || alreadySaidNo) return null
  if (!data || data.has_placed) return null

  if (testing) {
    return (
      <PlacementTest
        language={language}
        onClose={() => {
          setTesting(false)
          dismiss(languageId)
        }}
      />
    )
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
      role="dialog"
      aria-modal="true"
      aria-label={`Place your ${language.name}`}
      data-testid="placement-offer"
    >
      <div className="w-full max-w-md rounded-2xl bg-white p-5 shadow-xl space-y-3">
        <p className="text-xs uppercase tracking-wide text-lang font-semibold">
          New to {language.name} here
        </p>
        <h2 className="text-base font-semibold text-gray-900">
          Want to find your starting level?
        </h2>
        <p className="text-sm text-gray-600">
          A short test that adapts to your answers — most people finish in 5–8
          questions. We&apos;ll use the result to queue grammar and vocabulary
          that actually fits you, instead of starting you at A1 by default.
        </p>
        <p className="text-xs text-gray-500">
          Not now is fine — you can take it, and retake it, <b>any time</b> from
          Settings &rarr; Your level.
        </p>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setTesting(true)}
            className="flex-1 rounded-xl bg-lang text-lang-on px-4 py-2.5 text-sm font-semibold hover:bg-lang-dark"
            style={{ minHeight: '44px' }}
          >
            Take the test
          </button>
          <button
            type="button"
            onClick={() => dismiss(languageId)}
            className="rounded-xl border border-gray-300 px-4 py-2.5 text-sm text-gray-600 hover:bg-gray-50"
            style={{ minHeight: '44px' }}
          >
            Not now
          </button>
        </div>
      </div>
    </div>
  )
}
