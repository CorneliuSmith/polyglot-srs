import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getCardDetail } from '../../api/review'
import { getLanguages } from '../../api/profile'
import type { CardProgress } from '../../api/types'
import LanguageWrapper from '../../components/LanguageWrapper'
import FormsPanel from '../../components/FormsPanel'
import SpeakButton from '../../components/SpeakButton'
import BlurReveal from '../../components/BlurReveal'
import StageBadge from '../../components/StageBadge'
import ResourceList from '../../components/ResourceList'
import RelatedGrid from '../../components/RelatedGrid'

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

function ProgressPanel({ progress }: { progress: CardProgress }) {
  const cells: { value: string; label: string }[] = [
    { value: String(progress.times_studied), label: 'Times studied' },
    {
      value:
        progress.accuracy != null ? `${Math.round(progress.accuracy * 100)}%` : '—',
      label: 'Accuracy',
    },
    { value: String(progress.streak), label: 'Streak' },
    { value: String(progress.misses), label: 'Misses' },
    {
      value: progress.first_studied
        ? new Date(progress.first_studied).toLocaleDateString()
        : '—',
      label: 'First studied',
    },
    {
      value: progress.next_review
        ? new Date(progress.next_review).toLocaleDateString()
        : '—',
      label: 'Next review',
    },
  ]
  return (
    <div className="grid grid-cols-3 gap-2 text-center bg-gray-50 rounded-xl p-3">
      {cells.map((c) => (
        <div key={c.label}>
          <span className="block text-base font-semibold text-gray-800 tabular-nums">
            {c.value}
          </span>
          <span className="block text-[10px] uppercase tracking-wide text-gray-400">
            {c.label}
          </span>
        </div>
      ))}
    </div>
  )
}

/**
 * Optional, lazy-loaded "Show info" panel shown after answering — the full
 * item page, Bunpro-style: title + can-do line + SRS stage, progress panel,
 * explanation, blur-until-toggled examples (incl. the learner's own
 * sentences), culture note, Related grid, and read-tracked resources.
 * Collapsed by default — a learner who's satisfied with the quick feedback
 * just continues.
 */
export default function ReviewDetail({ cardId, languageCode, stats }: ReviewDetailProps) {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [showTranslations, setShowTranslations] = useState(false)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['card-detail', cardId],
    queryFn: () => getCardDetail(cardId),
    enabled: open,
    staleTime: 5 * 60 * 1000,
  })
  const { data: languages = [] } = useQuery({
    queryKey: ['languages'],
    queryFn: getLanguages,
    enabled: open,
    staleTime: 5 * 60 * 1000,
  })

  const ownSentences = data?.your_sentences ?? []
  // "Learning English from X": say which language the hints are in.
  const hintLanguage =
    data?.hint_locale && data.hint_locale !== 'en'
      ? languages.find((l) => l.code === data.hint_locale)?.name ??
        data.hint_locale.toUpperCase()
      : null

  return (
    <div className="border-t border-gray-100 pt-3">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="text-sm text-lang hover:underline touch-manipulation"
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
              {/* Item header: what this card IS + how deep it sits in memory */}
              <div className="text-center py-2">
                <LanguageWrapper languageCode={languageCode}>
                  <p className="text-2xl font-bold text-gray-900">{data.title}</p>
                </LanguageWrapper>
                {(data.function_note || data.definition) && (
                  <p className="text-sm text-gray-500 mt-1">
                    {data.function_note ?? data.definition}
                  </p>
                )}
                {data.progress && (
                  <div className="mt-2">
                    <StageBadge stage={data.progress.stage} />
                  </div>
                )}
                {hintLanguage && (
                  <p className="mt-1 inline-block text-[11px] rounded-full px-2 py-0.5 bg-lang-soft text-lang">
                    Hints in {hintLanguage}
                  </p>
                )}
              </div>

              {/* The learner's history with this card */}
              {data.progress ? (
                <ProgressPanel progress={data.progress} />
              ) : (
                stats && (
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
                )
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

              {data.card_type === 'vocabulary' && (
                <FormsPanel morphology={data.morphology} languageCode={languageCode} />
              )}

              {data.examples.length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <h3 className="font-semibold text-gray-700">Examples</h3>
                    <button
                      type="button"
                      onClick={() => setShowTranslations((v) => !v)}
                      aria-pressed={showTranslations}
                      className="text-xs text-lang hover:underline"
                    >
                      {showTranslations ? 'Hide translations' : 'Show translations'}
                    </button>
                  </div>
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
                          <BlurReveal
                            forceRevealed={showTranslations}
                            className="block text-gray-500"
                          >
                            {ex.translation}
                          </BlurReveal>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {ownSentences.length > 0 && (
                <div>
                  <h3 className="font-semibold text-gray-700 mb-1">Your sentences</h3>
                  <ul className="space-y-2">
                    {ownSentences.map((ex, i) => (
                      <li key={i}>
                        <span className="flex items-start gap-1">
                          <LanguageWrapper languageCode={languageCode}>
                            <span className="text-gray-800">{ex.sentence}</span>
                          </LanguageWrapper>
                          <SpeakButton text={ex.sentence} languageCode={languageCode} />
                        </span>
                        {ex.translation && (
                          <BlurReveal
                            forceRevealed={showTranslations}
                            className="block text-gray-500"
                          >
                            {ex.translation}
                          </BlurReveal>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {data.culture_note && (
                <div className="bg-lang-soft border border-lang/20 rounded-lg p-3">
                  <h3 className="font-semibold text-lang-dark mb-1">Culture note</h3>
                  <p className="text-lang-dark/80 whitespace-pre-wrap">{data.culture_note}</p>
                </div>
              )}

              {data.related && data.related.length > 0 && (
                <>
                  <RelatedGrid related={data.related} />
                  {data.point_id && (
                    <button
                      type="button"
                      onClick={() =>
                        navigate(
                          `/cram?points=${[
                            data.point_id,
                            ...data.related!.map((r) => r.id),
                          ].join(',')}`,
                        )
                      }
                      className="text-sm text-lang hover:underline"
                    >
                      ⚡ Quick cram this + related (nothing recorded)
                    </button>
                  )}
                </>
              )}

              {data.references && data.references.length > 0 && (
                <ResourceList
                  key={data.point_id ?? cardId}
                  pointId={data.point_id}
                  references={data.references}
                  readRefs={data.read_refs}
                />
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
