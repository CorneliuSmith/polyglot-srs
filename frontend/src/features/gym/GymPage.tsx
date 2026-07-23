import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getGymManifest, generateGymDrills } from '../../api/gym'
import type { GymEntry } from '../../api/gym'
import { usePrefsStore } from '../../stores/prefsStore'

/** The Gym (WP25): pick the FORMS to train — present, past perfect,
 * accusative… — never individual words, then drill them through a mixed
 * cram session (ungraded; misses don't touch the SRS schedule).
 *
 * Hovering (or focusing) a category shows an example sentence plus a
 * plain-language line on when the form is used. Categories the learner
 * already has in reviews are marked and listed first — cover familiar
 * ground, then expand. "Include non-standard words" reveals the
 * categories that break or sit outside the regular patterns.
 */
const MAX_SELECTED = 12 // the cram endpoint's point cap
const COUNT_OPTIONS = [10, 20, 30, 50] as const
const MAX_COUNT = 100 // the cram endpoint's hard cap

function sortFamiliarFirst(entries: GymEntry[]): GymEntry[] {
  return [...entries].sort((a, b) => Number(b.familiar) - Number(a.familiar))
}

export default function GymPage() {
  const navigate = useNavigate()
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [nonstandard, setNonstandard] = useState(false)
  const [count, setCount] = useState<number>(20)
  // WP41: opt-in on-demand generation. OFF by default — the seeded corpus
  // (forms × many sentences) is the main path; this tops up variety and
  // spends a tutor message, so the learner turns it on knowingly.
  const [generate, setGenerate] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [genError, setGenError] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['gym-manifest', activeLanguageId],
    queryFn: () => getGymManifest(activeLanguageId!),
    enabled: !!activeLanguageId,
  })

  const columns = data?.columns ?? []
  const hasNonstandard = columns.some((c) =>
    c.entries.some((e) => e.nonstandard),
  )

  const toggle = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else if (next.size < MAX_SELECTED) next.add(id)
      return next
    })

  const toggleNonstandard = (on: boolean) => {
    setNonstandard(on)
    if (!on) {
      // Hidden categories can't stay silently selected.
      const hidden = new Set(
        columns.flatMap((c) =>
          c.entries.filter((e) => e.nonstandard).map((e) => e.point_id),
        ),
      )
      setSelected((prev) => new Set([...prev].filter((id) => !hidden.has(id))))
    }
  }

  // How many drills the chosen forms can actually supply right now — the
  // session caps here (generating beyond this is a planned follow-up).
  const available = columns
    .flatMap((c) => c.entries)
    .filter((e) => selected.has(e.point_id))
    .reduce((sum, e) => sum + (e.drills || 0), 0)
  const short = selected.size > 0 && count > available

  const goToCram = () =>
    navigate(`/cram?points=${[...selected].join(',')}&mix=1&count=${count}`)

  const start = async () => {
    if (selected.size === 0 || generating) return
    // Only spend a message when we're actually short and the learner opted in;
    // otherwise the seeded pool already covers the requested count.
    if (generate && short) {
      setGenerating(true)
      setGenError(null)
      try {
        await generateGymDrills([...selected])
      } catch (err: unknown) {
        const status = (err as { response?: { status?: number } })?.response
          ?.status
        setGenerating(false)
        if (status === 402) {
          setGenError(
            "You're out of tutor messages for now — starting with the sentences we already have.",
          )
        } else if (status === 503) {
          setGenError(
            'Fresh generation is off right now — starting with what we have.',
          )
        } else {
          setGenError('Could not generate more — starting with what we have.')
        }
        goToCram()
        return
      }
      setGenerating(false)
    }
    goToCram()
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-3xl mx-auto px-4 py-8 space-y-5">
        <div className="flex items-center justify-between">
          <header>
            <h1 className="text-2xl font-bold text-gray-900">The Gym</h1>
            <p className="text-sm text-gray-500">
              Pick the forms to train — hover one to see how it's used. Your
              session mixes everything you pick.
            </p>
          </header>
          <button
            type="button"
            onClick={() => navigate('/')}
            className="text-sm text-lang hover:underline"
          >
            ← Dashboard
          </button>
        </div>

        {isLoading && <p className="text-sm text-gray-400">Loading…</p>}

        {!isLoading && columns.length === 0 && (
          <div className="bg-white rounded-2xl border border-gray-100 p-6 text-sm text-gray-500">
            This language doesn't bend its words enough to need a gym — there
            are no conjugation or declension forms to train here yet.
          </div>
        )}

        {columns.length > 0 && (
          <>
            <div
              className={
                'grid gap-4 ' +
                (columns.length >= 3
                  ? 'sm:grid-cols-3'
                  : columns.length === 2
                    ? 'sm:grid-cols-2'
                    : '')
              }
            >
              {columns.map((col) => {
                const entries = sortFamiliarFirst(col.entries).filter(
                  (e) => nonstandard || !e.nonstandard,
                )
                if (entries.length === 0) return null
                return (
                  <section
                    key={col.kind}
                    className="bg-white rounded-2xl border border-gray-100 p-4"
                  >
                    <h2 className="text-xs uppercase tracking-wide text-gray-400 mb-3">
                      {col.label}
                    </h2>
                    <div className="space-y-2">
                      {entries.map((e) => (
                        <div key={e.point_id} className="relative group">
                          <button
                            type="button"
                            onClick={() => toggle(e.point_id)}
                            aria-pressed={selected.has(e.point_id)}
                            className={
                              'w-full rounded-xl border px-3 py-2 text-left text-sm transition-colors ' +
                              (selected.has(e.point_id)
                                ? 'border-lang bg-lang-soft text-gray-900'
                                : 'border-gray-200 bg-white text-gray-700 hover:border-lang/50')
                            }
                            style={{ minHeight: '44px' }}
                          >
                            <span className="flex items-center justify-between gap-2">
                              <span className="font-medium">{e.label}</span>
                              <span className="flex items-center gap-1 text-[10px] text-gray-400">
                                {e.familiar && (
                                  <span
                                    className="rounded-full bg-lang-soft text-lang px-1.5 py-0.5"
                                    title="Already in your reviews"
                                  >
                                    known
                                  </span>
                                )}
                                {e.level}
                              </span>
                            </span>
                          </button>
                          {/* Hover/focus preview: what the form does + one
                              real example, BEFORE committing to it. */}
                          {(e.usage || e.example) && (
                            <div
                              role="tooltip"
                              className="pointer-events-none absolute left-0 right-0 top-full z-10 mt-1 hidden rounded-xl border border-gray-200 bg-white p-3 text-xs shadow-lg group-hover:block group-focus-within:block"
                            >
                              {e.usage && (
                                <p className="text-gray-600">{e.usage}</p>
                              )}
                              {e.example && (
                                <p className="mt-1 text-gray-400">{e.example}</p>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </section>
                )
              })}
            </div>

            {/* How many questions — a real gym isn't three reps. */}
            <div className="bg-white rounded-2xl border border-gray-100 p-4 space-y-2">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
                <span className="text-sm font-medium text-gray-700">
                  How many questions?
                </span>
                <div className="flex rounded-lg border border-gray-200 overflow-hidden text-sm">
                  {COUNT_OPTIONS.map((n) => (
                    <button
                      key={n}
                      type="button"
                      onClick={() => setCount(n)}
                      aria-pressed={count === n}
                      className={`px-3 py-1.5 tabular-nums transition-colors ${
                        count === n
                          ? 'bg-lang text-lang-on'
                          : 'bg-white text-gray-600 hover:bg-gray-50'
                      }`}
                      style={{ minHeight: '40px' }}
                    >
                      {n}
                    </button>
                  ))}
                </div>
                <label className="flex items-center gap-1.5 text-sm text-gray-500">
                  <span className="sr-only">Custom count</span>
                  or
                  <input
                    type="number"
                    min={1}
                    max={MAX_COUNT}
                    value={count}
                    onChange={(e) => {
                      const v = Math.round(Number(e.target.value))
                      if (Number.isFinite(v)) setCount(Math.max(1, Math.min(MAX_COUNT, v)))
                    }}
                    aria-label="Number of questions"
                    className="w-16 rounded-lg border border-gray-200 px-2 py-1.5 text-sm tabular-nums"
                  />
                </label>
              </div>
              {short && !generate && (
                <p className="text-xs text-amber-600">
                  These forms have {available} question{available === 1 ? '' : 's'} to
                  draw from — you&apos;ll get {available} this round. Pick more forms, or
                  turn on fresh variations below to top up.
                </p>
              )}
              {short && generate && (
                <p className="text-xs text-amber-600">
                  Only {available} ready for this session. We&apos;ll draft a few fresh
                  ones — they go to a reviewer first, so they grow the corpus for
                  next time rather than this run. Uses your tutor allowance: about
                  one message per form (up to 3), and it stops early if you&apos;re
                  low so it never overdraws.
                </p>
              )}

              {/* Opt-in generation. Warn BEFORE they commit — the toggle itself
                  carries the cost + review note ("let them know early"). */}
              <label className="flex items-start gap-2 pt-1 text-sm text-gray-600 select-none">
                <input
                  type="checkbox"
                  checked={generate}
                  onChange={(e) => setGenerate(e.target.checked)}
                  className="mt-0.5 rounded border-gray-300"
                />
                <span>
                  Help grow this form when it runs thin
                  <span className="block text-xs text-gray-400">
                    Drafts a few new drills for the forms you picked. They&apos;re
                    checked, then wait for a reviewer before joining the corpus —
                    so they enrich future sessions, not this one. Spends a little of
                    your tutor allowance (about one message per form).
                  </span>
                </span>
              </label>
              {genError && <p className="text-xs text-amber-600">{genError}</p>}
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3">
              {hasNonstandard ? (
                <label className="flex items-center gap-2 text-sm text-gray-600 select-none">
                  <input
                    type="checkbox"
                    checked={nonstandard}
                    onChange={(event) => toggleNonstandard(event.target.checked)}
                    className="rounded border-gray-300"
                  />
                  Include non-standard words
                </label>
              ) : (
                <span />
              )}
              <button
                type="button"
                onClick={start}
                disabled={selected.size === 0 || generating}
                className="bg-lang hover:bg-lang-dark disabled:opacity-40 text-lang-on font-semibold rounded-xl px-6 py-3 text-sm"
                style={{ minHeight: '44px' }}
              >
                {generating
                  ? 'Generating…'
                  : selected.size === 0
                    ? 'Pick at least one form'
                    : `Start training · ${Math.min(count, available || count)} question${Math.min(count, available || count) === 1 ? '' : 's'}`}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
