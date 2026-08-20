import { useQuery } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { getReviewNotifications } from '../api/contribute'
import type { Language } from '../api/types'

/** The shared review-work query. Keyed once so the picker, the bell and any
 * panel that wants a badge all read the same fetch. */
export function useReviewNotifications() {
  return useQuery({
    queryKey: ['review-notifications'],
    queryFn: getReviewNotifications,
    retry: false,
    // Review work arrives while you are looking at it. A minute is often
    // enough to notice a submission without polling the database flat.
    staleTime: 60_000,
    refetchInterval: 60_000,
  })
}

/**
 * The language a staff surface is scoped to, with the work waiting in each
 * one, and arrows to move between them.
 *
 * Owner: "You should easily be able to cycle through reviews for each
 * language… so the users do not have a bunch of clicks to give feedback."
 *
 * Three things make that true rather than merely possible:
 *
 *   - The counts are ON the options. Picking where to work next used to
 *     mean switching to a language and looking, one at a time; the number
 *     is in the list now, so the choice is made before the click.
 *   - The arrows step through every language in order, so working through
 *     all of them is a repeated single tap rather than a repeated
 *     open-menu-find-next-select.
 *   - It writes the WORKSPACE language, never the study language. Reviewing
 *     Hebrew no longer changes what you are learning, so there is no third
 *     click to put it back.
 */
export default function LanguageScopePicker({
  languages,
  value,
  onChange,
  label = 'Working language',
}: {
  languages: Language[]
  value: string | null
  onChange: (languageId: string) => void
  label?: string
}) {
  const { data } = useReviewNotifications()
  const waiting = new Map(
    (data?.languages ?? []).map((l) => [l.id, l.total]),
  )

  if (languages.length === 0) return null

  const index = languages.findIndex((l) => l.id === value)
  // Wrap rather than disable at the ends: cycling is the verb the owner
  // used, and a disabled arrow at the last language means noticing you are
  // at the end and reaching for the other one.
  const step = (delta: number) => {
    const from = index < 0 ? 0 : index
    const next = (from + delta + languages.length) % languages.length
    onChange(languages[next].id)
  }

  // Somewhere else has work and here doesn't: the one case where "next" is
  // not what you want, because the next language might be quiet too.
  const elsewhere = (data?.languages ?? [])
    .filter((l) => l.id !== value && l.total > 0)
    .sort((a, b) => b.total - a.total)
  const here = waiting.get(value ?? '') ?? 0

  return (
    <div className="flex min-w-0 items-center gap-1">
      <button
        type="button"
        onClick={() => step(-1)}
        aria-label="Previous language"
        data-testid="scope-prev"
        className="shrink-0 rounded-lg border border-gray-200 p-1 text-gray-500 hover:text-lang hover:border-lang/40"
      >
        <ChevronLeft aria-hidden className="h-4 w-4 rtl:rotate-180" />
      </button>
      <select
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value)}
        aria-label={label}
        data-testid="scope-select"
        title="Everything on this page applies to this language"
        className="min-w-0 rounded-lg border border-gray-200 bg-white px-2 py-1 text-lg font-semibold text-gray-900"
      >
        {languages.map((l) => {
          const n = waiting.get(l.id) ?? 0
          return (
            <option key={l.id} value={l.id}>
              {l.name}
              {l.is_visible ? '' : ' (hidden)'}
              {n > 0 ? ` · ${n} waiting` : ''}
            </option>
          )
        })}
      </select>
      <button
        type="button"
        onClick={() => step(1)}
        aria-label="Next language"
        data-testid="scope-next"
        className="shrink-0 rounded-lg border border-gray-200 p-1 text-gray-500 hover:text-lang hover:border-lang/40"
      >
        <ChevronRight aria-hidden className="h-4 w-4 rtl:rotate-180" />
      </button>
      {here === 0 && elsewhere.length > 0 && (
        <button
          type="button"
          onClick={() => onChange(elsewhere[0].id)}
          data-testid="scope-jump"
          title={`${elsewhere[0].total} waiting in ${elsewhere[0].name}`}
          className="shrink-0 rounded-full border border-amber-300 bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-900 hover:bg-amber-100"
        >
          {elsewhere[0].name} · {elsewhere[0].total}
        </button>
      )}
    </div>
  )
}
