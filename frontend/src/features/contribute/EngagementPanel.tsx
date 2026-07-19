import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getEngagement, getEngagementUsers } from '../../api/contribute'
import type { EngagementUser } from '../../api/contribute'

type ActiveWindow = 'd1' | 'd7' | 'd30'
const WINDOW_DAYS: Record<ActiveWindow, number> = { d1: 1, d7: 7, d30: 30 }

function withinDays(iso: string | null, days: number): boolean {
  if (!iso) return false
  return Date.now() - new Date(iso).getTime() <= days * 24 * 60 * 60 * 1000
}

function relativeDay(iso: string | null): string {
  if (!iso) return 'never'
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000)
  if (days <= 0) return 'today'
  if (days === 1) return 'yesterday'
  return `${days}d ago`
}

/** Admin engagement snapshot (beta request): who's using the app, doing
 * what, for how long — read from the activity tables normal use writes.
 * The active-user tiles drill down (beta request, round 2): tapping one
 * lists the ACTUAL users in that window with their per-feature activity. */
export default function EngagementPanel() {
  const { data } = useQuery({
    queryKey: ['engagement'],
    queryFn: () => getEngagement(30),
    retry: false,
  })
  const [windowFilter, setWindowFilter] = useState<ActiveWindow | null>(null)
  const { data: users } = useQuery({
    queryKey: ['engagement-users'],
    queryFn: () => getEngagementUsers(30),
    enabled: windowFilter !== null,
    retry: false,
  })
  if (!data) return null

  const toggle = (w: ActiveWindow) =>
    setWindowFilter((cur) => (cur === w ? null : w))

  const shownUsers: EngagementUser[] = (users ?? []).filter((u) =>
    windowFilter ? withinDays(u.last_active, WINDOW_DAYS[windowFilter]) : true,
  )

  const tile = (w: ActiveWindow, label: string, value: number, sub?: string) => (
    <button
      type="button"
      onClick={() => toggle(w)}
      aria-pressed={windowFilter === w}
      className={
        'rounded-xl p-3 text-left transition-colors ' +
        (windowFilter === w
          ? 'bg-lang-soft ring-1 ring-lang/40'
          : 'bg-gray-50 hover:bg-gray-100')
      }
    >
      <div className="text-xl font-bold text-lang tabular-nums">{value}</div>
      <div className="text-xs text-gray-600">{label}</div>
      <div className="text-[10px] text-gray-400">{sub ?? 'tap for users'}</div>
    </button>
  )

  const stat = (label: string, value: string | number, sub?: string) => (
    <div className="rounded-xl bg-gray-50 p-3">
      <div className="text-xl font-bold text-lang tabular-nums">{value}</div>
      <div className="text-xs text-gray-600">{label}</div>
      {sub && <div className="text-[10px] text-gray-400">{sub}</div>}
    </div>
  )

  return (
    <div
      className="bg-white rounded-2xl border border-gray-100 p-4 text-sm"
      data-testid="engagement"
    >
      <h2 className="text-sm font-semibold text-gray-800">
        Engagement · last {data.days} days
      </h2>
      <p className="text-xs text-gray-500 mb-3">
        All users, all languages — from review, tutor, reader, and learning
        activity. No extra tracking. Tap an active-user tile to see who.
      </p>

      <div className="grid grid-cols-3 gap-2 mb-3">
        {tile('d1', 'active today', data.active_users.d1)}
        {tile('d7', 'active · 7 days', data.active_users.d7)}
        {tile('d30', 'active · 30 days', data.active_users.d30,
              `of ${data.total_users} total`)}
      </div>

      {windowFilter && (
        <div className="mb-3 overflow-x-auto" data-testid="engagement-users">
          <table className="w-full text-xs whitespace-nowrap">
            <thead>
              <tr className="text-left text-gray-400 uppercase tracking-wide text-[10px]">
                <th className="py-1 pr-2">User</th>
                <th className="py-1 pr-2">Last active</th>
                <th className="py-1 pr-2 text-right">Reviews</th>
                <th className="py-1 pr-2 text-right">Tutor</th>
                <th className="py-1 pr-2 text-right">Reads</th>
                <th className="py-1 pr-2 text-right">Cards</th>
                <th className="py-1">Langs</th>
              </tr>
            </thead>
            <tbody>
              {shownUsers.map((u) => (
                <tr key={u.id} className="border-t border-gray-50 text-gray-700">
                  <td className="py-1 pr-2 max-w-40 truncate">{u.email ?? u.id}</td>
                  <td className="py-1 pr-2 text-gray-500">{relativeDay(u.last_active)}</td>
                  <td className="py-1 pr-2 text-right tabular-nums">
                    {u.reviews}
                    {u.review_minutes > 0 && (
                      <span className="text-gray-400"> · {u.review_minutes}m</span>
                    )}
                  </td>
                  <td className="py-1 pr-2 text-right tabular-nums">{u.tutor_messages}</td>
                  <td className="py-1 pr-2 text-right tabular-nums">{u.readings}</td>
                  <td className="py-1 pr-2 text-right tabular-nums">{u.cards_total}</td>
                  <td className="py-1 text-gray-500">{u.languages.join(' ')}</td>
                </tr>
              ))}
              {users && shownUsers.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-2 text-gray-400">
                    No users active in this window.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3">
        {stat('reviews', data.reviews.toLocaleString(), `${data.review_hours} h studying`)}
        {stat('tutor messages', data.tutor_messages.toLocaleString(), `${data.feature_users.tutor} users`)}
        {stat('reader sessions', data.readings.toLocaleString(), `${data.feature_users.reader} users`)}
        {stat('cards started', data.cards_started.toLocaleString(), `+${data.new_users} new users`)}
      </div>

      {data.top_languages.length > 0 && (
        <div>
          <h3 className="text-xs uppercase tracking-wide text-gray-400 mb-1">
            Most-studied languages
          </h3>
          <table className="w-full text-xs">
            <tbody>
              {data.top_languages.map((l) => (
                <tr key={l.code} className="border-t border-gray-50 text-gray-700">
                  <td className="py-1">{l.name}</td>
                  <td className="py-1 text-right text-gray-500">
                    {l.learners} learner{l.learners === 1 ? '' : 's'}
                  </td>
                  <td className="py-1 text-right text-gray-400">
                    {l.cards.toLocaleString()} cards
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
