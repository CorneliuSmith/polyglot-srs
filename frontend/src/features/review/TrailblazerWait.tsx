import { useEffect, useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { ArrowLeft, Compass, Sparkles } from 'lucide-react'
import { getSessionReadiness } from '../../api/review'
import type { SessionReadiness } from '../../api/types'
import MatchGame, { MIN_GAME_PAIRS } from './MatchGame'
import TriviaGame from './TriviaGame'

/** No new rows in this long and the fill isn't happening — say so rather
 * than leaving someone watching a bar that will never move. */
const STALL_AFTER_MS = 45_000

interface Props {
  languageId: string
  /** Which lane gates this session. */
  kind: 'learn' | 'review'
  /** The session size, so readiness measures the batch actually coming. */
  limit?: number
  /** Fires when the session should begin: the learner clicked "Start in
   * English", or readiness crossed the threshold, or readiness itself
   * failed (the wait must never be what blocks a session). */
  onStart: () => void
  /** Leaves the session entirely. Required, not optional: the tab bar is
   * hidden on session routes, so without this the screen is a dead end —
   * a learner who wants neither to wait nor to read English has nowhere
   * to go but the browser's Back button, and on the native shells not
   * even that. */
  onExit: () => void
  /** The support language's display name, for the headline. */
  localeName?: string
  /** Overridable so a test can exercise the real stall path without
   * waiting 45 seconds or fighting the poll interval with fake timers. */
  stallAfterMs?: number
}

/** The trailblazer wait: shown when a session's content hasn't been written
 * in the learner's language yet. Checking readiness is itself what primes
 * the translation queue server-side, so opening this screen starts the
 * fill. Auto-advances the moment the lane crosses the threshold; "Start in
 * English" is always one tap away, and so is leaving altogether — nobody
 * is ever held here. */
export default function TrailblazerWait({
  languageId,
  kind,
  limit,
  onStart,
  onExit,
  localeName,
  stallAfterMs = STALL_AFTER_MS,
}: Props) {
  const { t } = useTranslation()
  const [waiting, setWaiting] = useState(false)

  // A wait that never moves has to say so. Sitting at "0 % ready" forever
  // is indistinguishable from a hang, and the causes (no provider key, the
  // course switched off, an empty budget) are all invisible from here.
  const [stalled, setStalled] = useState(false)
  // Trivia is the fallback when this session has nothing to play with yet.
  // If its bank is empty too, fall through to plain progress rather than
  // showing an empty frame.
  const [noTrivia, setNoTrivia] = useState(false)
  // Starts at 0, not -1: a lane reporting zero ready rows is not progress,
  // and treating it as such armed nothing on the first poll — the wait sat
  // at 0% forever without ever admitting it had stopped.
  const highWater = useRef(0)
  const lastProgressAt = useRef(Date.now())

  const readiness = useQuery<SessionReadiness>({
    queryKey: ['session-readiness', languageId, kind, limit],
    queryFn: () => getSessionReadiness(languageId, limit),
    refetchInterval: 5000,
    retry: 1,
  })

  const lane = readiness.data?.[kind]
  // The bar tracks the thing that actually opens the gate: cards you could
  // start on. Showing the whole-batch percentage instead meant someone sat
  // watching "5 %" with no idea they were one card from being let in — and
  // that number climbs slowest precisely because example sentences, which
  // are the bulk of it, are translated last.
  const needed = lane?.start_cards ?? 0
  const have = Math.min(lane?.cards_ready ?? 0, needed)
  const pct = needed > 0
    ? Math.round((have / needed) * 100)
    : lane
      ? Math.round(lane.pct * 100)
      : 0

  // Keyed on the COUNT and the fetch timestamp, not on `lane` itself:
  // react-query's structural sharing keeps the object referentially stable
  // when a poll returns identical data, so depending on the object meant
  // the effect never re-ran and progress was never recorded.
  const readyCount = lane?.ready
  const fetchedAt = readiness.dataUpdatedAt
  useEffect(() => {
    if (readyCount == null) return
    if (readyCount > highWater.current) {
      highWater.current = readyCount
      lastProgressAt.current = Date.now()
      setStalled(false)
    }
  }, [readyCount, fetchedAt])

  // The stall check runs on its OWN clock, deliberately not keyed to the
  // query. Armed inside the effect above, every 5-second poll tore the
  // 45-second timer down and started a fresh one, so it could never reach
  // its own deadline: a fill that had genuinely stopped sat there
  // indefinitely without ever saying so, which is exactly the case this
  // exists to report.
  useEffect(() => {
    const tick = window.setInterval(() => {
      if (Date.now() - lastProgressAt.current >= stallAfterMs) setStalled(true)
    }, Math.min(1000, stallAfterMs))
    return () => window.clearInterval(tick)
  }, [stallAfterMs])

  // The wait must never be what blocks a session: a failed readiness check
  // or a lane that's already over the bar both mean "just start".
  const shouldStart = readiness.isError || (lane != null && lane.ready_enough)
  useEffect(() => {
    if (shouldStart) onStart()
  }, [shouldStart, onStart])

  const pool = useMemo(() => readiness.data?.pairs ?? [], [readiness.data])

  if (!readiness.data || shouldStart) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center gap-4">
        <p className="text-gray-500">{t('learnSession.preparing')}</p>
        {/* A readiness check that never answers used to leave the learner
            on a bare "preparing…" with nothing to press. */}
        {!shouldStart && (
          <button
            type="button"
            onClick={onExit}
            data-testid="trailblazer-exit"
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
          >
            <ArrowLeft className="w-3.5 h-3.5 rtl:rotate-180" />
            {t('trailblazer.leave')}
          </button>
        )}
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="w-full max-w-md text-center space-y-6 py-10">
        <div className="relative inline-block">
          <Compass className="w-14 h-14 text-lang animate-[spin_6s_linear_infinite]" />
          <Sparkles className="w-5 h-5 text-amber-400 absolute -top-1 -end-2" />
        </div>
        <div className="space-y-2">
          <h1 className="text-xl font-bold text-gray-900">
            {t('trailblazer.title')}
          </h1>
          <p className="text-sm text-gray-600">
            {localeName
              ? t('trailblazer.body', { language: localeName })
              : t('trailblazer.bodyGeneric')}
          </p>
        </div>

        <div className="space-y-1.5">
          <div
            className="h-2.5 w-full rounded-full bg-gray-200 overflow-hidden"
            role="progressbar"
            aria-valuenow={pct}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div
              className="h-full rounded-full bg-lang transition-all duration-700"
              style={{ width: `${pct}%` }}
            />
          </div>
          <p className="text-xs text-gray-500">
            {needed > 0
              ? t('trailblazer.cardsReady', { have, needed })
              : t('trailblazer.progress', { pct })}
          </p>
          {stalled && (
            <p className="text-xs text-amber-700" data-testid="trailblazer-stalled">
              {t('trailblazer.stalled')}
            </p>
          )}
        </div>

        {waiting && pool.length >= MIN_GAME_PAIRS ? (
          // Enough of the session has landed to play with the real thing.
          <div className="flex justify-center">
            <MatchGame pool={pool} />
          </div>
        ) : waiting && !noTrivia ? (
          // Nothing of this session yet — but the trivia bank is shared per
          // locale, so it was stocked long before this learner arrived.
          <div className="flex justify-center">
            <TriviaGame onEmpty={() => setNoTrivia(true)} />
          </div>
        ) : waiting ? (
          <p className="text-sm text-gray-500">{t('trailblazer.firstWords')}</p>
        ) : null}

        <div className="flex flex-col sm:flex-row gap-2 justify-center">
          {!waiting && (
            <button
              type="button"
              onClick={() => setWaiting(true)}
              className="px-5 py-2.5 rounded-lg bg-lang text-white text-sm font-semibold hover:opacity-90"
            >
              {t('trailblazer.waitAndPlay')}
            </button>
          )}
          <button
            type="button"
            onClick={onStart}
            className={
              waiting
                ? 'px-5 py-2 text-sm text-gray-500 hover:text-gray-700 underline'
                : 'px-5 py-2.5 rounded-lg border border-gray-300 bg-white text-sm font-semibold text-gray-700 hover:bg-gray-50'
            }
          >
            {t('trailblazer.startInEnglish')}
          </button>
        </div>

        {/* Neither waiting nor starting is a choice someone has to be
            argued out of. The tab bar is hidden on session routes, so this
            is the only way back — quiet, but always there. */}
        <button
          type="button"
          onClick={onExit}
          data-testid="trailblazer-exit"
          className="mx-auto flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
        >
          <ArrowLeft className="w-3.5 h-3.5 rtl:rotate-180" />
          {t('trailblazer.leave')}
        </button>
      </div>
    </div>
  )
}
