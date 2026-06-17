import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getCardDetail } from '../../api/review'
import LanguageWrapper from '../../components/LanguageWrapper'
import SpeakButton from '../../components/SpeakButton'

interface ReviewDetailProps {
  cardId: string
  cardType: 'grammar' | 'vocabulary' | 'personal'
  languageCode: string
}

/**
 * Optional, lazy-loaded "review this card" panel shown after answering.
 * Collapsed by default — a learner who's satisfied with the quick feedback
 * just rates and moves on. Grammar cards reveal a broad explanation + culture
 * note + example sentences; vocabulary cards reveal usage notes + examples.
 */
export default function ReviewDetail({ cardId, cardType, languageCode }: ReviewDetailProps) {
  const [open, setOpen] = useState(false)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['card-detail', cardId],
    queryFn: () => getCardDetail(cardId),
    enabled: open,
    staleTime: 5 * 60 * 1000,
  })

  const label = cardType === 'grammar' ? 'Show grammar' : 'More examples'

  return (
    <div className="border-t border-gray-100 pt-3">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="text-sm text-indigo-600 hover:underline touch-manipulation"
        style={{ minHeight: '44px' }}
      >
        {open ? 'Hide' : label}
      </button>

      {open && (
        <div className="mt-2 space-y-4 text-sm" data-testid="review-detail">
          {isLoading && <p className="text-gray-400">Loading…</p>}
          {isError && <p className="text-red-500">Couldn’t load the details.</p>}

          {data && (
            <>
              {data.card_type === 'grammar' && data.reviewed === false && (
                <p className="inline-block text-xs rounded-full px-2 py-0.5 bg-gray-100 text-gray-500">
                  Draft · pending expert review
                </p>
              )}

              {data.explanation && (
                <div>
                  <h3 className="font-semibold text-gray-700 mb-1">Grammar</h3>
                  <p className="text-gray-700 whitespace-pre-wrap">{data.explanation}</p>
                </div>
              )}

              {data.definition && (
                <p className="text-gray-700">
                  <span className="font-semibold">{data.title}</span>
                  {data.part_of_speech ? ` (${data.part_of_speech})` : ''} — {data.definition}
                </p>
              )}

              {data.usage_note && (
                <div>
                  <h3 className="font-semibold text-gray-700 mb-1">Usage</h3>
                  <p className="text-gray-700 whitespace-pre-wrap">{data.usage_note}</p>
                </div>
              )}

              {data.examples.length > 0 && (
                <div>
                  <h3 className="font-semibold text-gray-700 mb-1">Examples</h3>
                  <ul className="space-y-2">
                    {data.examples.map((ex, i) => (
                      <li key={i}>
                        <span className="flex items-start gap-1">
                          <LanguageWrapper languageCode={languageCode}>
                            <span className="text-gray-800">{ex.sentence}</span>
                          </LanguageWrapper>
                          <SpeakButton text={ex.sentence} languageCode={languageCode} />
                        </span>
                        {ex.translation && (
                          <span className="block text-gray-500">{ex.translation}</span>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {data.culture_note && (
                <div className="bg-indigo-50 border border-indigo-100 rounded-lg p-3">
                  <h3 className="font-semibold text-indigo-700 mb-1">Culture note</h3>
                  <p className="text-indigo-900/80 whitespace-pre-wrap">{data.culture_note}</p>
                </div>
              )}

              {data.references && data.references.length > 0 && (
                <div>
                  <h3 className="font-semibold text-gray-700 mb-1">References</h3>
                  <ul className="space-y-1">
                    {data.references.map((ref, i) => (
                      <li key={i}>
                        <a
                          href={ref.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-indigo-600 hover:underline"
                        >
                          {ref.title}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {!data.explanation &&
                !data.definition &&
                !data.usage_note &&
                data.examples.length === 0 && (
                  <p className="text-gray-400">No extra notes for this card yet.</p>
                )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
