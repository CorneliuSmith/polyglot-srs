import { useState, type ComponentType } from 'react'
import { useTranslation } from 'react-i18next'
import { Flame, Plus, X } from 'lucide-react'
import { usePrefsStore } from '../../stores/prefsStore'
import type { DashboardStats } from '../../api/types'

/**
 * iPhone-style widget slots under the Study bar (owner request): two open
 * spaces where the learner pins compact views of the progress charts they
 * actually glance at, instead of scrolling to the Progress tab for them.
 *
 * The full charts stay on Progress; these are deliberately small versions
 * that fit a half-width card. Choice is device-local (prefsStore) — which
 * chart you like at the top of your phone is not account state.
 */

const SLOT_COUNT = 2
const DAY_KEYS = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']
const CEFR_LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']

const WIDGET_IDS = ['streak', 'forecast', 'cefr', 'itemsStudied', 'activity'] as const
type WidgetId = (typeof WIDGET_IDS)[number]

const isWidgetId = (id: string): id is WidgetId =>
  (WIDGET_IDS as readonly string[]).includes(id)

// Label keys reuse the full charts' own titles so the picker names match
// what the learner already knows from the Progress tab.
const LABEL_KEYS: Record<WidgetId, string> = {
  streak: 'dashboard.streakTitle',
  forecast: 'dashboard.forecastTitle',
  cefr: 'dashboard.cefrTitle',
  itemsStudied: 'dashboard.itemsStudied',
  activity: 'dashboard.activityTitle',
}

function StreakWidget({ stats }: { stats?: DashboardStats }) {
  const { t } = useTranslation()
  return (
    <div className="flex items-center justify-center gap-2 h-full">
      <Flame aria-hidden className="h-7 w-7 text-orange-400" />
      <div>
        <span className="block text-2xl font-bold leading-none text-gray-900">
          {stats?.streak_days ?? 0}
        </span>
        <span className="block text-[10px] text-gray-500">
          {t('settings.progress.dayStreak')}
        </span>
      </div>
    </div>
  )
}

function ItemsStudiedWidget({ stats }: { stats?: DashboardStats }) {
  return (
    <div className="flex items-center justify-center h-full">
      <span className="text-3xl font-bold text-gray-900">
        {stats?.profile?.items_studied ?? 0}
      </span>
    </div>
  )
}

function ForecastWidget({ stats }: { stats?: DashboardStats }) {
  const { t } = useTranslation()
  const forecast = stats?.forecast ?? []
  const max = Math.max(1, ...forecast.map((d) => d.count))
  return (
    <div className="flex items-end justify-between gap-1 h-full">
      {forecast.map((d, i) => {
        const day = new Date(`${d.date}T00:00:00Z`)
        const label =
          i === 0 ? t('common.today') : t(`days.${DAY_KEYS[day.getUTCDay()]}`)
        return (
          <div key={d.date} className="flex-1 flex flex-col items-center justify-end gap-0.5 min-w-0">
            <span className="text-[9px] tabular-nums text-gray-500 leading-none">
              {d.count > 0 ? d.count : ''}
            </span>
            <div
              className={`w-full rounded-t ${d.count > 0 ? 'bg-lang/70' : 'bg-gray-100'}`}
              style={{ height: `${Math.max(3, (d.count / max) * 28)}px` }}
            />
            <span className="text-[8px] text-gray-400 truncate max-w-full">{label}</span>
          </div>
        )
      })}
    </div>
  )
}

function ActivityWidget({ stats }: { stats?: DashboardStats }) {
  // Last week only — half a card can't hold the full two-week chart.
  const activity = (stats?.activity ?? []).slice(-7)
  const max = Math.max(1, ...activity.map((d) => d.vocab + d.grammar))
  return (
    <div className="flex items-end justify-between gap-1 h-full">
      {activity.map((d) => {
        const total = d.vocab + d.grammar
        return (
          <div key={d.date} className="flex-1 flex flex-col justify-end">
            <div
              className="w-full flex flex-col justify-end rounded-t overflow-hidden"
              style={{ height: `${Math.max(total > 0 ? 5 : 2, (total / max) * 40)}px` }}
            >
              <div
                className="w-full bg-lang-accent"
                style={{ height: total ? `${(d.grammar / total) * 100}%` : 0 }}
              />
              <div className={`w-full flex-1 ${total > 0 ? 'bg-lang' : 'bg-gray-100'}`} />
            </div>
          </div>
        )
      })}
    </div>
  )
}

