import { useEffect, useState } from 'react'
import ExplanationView from '../../components/ExplanationView'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getLanguages } from '../../api/profile'
import { getCurriculum, getCurriculumPoint, learnPoint } from '../../api/curriculum'
import type { CurriculumPoint } from '../../api/curriculum'
import { usePrefsStore } from '../../stores/prefsStore'
import LanguageWrapper from '../../components/LanguageWrapper'
import SpeakButton from '../../components/SpeakButton'
import BlurReveal from '../../components/BlurReveal'
import ResourceList from '../../components/ResourceList'
import RelatedGrid from '../../components/RelatedGrid'

const LEVEL_ORDER = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']

/**
 * The browsable grammar path — every point in curriculum order, grouped by
 * CEFR level, readable outside of reviews (Bunpro-style grammar pages), with
 * per-point "Add to my reviews".
 */
export default function GrammarPathPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [searchParams] = useSearchParams()
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)
  // Deep link from search (WP13g): /grammar?point=<id> opens that point.
  const [openPointId, setOpenPointId] = useState<string | null>(
    searchParams.get('point'),
  )

  useEffect(() => {
    if (!openPointId) return
    // Scroll the deep-linked (or Related-grid-opened) point into view once
    // the list has rendered it.
    const el = document.getElementById(`point-${openPointId}`)
    el?.scrollIntoView?.({ block: 'center' })
  }, [openPointId])

  const { data: languages = [] } = useQuery({ queryKey: ['languages'], queryFn: getLanguages })
  const language = languages.find((l) => l.id === activeLanguageId)

  const { data: points = [], isLoading } = useQuery({
    queryKey: ['curriculum', activeLanguageId],
    queryFn: () => getCurriculum(activeLanguageId!),
    enabled: !!activeLanguageId,
  })

  const { data: detail } = useQuery({
    queryKey: ['curriculum-point', openPointId],
    queryFn: () => getCurriculumPoint(openPointId!),
    enabled: !!openPointId,
    staleTime: 5 * 60 * 1000,
  })

  const learnMutation = useMutation({
    mutationFn: (pointId: string) => learnPoint(pointId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['curriculum'] })
      queryClient.invalidateQueries({ queryKey: ['curriculum-point'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })

  const byLevel = new Map<string, CurriculumPoint[]>()
  for (const p of points) {
    const level = p.level ?? 'Other'
    if (!byLevel.has(level)) byLevel.set(level, [])
    byLevel.get(level)!.push(p)
  }
  const levels = [...byLevel.keys()].sort(
    (a, b) => LEVEL_ORDER.indexOf(a) - LEVEL_ORDER.indexOf(b),
  )
  const learnedCount = points.filter((p) => p.learned).length
  const languageCode = language?.code ?? 'en'

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {language ? `${language.name} grammar path` : 'Grammar path'}
            </h1>
            {points.length > 0 && (
              <p className="text-sm text-gray-500">
                {learnedCount} of {points.length} in your reviews
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={() => navigate('/')}
            className="text-sm text-lang hover:underline"
          >
            ← Dashboard
          </button>
        </div>

        {isLoading && <p className="text-gray-500">Loading the path…</p>}

        {!isLoading && points.length === 0 && (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 text-center">
            <p className="text-gray-700">No grammar has been published for this language yet.</p>
            <p className="text-sm text-gray-500 mt-1">
              Points appear here once they pass linguist review.
            </p>
          </div>
        )}

        {levels.map((level) => (
          <section key={level}>
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-2">
              {level}
            </h2>
            <ol className="space-y-2">
              {byLevel.get(level)!.map((point, i) => (
                <li
                  key={point.id}
                  id={`point-${point.id}`}
                  className="bg-white rounded-xl shadow-sm border border-gray-100"
                >
                  <button
                    type="button"
                    onClick={() =>
                      setOpenPointId(openPointId === point.id ? null : point.id)
                    }
                    aria-expanded={openPointId === point.id}
                    className="w-full text-left px-4 py-3 flex items-center gap-3"
                    style={{ minHeight: '44px' }}
                  >
                    <span className="text-xs text-gray-400 w-5 shrink-0">{i + 1}</span>
                    <span className="flex-1">
                      <span className="block text-sm font-semibold text-gray-900">
                        {point.title}
                      </span>
                      {point.function_note && (
                        <span className="block text-xs text-gray-500">
                          {point.function_note}
                        </span>
                      )}
                    </span>
                    {point.learned ? (
                      <span className="text-xs rounded-full px-2 py-0.5 bg-green-50 text-green-700">
                        In reviews ✓
                      </span>
                    ) : !point.learnable ? (
                      <span className="text-xs rounded-full px-2 py-0.5 bg-gray-100 text-gray-500">
                        Reading only
                      </span>
                    ) : null}
                    {!point.reviewed && (
                      <span className="text-xs rounded-full px-2 py-0.5 bg-gray-100 text-gray-500">
                        Draft · pending expert review
                      </span>
                    )}
                  </button>

                  {openPointId === point.id && detail && detail.id === point.id && (
                    <div className="border-t border-gray-100 px-4 py-4 space-y-3 text-sm">
                      {detail.explanation && (
                        <ExplanationView text={detail.explanation} />
                      )}
                      {detail.examples.length > 0 && (
                        <ul className="space-y-2">
                          {detail.examples.map((ex, j) => (
                            <li key={j}>
                              <span className="flex items-start gap-1">
                                <LanguageWrapper languageCode={languageCode}>
                                  <span className="text-gray-900">{ex.sentence}</span>
                                </LanguageWrapper>
                                <SpeakButton text={ex.sentence} languageCode={languageCode} />
                              </span>
                              {ex.translation && (
                                <BlurReveal className="block text-gray-500">
                                  {ex.translation}
                                </BlurReveal>
                              )}
                            </li>
                          ))}
                        </ul>
                      )}
                      {detail.culture_note && (
                        <div className="bg-lang-soft border border-lang/20 rounded-lg p-3">
                          <p className="text-lang-dark/80 whitespace-pre-wrap">
                            {detail.culture_note}
                          </p>
                        </div>
                      )}
                      {!!detail.related?.length && (
                        <>
                          <RelatedGrid
                            related={detail.related}
                            onOpen={(id) => setOpenPointId(id)}
                          />
                          <button
                            type="button"
                            onClick={() =>
                              navigate(
                                `/cram?points=${[
                                  detail.id,
                                  ...detail.related!.map((r) => r.id),
                                ].join(',')}`,
                              )
                            }
                            className="text-sm text-lang hover:underline"
                          >
                            ⚡ Quick cram this + related (nothing recorded)
                          </button>
                        </>
                      )}
                      {detail.references.length > 0 && (
                        <ResourceList
                          key={detail.id}
                          pointId={detail.id}
                          references={detail.references}
                          readRefs={detail.read_refs}
                        />
                      )}
                      {detail.learnable && !detail.learned && (
                        <button
                          type="button"
                          onClick={() => learnMutation.mutate(point.id)}
                          disabled={learnMutation.isPending}
                          className="bg-lang hover:bg-lang-dark disabled:opacity-50 text-lang-on font-semibold rounded-xl px-5 py-2.5 text-sm"
                          style={{ minHeight: '44px' }}
                        >
                          {learnMutation.isPending ? 'Adding…' : 'Add to my reviews'}
                        </button>
                      )}
                      {detail.learned && (
                        <p className="text-xs text-green-700">
                          Already in your reviews — it will keep coming back on its FSRS schedule.
                        </p>
                      )}
                    </div>
                  )}
                </li>
              ))}
            </ol>
          </section>
        ))}
      </div>
    </div>
  )
}
