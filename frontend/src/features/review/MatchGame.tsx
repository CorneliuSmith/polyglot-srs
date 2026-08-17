import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

/** How many pairs a board needs before the game is worth showing at all. */
export const MIN_GAME_PAIRS = 4
const ROUND_SIZE = 5

export interface Pair {
  word: string
  gloss: string
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

/**
 * Tap-to-match: words on the left, meanings shuffled on the right.
 *
 * Built for the trailblazer wait, where the pool is the very session being
 * waited for and grows as the translation loop fills. The Reader's wait
 * feeds it the learner's own due words instead — same game, and the
 * closest thing to "review while you wait" that fits in sixty seconds.
 */
export default function MatchGame({ pool }: { pool: Pair[] }) {
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
