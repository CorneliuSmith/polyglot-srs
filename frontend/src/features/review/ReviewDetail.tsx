import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getCardDetail } from '../../api/review'
import LanguageWrapper from '../../components/LanguageWrapper'
import SpeakButton from '../../components/SpeakButton'

export interface ReviewCardStats {
  repetitions: number
  streak: number
  lapses: number
  next_review?: string | null
}

interface ReviewDetailProps {
  cardId: string
  cardType: 'grammar' | 'vocabulary' | 'personal'
  languageCode: string
  stats?: ReviewCardStats
}

/**
 * Optional, lazy-loaded "Show info" panel shown after answering — the full
 * item page, Bunpro-style: title + can-do line, explanation, examples,
 * culture note, resources, and the learner's own progress on this card.
 * Collapsed by default — a learner who's satisfied with the quick feedback
 * just continues.
 */
export default function ReviewDetail({ cardId, languageCode, stats }: ReviewDetailProps) {
  const [open, setOpen] = useState(false)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['card-detail', cardId],
    queryFn: () => getCardDetail(cardId),
    enabled: open,
    staleTime: 5 * 60 * 1000,
  })

  return (
    <div className="border-t border-gray-100 pt-3">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="text-sm text-indigo-600 hover:underline touch-manipulation"
        style={{ minHeight: '44px' }}
      >
        {open ? 'Hide info' : 'Show info'}
      </button>

      {open && (
        <div className="mt-2 space-y-4 text-sm" data-testid="review-detail">
          {isLoading && <p className="text-gray-400">Loading…</p>}
          {isError && <p className="text-red-500">Couldn’t load the details.</p>}

          {data && (
            <>
              {/* Item header: what this card IS */}
              <div className="text-center py-2">
                <LanguageWrapper languageCode={languageCode}>
                  <p className="text-2xl font-bold text-gray-900">{data.title}</p>
                </LanguageWrapper>
                {(data.function_note || data.definition) && (
                  <p className="text-sm text-gray-500 mt-1">
                    {data.function_note ?? data.definition}
                  </p>
                )}
              </div>

              {/* The learner's history with this card */}
              {stats && (
                <div className="grid grid-cols-4 gap-2 text-center bg-gray-50 rounded-xl p-3">
                  <div>
                    <span className="block text-base font-semibold text-gray-800 tabular-nums">
                      {stats.repetitions}
                    </span>
                    <span className="block text-[10px] uppercase tracking-wide text-gray-400">
                      Times studied
                    </span>
                  </div>
                  <div>
                    <span className="block text-base font-semibold text-gray-800 tabular-nums">
                      {stats.streak}
                    </span>
                    <span className="block text-[10px] uppercase tracking-wide text-gray-400">
                      Streak
                    </span>
                  </div>
                  <div>
                    <span className="block text-base font-semibold text-gray-800 tabular-nums">
                      {stats.lapses}
                    </span>
                    <span className="block text-[10px] uppercase tracking-wide text-gray-400">
                      Misses
                    </span>
                  </div>
                  <div>
                    <span className="block text-base font-semibold text-gray-800">
                      {stats.next_review
                        ? new Date(stats.next_review).toLocaleDateString()
                        : '—'}
                    </span>
                    <span className="block text-[10px] uppercase tracking-wide text-gray-400">
                      Next review
                    </span>
                  </div>
                </div>
              )}
              {data.card_type === 'grammar' && data.reviewed === false && (
                <p className="inline-block text-xs rounded-full px-2 py-0.5 bg-gray-100 text-gray-500">
                  Draft · pending expert review
                </p>
              )}

              {data.explanation && (
                <div>
                  <h3 className="font-semibold text-gray-700 mb-1">About</h3>
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
                  <h3 className="font-semibold text-gray-700 mb-1">Resources</h3>
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
