import { useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import UiLanguageSwitcher from '../../components/UiLanguageSwitcher'
import {
  BookOpen,
  Film,
  Headphones,
  Music,
  Sparkles,
  Tv,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { usePrefsStore } from '../../stores/prefsStore'
import {
  getRecommendations,
  refreshRecommendations,
  markRecommendationsSeen,
  type RecoBatch,
  type RecoItem,
} from '../../api/recommendations'

const MEDIA_TYPE_ICONS: Record<string, LucideIcon> = {
  book: BookOpen,
  film: Film,
  series: Tv,
  podcast: Headphones,
  music: Music,
}

function formatDate(iso: string, locale: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString(locale, {
    year: 'numeric', month: 'long', day: 'numeric',
  })
}

function RecoCard({ item }: { item: RecoItem }) {
  const { t } = useTranslation()
  const Icon = MEDIA_TYPE_ICONS[item.type] ?? Sparkles
  const label = t(`recos.mediaTypes.${item.type}`, { defaultValue: item.type })
  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
      <div className="flex items-center gap-2 mb-1">
        <Icon aria-hidden className="h-4 w-4 text-lang" strokeWidth={1.75} />
        <span className="text-[11px] uppercase tracking-wide text-gray-400">
          {label}
        </span>
        {item.genre && (
          <span className="rounded-full bg-gray-100 text-gray-500 text-[11px] px-2 py-0.5">
            {item.genre}
          </span>
        )}
        {item.level && (
          <span className="ms-auto shrink-0 rounded-full bg-lang-soft text-lang-dark text-[11px] font-medium px-2 py-0.5">
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
          <span className="font-medium">{t('recos.whyFits')}</span>
          {item.why}
        </p>
      )}
    </div>
  )
}

function Batch({ batch, heading }: { batch: RecoBatch; heading: string }) {
  const { i18n } = useTranslation()
  return (
    <section className="space-y-3" data-testid="reco-batch">
      <div className="flex items-baseline justify-between">
        <h2 className="text-sm font-semibold text-gray-700">{heading}</h2>
        <span className="text-xs text-gray-400">
          {formatDate(batch.created_at, i18n.language)}
        </span>
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
  const { t, i18n } = useTranslation()
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['recommendations', activeLanguageId],
    queryFn: () => getRecommendations(activeLanguageId!),
    enabled: !!activeLanguageId,
  })

  const refresh = useMutation({
    mutationFn: (force: boolean) =>
      refreshRecommendations(activeLanguageId!, force),
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
      refresh.mutate(false)
    }
  }, [data, refresh])

  // Reaching this page IS seeing the picks — clear the dashboard prompt so
  // it can't nag about something already read. Once per mount; failure is
  // silently fine, the prompt simply shows once more.
  const marked = useRef(false)
  useEffect(() => {
    if (!marked.current && (data?.batches?.length ?? 0) > 0) {
      marked.current = true
      markRecommendationsSeen().catch(() => undefined)
      queryClient.setQueryData(['recommendations-unseen', activeLanguageId], null)
    }
  }, [data, queryClient, activeLanguageId])

  const batches = data?.batches ?? []
  const drafting =
    refresh.isPending || (!!data?.enabled && !!data?.entitled && data.stale && batches.length === 0)
  const refreshStatus = (refresh.error as { response?: { status?: number } })
    ?.response?.status

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
        <div className="flex items-center justify-between gap-3">
          <span className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => navigate('/')}
              className="text-sm text-gray-500 hover:text-lang"
            >
              {t('common.backToDashboard')}
            </button>
            <UiLanguageSwitcher />
          </span>
          <h1 className="text-lg font-bold text-gray-900">{t('dashboard.recommendedTitle')}</h1>
        </div>

        {isLoading && <p className="text-sm text-gray-400">{t('common.loading')}</p>}

        {/* Feature off → point to Settings. */}
        {data && !data.enabled && (
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 text-sm text-gray-600 space-y-3">
            <p>
              {t('recos.turnOn')}
            </p>
            <button
              type="button"
              onClick={() => navigate('/account')}
              className="text-lang font-medium hover:underline"
            >
              {t('recos.setUpSettings')}
            </button>
          </div>
        )}

        {/* On but not entitled → tutor+ upsell. */}
        {data?.enabled && !data.entitled && (
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 text-sm text-gray-600 space-y-2">
            <p className="font-medium text-gray-800">{t('recos.plusFeature')}</p>
            <p>
              {t('recos.plusUpsell')}
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
              {t('recos.drafting')}
            </p>
          </div>
        )}

        {data?.enabled && data.entitled && refreshStatus === 402 && (
          <p className="text-sm text-amber-600">
            {t('recos.needPlus')}
          </p>
        )}

        {/* Ask for picks NOW, rather than waiting out the weekly window.
            Each draft reads current level and progress, so this is the
            right move after finishing a level or shifting interests. */}
        {data?.enabled && data.entitled && !drafting && refreshStatus !== 402 && (
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              data-testid="reco-refresh-now"
              onClick={() => refresh.mutate(true)}
              className="rounded-lg bg-lang hover:bg-lang-dark text-lang-on font-semibold px-4 py-2 text-sm"
              style={{ minHeight: '44px' }}
            >
              {batches.length === 0 ? t('recos.getMyPicks') : t('recos.getNewPicks')}
            </button>
            <span className="text-xs text-gray-500">
              {t('recos.matchedNow')}
            </span>
          </div>
        )}

        {refreshStatus === 429 && (
          <p className="text-sm text-amber-600">
            {t('recos.rateLimited')}
          </p>
        )}

        {/* This week + history. */}
        {batches.length > 0 && (
          <div className="space-y-8">
            <Batch batch={batches[0]} heading={t('recos.thisWeeksPicks')} />
            {batches.length > 1 && (
              <div className="space-y-6">
                <h2 className="text-xs uppercase tracking-wide text-gray-400">
                  {t('recos.earlier')}
                </h2>
                {batches.slice(1).map((b) => (
                  <Batch
                    key={b.id}
                    batch={b}
                    heading={formatDate(b.created_at, i18n.language)}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {data?.enabled && data.entitled && !drafting && batches.length === 0 &&
          refreshStatus !== 402 && (
            <p className="text-sm text-gray-500">
              {t('recos.noneYet')}
            </p>
          )}
      </div>
    </div>
  )
}
