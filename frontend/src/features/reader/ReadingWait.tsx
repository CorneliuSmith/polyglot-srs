import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { PenLine } from 'lucide-react'
import { getDueCards } from '../../api/review'
import MatchGame, { MIN_GAME_PAIRS } from '../review/MatchGame'
import type { Pair } from '../review/MatchGame'
import TriviaGame from '../review/TriviaGame'

/** Ask for the browser's permission to interrupt only at the moment the
 * learner chooses to wander off — never on page load. An unprompted
 * permission dialog is the most-ignored prompt on the web; asked when it
 * has just been made useful, it earns a yes. */
export function askToNotify() {
  try {
    if (typeof Notification === 'undefined') return
    if (Notification.permission === 'default') Notification.requestPermission()
  } catch {
    // Some embedded webviews throw on the call itself; the in-app banner
    // covers the learner either way.
  }
}

/**
 * The Reader's wait: what a learner does while their text is written.
 *
 * Generation got slower on purpose (#285 grades every text and rewrites
 * one that misses its contract), so this replaces a disabled "Writing…"
 * button with two real offers — play the word game, or go run reviews —
 * and the promise that makes leaving safe: the text finds them when it's
 * done (components/ReadingReadyBanner).
 */
export default function ReadingWait({
  languageId,
  topic,
}: {
  languageId: string
  topic: string
}) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [playing, setPlaying] = useState(false)
  const [noTrivia, setNoTrivia] = useState(false)

  // The learner's own due words — reviewing, in the shape of a game.
  // Only fetched once they ask to play: a wait nobody plays should cost
  // nothing.
  const { data: due = [] } = useQuery({
    queryKey: ['due-cards', languageId, 'wait-game'],
    queryFn: () => getDueCards(languageId, 20, 'vocabulary'),
    enabled: playing && !!languageId,
    staleTime: 60_000,
    retry: false,
  })

  const pool = useMemo<Pair[]>(() => {
    const seen = new Set<string>()
    const pairs: Pair[] = []
    for (const c of due) {
      const word = c.correct_answer
      const gloss = c.gloss || c.translation
      if (!word || !gloss || seen.has(word)) continue
      seen.add(word)
      pairs.push({ word, gloss })
    }
    return pairs
  }, [due])

  return (
    <div
      data-testid="reading-wait"
      className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-4 text-center"
    >
      <div className="space-y-1">
        <PenLine className="w-8 h-8 text-lang mx-auto animate-pulse" />
        <h2 className="font-semibold text-gray-800">
          {t('reader.wait.title', { topic })}
        </h2>
        <p className="text-xs text-gray-500">{t('reader.wait.body')}</p>
      </div>

      {playing && (
        <div className="flex justify-center">
          {pool.length >= MIN_GAME_PAIRS ? (
            <MatchGame pool={pool} />
          ) : !noTrivia ? (
            // Nothing due to match — the trivia bank is shared per locale
            // and stocked long before this learner arrived.
            <TriviaGame onEmpty={() => setNoTrivia(true)} />
          ) : (
            <p className="text-sm text-gray-500">{t('reader.wait.noGame')}</p>
          )}
        </div>
      )}

      <div className="flex flex-col sm:flex-row gap-2 justify-center">
        {!playing && (
          <button
            type="button"
            onClick={() => {
              setPlaying(true)
              askToNotify()
            }}
            className="px-5 py-2.5 rounded-lg bg-lang text-lang-on text-sm font-semibold hover:opacity-90"
          >
            {t('reader.wait.play')}
          </button>
        )}
        <button
          type="button"
          onClick={() => {
            // Leaving is the case the notification exists for, so this is
            // the moment worth spending the permission prompt on.
            askToNotify()
            navigate('/review')
          }}
          className={
            playing
              ? 'px-5 py-2 text-sm text-gray-500 hover:text-gray-700 underline'
              : 'px-5 py-2.5 rounded-lg border border-gray-300 bg-white text-sm font-semibold text-gray-700 hover:bg-gray-50'
          }
        >
          {t('reader.wait.review')}
        </button>
      </div>

      <p className="text-[11px] text-gray-500">{t('reader.wait.promise')}</p>
    </div>
  )
}
