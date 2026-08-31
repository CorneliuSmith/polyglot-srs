import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { BookOpen, Film, Headphones, Music, Sparkles, Tv } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { getRecommendations } from '../../api/recommendations'
import type { RecoItem } from '../../api/recommendations'
import { usePrefsStore } from '../../stores/prefsStore'

/**
 * The latest picks, as a sideways scroll for a dashboard widget slot
 * (owner: "a recs scroll of your latest recs should be an option").
 *
 * Deliberately the glance, not the page: cover-ish cards you can flick
 * through, each one tapping into /recommendations where the blurb, the
 * reason it was picked, and the finished/rating controls live. Repeating
 * that detail here would make a widget the size of the thing it links to.
 *
 * Unlike the other widgets it feeds itself rather than reading the shared
 * DashboardStats — recommendations are per language and already cached
 * under their own key, so pinning this costs no extra request on a device
 * that has the page open too.
 */

const MEDIA_TYPE_ICONS: Record<string, LucideIcon> = {
  book: BookOpen,
  film: Film,
  series: Tv,
  podcast: Headphones,
  music: Music,
}

function PickCard({ item, onOpen }: { item: RecoItem; onOpen: () => void }) {
  const { t } = useTranslation()
  const Icon = MEDIA_TYPE_ICONS[item.type] ?? Sparkles
  const label = t(`recos.mediaTypes.${item.type}`, { defaultValue: item.type })
  const meta = [item.creator, item.year].filter(Boolean).join(' · ')

  return (
    <button
      type="button"
      onClick={onOpen}
      // Fixed width so the row is a scroll rather than a squeeze: the model
      // writes titles free-form, and letting them size the cards made one
      // long title eat the whole viewport.
      className="snap-start shrink-0 w-40 rounded-xl border border-gray-100 bg-gray-50/60 px-3 py-2 text-start hover:border-lang/40 hover:bg-lang-soft/40 transition-colors"
      style={{ minHeight: '44px' }}
    >
      <span className="flex items-center gap-1.5">
        <Icon aria-hidden className="h-3.5 w-3.5 shrink-0 text-lang" strokeWidth={1.75} />
        <span className="truncate text-[10px] uppercase tracking-wide text-gray-500">
          {label}
        </span>
      </span>
      {/* Two lines, then ellipsis. A widget row cannot grow to fit a title
          the model felt like writing in full. */}
      <span
        className="mt-0.5 block text-xs font-semibold leading-snug text-gray-800 overflow-hidden"
        style={{
          display: '-webkit-box',
          WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical',
        }}
      >
        {item.title}
      </span>
      {meta && (
        <span className="mt-0.5 block truncate text-[10px] text-gray-500">
          {meta}
        </span>
      )}
    </button>
  )
}

/** A one-line body for every state that isn't "here are your picks", each
 *  one a way into the page rather than a dead end. */
function Hint({ text, onOpen }: { text: string; onOpen: () => void }) {
  return (
    <button
      type="button"
      onClick={onOpen}
      className="text-start text-xs text-gray-500 hover:text-lang hover:underline"
    >
      {text}
    </button>
  )
}

export default function RecsWidget() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)

  // Same key the Recommendations page uses, so the two share one cache
  // entry. `retry: false` because the informative failures here (402 not
  // entitled, 409 feature off) are answers, not outages.
  const { data, isLoading } = useQuery({
    queryKey: ['recommendations', activeLanguageId],
    queryFn: () => getRecommendations(activeLanguageId!),
    enabled: !!activeLanguageId,
    retry: false,
  })

  const open = () => navigate('/recommendations')

  if (isLoading) {
    return <span className="text-xs text-gray-400">{t('common.loading')}</span>
  }
  // Off, or not available on this account. No pitch and no price: what a
  // widget slot owes the reader is where to go, and the monetization
  // master switch may well be off entirely.
  if (!data?.enabled || !data.entitled) {
    return <Hint text={t('dashboard.recsSetUp')} onOpen={open} />
  }

  const items = data.batches?.[0]?.items ?? []
  if (items.length === 0) {
    return (
      <Hint
        text={data.generating ? t('recos.drafting') : t('recos.noneYet')}
        onOpen={open}
      />
    )
  }

  return (
    <div
      // Focusable and labelled: a scroll region that only a mouse can reach
      // is one most people cannot reach.
      tabIndex={0}
      role="group"
      aria-label={t('dashboard.recsTitle')}
      data-testid="recs-scroll"
      className="flex w-full gap-2 overflow-x-auto snap-x snap-mandatory pb-1"
    >
      {items.map((item, i) => (
        <PickCard key={`${item.title}-${i}`} item={item} onOpen={open} />
      ))}
      {/* The end of the scroll is the way in, so flicking to the last card
          lands on an action rather than a wall. */}
      <button
        type="button"
        onClick={open}
        data-testid="recs-see-all"
        className="snap-start shrink-0 w-28 rounded-xl border border-dashed border-gray-200 px-3 py-2 text-xs font-medium text-gray-500 hover:border-lang/40 hover:text-lang"
        style={{ minHeight: '44px' }}
      >
        {t('dashboard.recsSeeAll')}
      </button>
    </div>
  )
}
