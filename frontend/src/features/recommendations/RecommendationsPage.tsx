import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { usePrefsStore } from '../../stores/prefsStore'
import {
  getRecommendations,
  refreshRecommendations,
  MEDIA_TYPE_LABELS,
  MEDIA_TYPE_ICONS,
  type RecoBatch,
  type RecoItem,
} from '../../api/recommendations'

function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString(undefined, {
    year: 'numeric', month: 'long', day: 'numeric',
  })
}

function RecoCard({ item }: { item: RecoItem }) {
  const icon = MEDIA_TYPE_ICONS[item.type] ?? '✨'
  const label = MEDIA_TYPE_LABELS[item.type] ?? item.type
  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
      <div className="flex items-center gap-2 mb-1">
        <span aria-hidden className="text-lg">{icon}</span>
        <span className="text-[11px] uppercase tracking-wide text-gray-400">
          {label}
        </span>
        {item.level && (
          <span className="ml-auto shrink-0 rounded-full bg-lang-soft text-lang-dark text-[11px] font-medium px-2 py-0.5">
            {item.level}
          </span>
        )}
      </div>
      <h3 className="text-base font-semibold text-gray-900">{item.title}</h3>
      {(item.creator || item.year) && (
        <p className="text-xs text-gray-500">
          {[item.creator, item.year].filter(Boolean).join(' · ')}
        </p>
      )}
      <p className="mt-2 text-sm text-gray-700">{item.blurb}</p>
      {item.why && (
        <p className="mt-2 text-sm text-lang-dark bg-lang-soft/50 rounded-lg px-3 py-2">
          <span className="font-medium">Why this fits you: </span>
          {item.why}
        </p>
      )}
    </div>
  )
}

function Batch({ batch, heading }: { batch: RecoBatch; heading: string }) {
  return (
    <section className="space-y-3" data-testid="reco-batch">
      <div className="flex items-baseline justify-between">
        <h2 className="text-sm font-semibold text-gray-700">{heading}</h2>
        <span className="text-xs text-gray-400">{formatDate(batch.created_at)}</span>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {batch.items.map((item, i) => (
          <RecoCard key={`${batch.id}-${i}`} item={item} />
        ))}
      </div>
    </section>
  )
}

export default function RecommendationsPage() {
  const navigate = useNavigate()
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['recommendations', activeLanguageId],
    queryFn: () => getRecommendations(activeLanguageId!),
    enabled: !!activeLanguageId,
  })

  const refresh = useMutation({
    mutationFn: () => refreshRecommendations(activeLanguageId!),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ['recommendations', activeLanguageId],
      }),
  })

  // Auto-draft this week's batch when it's due — once per page load. The server
  // is idempotent, so this can't double-generate even across quick remounts.
  const fired = useRef(false)
  useEffect(() => {
    if (
      data?.enabled && data.entitled && data.stale &&
      !refresh.isPending && !fired.current
    ) {
      fired.current = true
      refresh.mutate()
    }
  }, [data, refresh])

  const batches = data?.batches ?? []
  const drafting =
    refresh.isPending || (!!data?.enabled && !!data?.entitled && data.stale && batches.length === 0)
  const refreshStatus = (refresh.error as { response?: { status?: number } })
    ?.response?.status

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
        <div className="flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="text-sm text-gray-500 hover:text-lang"
          >
            ← Dashboard
          </button>
          <h1 className="text-lg font-bold text-gray-900">Recommended for you</h1>
        </div>

        {isLoading && <p className="text-sm text-gray-400">Loading…</p>}

        {/* Feature off → point to Settings. */}
        {data && !data.enabled && (
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 text-sm text-gray-600 space-y-3">
            <p>
              Turn on recommendations to get the occasional book, film, series,
              or podcast in your target language — picked for your level and
              your interests.
            </p>
            <button
              type="button"
              onClick={() => navigate('/account')}
              className="text-lang font-medium hover:underline"
            >
              Set it up in Settings →
            </button>
          </div>
        )}

        {/* On but not entitled → tutor+ upsell. */}
        {data?.enabled && !data.entitled && (
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 text-sm text-gray-600 space-y-2">
            <p className="font-medium text-gray-800">A tutor+ feature</p>
            <p>
              Personalized recommendations are part of tutor+. Upgrade for this
              language to get a fresh, level-matched pick list every week.
            </p>
          </div>
        )}

        {/* Drafting this week's batch. */}
        {data?.enabled && data.entitled && drafting && (
          <div
            className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 flex items-center gap-3"
            data-testid="reco-drafting"
          >
            <span
              className="h-5 w-5 animate-spin rounded-full border-2 border-lang border-t-transparent"
              aria-hidden
            />
            <p className="text-sm text-gray-600">
              Putting together this week’s picks for you…
            </p>
          </div>
        )}

        {data?.enabled && data.entitled && refreshStatus === 402 && (
          <p className="text-sm text-amber-600">
            Recommendations need a tutor+ subscription for this language.
          </p>
        )}

        {/* This week + history. */}
        {batches.length > 0 && (
          <div className="space-y-8">
            <Batch batch={batches[0]} heading="This week’s picks" />
            {batches.length > 1 && (
              <div className="space-y-6">
                <h2 className="text-xs uppercase tracking-wide text-gray-400">
                  Earlier recommendations
                </h2>
                {batches.slice(1).map((b) => (
                  <Batch key={b.id} batch={b} heading={formatDate(b.created_at)} />
                ))}
              </div>
            )}
          </div>
        )}

        {data?.enabled && data.entitled && !drafting && batches.length === 0 &&
          refreshStatus !== 402 && (
            <p className="text-sm text-gray-500">
              No recommendations yet — check back soon.
            </p>
          )}
      </div>
    </div>
  )
}
