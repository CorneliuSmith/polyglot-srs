import { Fragment, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  getEngagement,
  getEngagementUsers,
  getEngagementUserDetail,
} from '../../api/contribute'
import type { EngagementUser } from '../../api/contribute'

type ActiveWindow = 'd1' | 'd7' | 'd30'
type MetricKey = 'reviews' | 'tutor_messages' | 'readings' | 'cards_started'

/** Which users a tapped tile shows. Window tiles filter by recency,
 * metric tiles by who actually used that feature, language rows by who
 * studies it — one filter active at a time. */
type Filter =
  | { kind: 'window'; w: ActiveWindow }
  | { kind: 'metric'; m: MetricKey }
  | { kind: 'language'; code: string }
  | { kind: 'all' }

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

function sameFilter(a: Filter | null, b: Filter): boolean {
  if (!a || a.kind !== b.kind) return false
  if (a.kind === 'window' && b.kind === 'window') return a.w === b.w
  if (a.kind === 'metric' && b.kind === 'metric') return a.m === b.m
  if (a.kind === 'language' && b.kind === 'language') return a.code === b.code
  return a.kind === 'all'
}

/** Admin engagement snapshot (beta request): who's using the app, doing
 * what, for how long — read from the activity tables normal use writes.
 * Every number drills down (beta request, round 2): active-user tiles,
 * feature tiles, and language rows all list the ACTUAL users behind
 * them, and each user row expands to their per-language activity. */
export default function EngagementPanel() {
  const { data } = useQuery({
    queryKey: ['engagement'],
    queryFn: () => getEngagement(30),
    retry: false,
  })
  const [filter, setFilter] = useState<Filter | null>(null)
  const [expandedUser, setExpandedUser] = useState<string | null>(null)
  const { data: users } = useQuery({
    queryKey: ['engagement-users'],
    queryFn: () => getEngagementUsers(30),
    enabled: filter !== null,
    retry: false,
  })
  const { data: userLangs } = useQuery({
    queryKey: ['engagement-user', expandedUser],
    queryFn: () => getEngagementUserDetail(expandedUser!, 30),
    enabled: expandedUser !== null,
    retry: false,
  })
  if (!data) return null

  const toggle = (f: Filter) =>
    setFilter((cur) => (sameFilter(cur, f) ? null : f))

  let shownUsers: EngagementUser[] = users ?? []
  if (filter?.kind === 'window') {
    shownUsers = shownUsers.filter((u) =>
      withinDays(u.last_active, WINDOW_DAYS[filter.w]),
    )
  } else if (filter?.kind === 'metric') {
    shownUsers = shownUsers
      .filter((u) => u[filter.m] > 0)
      .sort((a, b) => b[filter.m] - a[filter.m])
  } else if (filter?.kind === 'language') {
    shownUsers = shownUsers.filter((u) => u.languages.includes(filter.code))
  }

  const tileClasses = (active: boolean) =>
    'rounded-xl p-3 text-left transition-colors ' +
    (active ? 'bg-lang-soft ring-1 ring-lang/40' : 'bg-gray-50 hover:bg-gray-100')

  const tile = (f: Filter, label: string, value: string | number, sub?: string) => (
    <button
      type="button"
      onClick={() => toggle(f)}
      aria-pressed={sameFilter(filter, f)}
      className={tileClasses(sameFilter(filter, f))}
    >
      <div className="text-xl font-bold text-lang tabular-nums">{value}</div>
      <div className="text-xs text-gray-600">{label}</div>
      <div className="text-[10px] text-gray-400">{sub ?? 'tap for users'}</div>
    </button>
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
        activity. No extra tracking. Tap any tile or language for the users
        behind it; tap a user for their per-language detail.
      </p>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3">
        {tile({ kind: 'window', w: 'd1' }, 'active today', data.active_users.d1)}
        {tile({ kind: 'window', w: 'd7' }, 'active · 7 days', data.active_users.d7)}
        {tile({ kind: 'window', w: 'd30' }, 'active · 30 days', data.active_users.d30)}
        {tile({ kind: 'all' }, 'all accounts', data.total_users,
              'including never-active')}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3">
        {tile({ kind: 'metric', m: 'reviews' }, 'reviews',
              data.reviews.toLocaleString(), `${data.review_hours} h studying`)}
        {tile({ kind: 'metric', m: 'tutor_messages' }, 'tutor messages',
              data.tutor_messages.toLocaleString(), `${data.feature_users.tutor} users`)}
        {tile({ kind: 'metric', m: 'readings' }, 'reader sessions',
              data.readings.toLocaleString(), `${data.feature_users.reader} users`)}
        {tile({ kind: 'metric', m: 'cards_started' }, 'cards started',
              data.cards_started.toLocaleString(), `+${data.new_users} new users`)}
      </div>

      {filter && (
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
                <Fragment key={u.id}>
                  <tr
                    className="border-t border-gray-50 text-gray-700 cursor-pointer hover:bg-gray-50"
                    onClick={() =>
                      setExpandedUser((cur) => (cur === u.id ? null : u.id))
                    }
                    aria-expanded={expandedUser === u.id}
                  >
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
                  {expandedUser === u.id && (
                    <tr data-testid="engagement-user-detail">
                      <td colSpan={7} className="py-1 pl-4 bg-gray-50/60">
                        {!userLangs ? (
                          <span className="text-gray-400">Loading…</span>
                        ) : userLangs.length === 0 ? (
                          <span className="text-gray-400">No per-language activity.</span>
                        ) : (
                          <table className="w-full text-[11px]">
                            <tbody>
                              {userLangs.map((l) => (
                                <tr key={l.code} className="text-gray-600">
                                  <td className="py-0.5 pr-2">{l.name}</td>
                                  <td className="py-0.5 pr-2 text-right tabular-nums">
                                    {l.cards_total} cards
                                  </td>
                                  <td className="py-0.5 pr-2 text-right tabular-nums">
                                    {l.reviews} reviews
                                    {l.review_minutes > 0 && ` · ${l.review_minutes}m`}
                                  </td>
                                  <td className="py-0.5 pr-2 text-right tabular-nums">
                                    {l.tutor_messages} tutor
                                  </td>
                                  <td className="py-0.5 pr-2 text-right tabular-nums">
                                    {l.readings} reads
                                  </td>
                                  <td className="py-0.5 text-right text-gray-400">
                                    last review {relativeDay(l.last_review)}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        )}
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
              {users && shownUsers.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-2 text-gray-400">
                    No users match this tile.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {data.top_languages.length > 0 && (
        <div>
          <h3 className="text-xs uppercase tracking-wide text-gray-400 mb-1">
            Most-studied languages
          </h3>
          <table className="w-full text-xs">
            <tbody>
              {data.top_languages.map((l) => (
                <tr
                  key={l.code}
                  className={
                    'border-t border-gray-50 text-gray-700 cursor-pointer ' +
                    (filter?.kind === 'language' && filter.code === l.code
                      ? 'bg-lang-soft'
                      : 'hover:bg-gray-50')
                  }
                  onClick={() => toggle({ kind: 'language', code: l.code })}
                  aria-pressed={filter?.kind === 'language' && filter.code === l.code}
                >
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
