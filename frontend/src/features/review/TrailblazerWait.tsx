import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Compass, Sparkles } from 'lucide-react'
import { getSessionReadiness } from '../../api/review'
import type { SessionReadiness } from '../../api/types'

/** How many pairs the match game needs before it's worth showing. Below
 * this the screen is animation + progress only — anything else we could
 * show would be English, which is what the learner chose to wait out. */
const MIN_GAME_PAIRS = 4
const ROUND_SIZE = 5

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
  /** The support language's display name, for the headline. */
  localeName?: string
}

/** Deterministic-enough shuffle for a game round. */
function shuffle<T>(arr: T[]): T[] {
  const out = [...arr]
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[out[i], out[j]] = [out[j], out[i]]
  }
  return out
}

interface Pair {
  word: string
  gloss: string
}

/** Tap-to-match: the words of the very session being waited for, in the
 * slice of it that has already landed in the learner's language. The pool
 * grows as the loop fills — the longer the wait, the richer the game — and
 * every match is a word the learner meets for real minutes later. */
function MatchGame({ pool }: { pool: Pair[] }) {
  const { t } = useTranslation()
  const [roundPairs, setRoundPairs] = useState<Pair[]>([])
  const [glossOrder, setGlossOrder] = useState<Pair[]>([])
  const [matched, setMatched] = useState<Set<string>>(new Set())
  const [pickedWord, setPickedWord] = useState<string | null>(null)
  const [shakeWord, setShakeWord] = useState<string | null>(null)
  const [score, setScore] = useState(0)

  // New round whenever the current one is cleared (or on first pool).
  const roundDone = roundPairs.length > 0 && matched.size >= roundPairs.length
  useEffect(() => {
    if (roundPairs.length > 0 && !roundDone) return
    if (pool.length < 2) return
    const next = shuffle(pool).slice(0, ROUND_SIZE)
    // Let a cleared board breathe for a beat before the next one.
    const timer = window.setTimeout(
      () => {
        setRoundPairs(next)
        setGlossOrder(shuffle(next))
        setMatched(new Set())
        setPickedWord(null)
      },
      roundDone ? 600 : 0,
    )
    return () => window.clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roundDone, roundPairs.length, pool.length])

  const tapGloss = (p: Pair) => {
    if (!pickedWord || matched.has(p.word)) return
    if (p.word === pickedWord) {
      setMatched((prev) => new Set(prev).add(p.word))
      setScore((n) => n + 1)
      setPickedWord(null)
    } else {
      setShakeWord(pickedWord)
      window.setTimeout(() => setShakeWord(null), 350)
      setPickedWord(null)
    }
  }

  const cell =
    'w-full rounded-lg border px-3 py-2 text-sm font-medium transition-all duration-150 text-center'

  return (
    <div data-testid="match-game" className="w-full max-w-sm space-y-3">
      <p className="text-xs text-gray-500 text-center">
        {t('trailblazer.gameHint')}
        {score > 0 && (
          <span className="ms-2 text-lang font-semibold">
            {t('trailblazer.matched', { count: score })}
          </span>
        )}
      </p>
      <div className="grid grid-cols-2 gap-2">
        <div className="space-y-2">
          {roundPairs.map((p) => (
            <button
              key={p.word}
              type="button"
              disabled={matched.has(p.word)}
              onClick={() => setPickedWord(p.word)}
              className={`${cell} ${
                matched.has(p.word)
                  ? 'border-green-300 bg-green-50 text-green-600 opacity-60'
                  : pickedWord === p.word
                    ? 'border-lang bg-lang/10 text-lang'
                    : 'border-gray-200 bg-white text-gray-800 hover:border-lang/50'
              } ${shakeWord === p.word ? 'animate-pulse border-red-300' : ''}`}
            >
              {p.word}
            </button>
          ))}
        </div>
        <div className="space-y-2">
          {glossOrder.map((p) => (
            <button
              key={p.gloss + p.word}
              type="button"
              disabled={matched.has(p.word)}
              onClick={() => tapGloss(p)}
              className={`${cell} ${
                matched.has(p.word)
                  ? 'border-green-300 bg-green-50 text-green-600 opacity-60'
                  : 'border-gray-200 bg-white text-gray-700 hover:border-lang/50'
              }`}
            >
              {p.gloss}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

/** The trailblazer wait: shown when a session's content hasn't been written
 * in the learner's language yet. Checking readiness is itself what primes
 * the translation queue server-side, so opening this screen starts the
 * fill. Auto-advances the moment the lane crosses the threshold; "Start in
 * English" is always one tap away — nobody is ever held here. */
export default function TrailblazerWait({
  languageId,
  kind,
  limit,
  onStart,
  localeName,
}: Props) {
  const { t } = useTranslation()
  const [waiting, setWaiting] = useState(false)

  const readiness = useQuery<SessionReadiness>({
    queryKey: ['session-readiness', languageId, kind, limit],
    queryFn: () => getSessionReadiness(languageId, limit),
    refetchInterval: 5000,
    retry: 1,
  })

  const lane = readiness.data?.[kind]
  const pct = lane ? Math.round(lane.pct * 100) : 0

  // The wait must never be what blocks a session: a failed readiness check
  // or a lane that's already over the bar both mean "just start".
  const shouldStart = readiness.isError || (lane != null && lane.ready_enough)
  useEffect(() => {
    if (shouldStart) onStart()
  }, [shouldStart, onStart])

  const pool = useMemo(() => readiness.data?.pairs ?? [], [readiness.data])

  if (!readiness.data || shouldStart) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-500">{t('learnSession.preparing')}</p>
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
            {t('trailblazer.progress', { pct })}
          </p>
        </div>

        {waiting && pool.length >= MIN_GAME_PAIRS ? (
          <div className="flex justify-center">
            <MatchGame pool={pool} />
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
      </div>
    </div>
  )
}
