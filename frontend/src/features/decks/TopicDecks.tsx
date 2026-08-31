import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { getTopicSummary, type TopicDeck } from '../../api/review'
import { inTopicOrder } from '../../lib/topics'

/**
 * The Topic Lens's learner surface (docs/plans/topic-lens.md): the same
 * learnable pool the level decks show, re-grouped by meaning. Everything
 * here is virtual — no ids, no detail pages, no subscription of its own —
 * so the one action a topic deck offers is Learn.
 *
 * The toggle that swaps views lives in the PARENTS (Decks page, dashboard
 * deck panel), because it switches between their existing level content
 * and these components; `useTopicDecks` is what tells a parent whether to
 * offer the toggle at all. No topics — no toggle: a course whose sorting
 * hasn't run (or, under strict policy, isn't confirmed) looks exactly
 * like today.
 */

export function useTopicDecks(languageId: string | null) {
  const { data = [], isLoading } = useQuery({
    queryKey: ['topic-decks', languageId],
    queryFn: () => getTopicSummary(languageId!),
    enabled: !!languageId,
    retry: false,
    staleTime: 5 * 60 * 1000,
  })
  return { topics: inTopicOrder(data), hasTopics: data.length > 0, isLoading }
}

export function DeckViewToggle({
  view,
  onChange,
}: {
  view: 'level' | 'topic'
  onChange: (view: 'level' | 'topic') => void
}) {
  const { t } = useTranslation()
  return (
    <div
      className="flex rounded-lg border border-gray-200 bg-white overflow-hidden text-xs w-fit"
      role="tablist"
      aria-label={t('decks.viewToggle')}
      data-testid="deck-view-toggle"
    >
      {(
        [
          ['level', t('decks.byLevel')],
          ['topic', t('decks.byTopic')],
        ] as const
      ).map(([key, label]) => (
        <button
          key={key}
          type="button"
          role="tab"
          aria-selected={view === key}
          onClick={() => onChange(key)}
          className={`px-3 py-1.5 font-medium transition-colors ${
            view === key
              ? 'bg-lang text-lang-on'
              : 'text-gray-500 hover:bg-gray-50'
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  )
}

export function topicName(
  topic: string,
  t: (key: string, opts?: Record<string, unknown>) => string,
): string {
  // defaultValue: a server ahead of this bundle renders its new slug as
  // readable words instead of a raw key or a crash.
  return t(`decks.topics.${topic}`, {
    defaultValue: topic.split('_').join(' '),
  })
}

/** Compact rows for the dashboard's deck panel. */
export function TopicDeckRows({
  topics,
  onLearn,
}: {
  topics: TopicDeck[]
  onLearn: (topic: string) => void
}) {
  const { t } = useTranslation()
  return (
    <>
      {topics.map((row) => {
        const done = row.total > 0 && row.learned >= row.total
        return (
          <div
            key={row.topic}
            className="border-t border-gray-100 first:border-t-0 flex items-center justify-between gap-3 px-4 py-3"
            data-testid={`topic-row-${row.topic}`}
          >
            <span className="min-w-0 truncate text-sm font-medium text-gray-800">
              {topicName(row.topic, t)}
            </span>
            <span className="flex items-center gap-2 shrink-0">
              <span className="text-xs tabular-nums text-gray-500">
                {Math.min(row.learned, row.total)} / {row.total}
              </span>
              <button
                type="button"
                onClick={() => onLearn(row.topic)}
                disabled={done}
                title={
                  done
                    ? t('dashboard.deckComplete')
                    : t('dashboard.startLearningDeck')
                }
                className="rounded-lg bg-lang hover:bg-lang-dark disabled:opacity-40 text-lang-on text-xs font-semibold px-3 py-1.5"
              >
                {t('dashboard.deckLearn')}
              </button>
            </span>
          </div>
        )
      })}
    </>
  )
}

/** Card grid for the Decks page. */
export function TopicDeckCards({
  topics,
  onLearn,
}: {
  topics: TopicDeck[]
  onLearn: (topic: string) => void
}) {
  const { t } = useTranslation()
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      {topics.map((row) => {
        const pct =
          row.total > 0
            ? Math.min(100, Math.round((row.learned / row.total) * 100))
            : 0
        const done = row.total > 0 && row.learned >= row.total
        return (
          <div
            key={row.topic}
            className="bg-white rounded-2xl shadow-sm border border-gray-100 p-4"
            data-testid={`topic-card-${row.topic}`}
          >
            <p className="text-sm font-semibold text-gray-800">
              {topicName(row.topic, t)}
            </p>
            <p className="text-xs text-gray-500 mt-0.5">
              {t('decks.learnedRatio', {
                learned: Math.min(row.learned, row.total),
                total: row.total,
              })}
            </p>
            <div className="mt-2 w-full bg-gray-100 rounded-full h-1.5">
              <div
                className="h-1.5 rounded-full bg-lang"
                style={{ width: `${pct}%` }}
              />
            </div>
            <button
              type="button"
              onClick={() => onLearn(row.topic)}
              disabled={done}
              className="mt-3 rounded-lg bg-lang hover:bg-lang-dark disabled:opacity-40 text-lang-on text-xs font-semibold px-3 py-1.5"
            >
              {t('dashboard.deckLearn')}
            </button>
          </div>
        )
      })}
    </div>
  )
}