function CefrWidget({ stats }: { stats?: DashboardStats }) {
  const progress = stats?.cefr_progress ?? {}
  return (
    <div className="space-y-1">
      {CEFR_LEVELS.map((level) => {
        const { learned = 0, total = 0 } = progress[level] ?? {}
        const pct = total > 0 ? Math.round((learned / total) * 100) : 0
        return (
          <div key={level} className="flex items-center gap-1.5">
            <span className="w-5 text-[9px] font-semibold text-gray-500 shrink-0">
              {level}
            </span>
            <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-lang rounded-full"
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}

const RENDERERS: Record<WidgetId, ComponentType<{ stats?: DashboardStats }>> = {
  streak: StreakWidget,
  forecast: ForecastWidget,
  cefr: CefrWidget,
  itemsStudied: ItemsStudiedWidget,
  activity: ActivityWidget,
}

export default function WidgetSlots({ stats }: { stats?: DashboardStats }) {
  const { t } = useTranslation()
  const dashboardWidgets = usePrefsStore((s) => s.dashboardWidgets)
  const setDashboardWidgets = usePrefsStore((s) => s.setDashboardWidgets)
  // Slot index whose picker is open, or null. One at a time.
  const [pickerFor, setPickerFor] = useState<number | null>(null)

  // Drop ids a stale persisted state might carry for widgets that no
  // longer exist, then compact left so slot order stays stable.
  const chosen = (dashboardWidgets ?? []).filter(isWidgetId).slice(0, SLOT_COUNT)
  const available = WIDGET_IDS.filter((id) => !chosen.includes(id))

  const addWidget = (id: WidgetId) => {
    setDashboardWidgets([...chosen, id])
    setPickerFor(null)
  }
  const removeWidget = (id: WidgetId) => {
    setDashboardWidgets(chosen.filter((w) => w !== id))
    setPickerFor(null)
  }

  return (
    <div data-testid="widget-slots" className="grid grid-cols-2 gap-4">
      {Array.from({ length: SLOT_COUNT }, (_, i) => {
        const id = chosen[i]
        if (id) {
          const Body = RENDERERS[id]
          return (
            <div
              key={id}
              data-testid={`widget-${id}`}
              className="bg-white rounded-2xl shadow-sm border border-gray-100 p-3"
            >
              <div className="flex items-center justify-between mb-2">
                <h2 className="text-[10px] uppercase tracking-wide text-gray-400 truncate">
                  {t(LABEL_KEYS[id])}
                </h2>
                <button
                  type="button"
                  onClick={() => removeWidget(id)}
                  aria-label={t('dashboard.removeWidget')}
                  title={t('dashboard.removeWidget')}
                  className="shrink-0 -me-1 -mt-1 p-1 text-gray-300 hover:text-gray-500"
                >
                  <X aria-hidden className="h-3.5 w-3.5" />
                </button>
              </div>
              <div className="h-16">
                <Body stats={stats} />
              </div>
            </div>
          )
        }
        // Open slot. The picker replaces the "+" in place, listing only
        // the widgets not already pinned in the other slot.
        return (
          <div key={`empty-${i}`}>
            {pickerFor === i ? (
              <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-2 space-y-1">
                {available.map((id) => (
                  <button
                    key={id}
                    type="button"
                    onClick={() => addWidget(id)}
                    className="w-full text-start px-2 py-1.5 text-xs font-medium text-gray-700 rounded-lg hover:bg-lang-soft hover:text-lang"
                  >
                    {t(LABEL_KEYS[id])}
                  </button>
                ))}
                <button
                  type="button"
                  onClick={() => setPickerFor(null)}
                  className="w-full text-center px-2 py-1 text-[10px] text-gray-400 hover:text-gray-600"
                >
                  {t('common.cancel')}
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setPickerFor(i)}
                data-testid={`widget-add-${i}`}
                className="w-full h-full min-h-[6.5rem] rounded-2xl border-2 border-dashed border-gray-200 flex flex-col items-center justify-center gap-1 text-gray-400 hover:text-lang hover:border-lang/40 transition-colors"
              >
                <Plus aria-hidden className="h-4 w-4" />
                <span className="text-xs font-medium">{t('dashboard.addWidget')}</span>
              </button>
            )}
          </div>
        )
      })}
    </div>
  )
}
