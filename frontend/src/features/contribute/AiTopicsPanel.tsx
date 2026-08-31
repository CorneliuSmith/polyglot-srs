import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import {
  bulkConfirmTopics,
  bulkRejectTopics,
  confirmVocabTopic,
  getAiTopics,
  type AiTopicWord,
} from '../../api/contribute'
import { TOPIC_ORDER, inTopicOrder } from '../../lib/topics'
import { topicName } from '../decks/TopicDecks'

/**
 * Workspace › Review: the classifier's provisional semantic buckets
 * (docs/plans/topic-lens.md). Grouped BY BUCKET, because that is how a
 * reviewer actually works: read a bucket's words, fix the misfits with the
 * per-word selector, then sign the rest with one bulk confirm. Bulk reject
 * (per bucket, or everything) is the bad-run recovery — cleared words
 * re-queue for the next classification run.
 *
 * Trial reviewers see everything, flagged provisional; only full
 * reviewers/admins get the confirm and reject controls (server-enforced
 * either way). Hidden when nothing is pending.
 */

function WordRow({
  word,
  canPublish,
  onDone,
}: {
  word: AiTopicWord
  canPublish: boolean
  onDone: () => void
}) {
  const { t } = useTranslation()
  const [topic, setTopic] = useState(word.topic)
  const confirm = useMutation({
    mutationFn: () => confirmVocabTopic(word.id, topic),
    onSuccess: onDone,
  })
  return (
    <li className="flex items-center justify-between gap-3 py-2">
      <div className="min-w-0">
        <span className="text-sm font-medium text-gray-800">{word.word}</span>
        {word.part_of_speech && (
          <span className="ms-1 text-[11px] italic text-gray-500">
            {word.part_of_speech}
          </span>
        )}
        {word.definition && (
          <span className="block text-xs text-gray-500 truncate">
            {word.definition}
          </span>
        )}
      </div>
      {canPublish && (
        <div className="flex items-center gap-2 shrink-0">
          <select
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            aria-label={`Topic for ${word.word}`}
            className="max-w-40 rounded-lg border border-gray-300 px-2 py-1 text-xs"
          >
            {TOPIC_ORDER.map((slug) => (
              <option key={slug} value={slug}>{topicName(slug, t)}</option>
            ))}
            {/* The hidden buckets are assignable here even though they
                never render as decks — "the" belongs in grammar glue. */}
            <option value="abstract_general">{topicName('abstract_general', t)}</option>
            <option value="function_words">{topicName('function_words', t)}</option>
          </select>
          <button
            type="button"
            onClick={() => confirm.mutate()}
            disabled={confirm.isPending}
            className="rounded-md bg-green-600 text-white px-2 py-1 text-[11px] hover:bg-green-700 disabled:opacity-40"
          >
            Confirm
          </button>
        </div>
      )}
    </li>
  )
}

export default function AiTopicsPanel({ languageId }: { languageId: string }) {
  const { t } = useTranslation()
  const qc = useQueryClient()
  const [openBucket, setOpenBucket] = useState<string | null>(null)
  const { data } = useQuery({
    queryKey: ['ai-topics', languageId],
    queryFn: () => getAiTopics(languageId),
    enabled: !!languageId,
    retry: false,
  })
  const onDone = () =>
    qc.invalidateQueries({ queryKey: ['ai-topics', languageId] })

  const bulkConfirm = useMutation({
    mutationFn: (topic: string) => bulkConfirmTopics(languageId, topic),
    onSuccess: onDone,
  })
  const bulkReject = useMutation({
    mutationFn: (topic?: string) => bulkRejectTopics(languageId, topic),
    onSuccess: onDone,
  })

  const counts = data?.counts ?? []
  if (counts.length === 0) return null
  const canPublish = data?.can_publish ?? false
  const total = counts.reduce((n, c) => n + c.pending, 0)
  const byBucket = new Map<string, AiTopicWord[]>()
  for (const w of data?.words ?? []) {
    byBucket.set(w.topic, [...(byBucket.get(w.topic) ?? []), w])
  }

  return (
    <div
      className="bg-white rounded-2xl border border-gray-100 p-4 text-sm space-y-2"
      data-testid="ai-topics-panel"
    >
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="text-sm font-semibold text-gray-800">
          Topic buckets · awaiting confirmation
        </h2>
        <span className="text-xs text-amber-600">{total} pending</span>
      </div>
      <p className="text-xs text-gray-500">
        {canPublish
          ? 'The classifier sorted these words by meaning. Open a bucket, read its words, fix any misfits — then Confirm the bucket. Reject re-queues it for a fresh run.'
          : 'Provisional topic sorting from the classifier. A full reviewer confirms each bucket.'}
      </p>
      {canPublish && (
        <button
          type="button"
          onClick={() => {
            if (window.confirm(
              'Clear EVERY pending topic for this language? The words '
              + 're-queue for the next classification run.',
            )) bulkReject.mutate(undefined)
          }}
          disabled={bulkReject.isPending}
          data-testid="topics-reject-all"
          className="text-[11px] text-red-600 hover:underline disabled:opacity-40"
        >
          Reject the whole run
        </button>
      )}
      <ul className="divide-y divide-gray-50">
        {inTopicOrder(counts.map((c) => ({ ...c, topic: c.topic }))).map((c) => (
          <li key={c.topic} className="py-2">
            <div className="flex items-center justify-between gap-2">
              <button
                type="button"
                onClick={() =>
                  setOpenBucket(openBucket === c.topic ? null : c.topic)
                }
                aria-expanded={openBucket === c.topic}
                className="min-w-0 flex-1 text-start text-sm font-medium text-gray-800 hover:text-lang"
              >
                {topicName(c.topic, t)}
                <span className="ms-2 text-xs tabular-nums text-amber-600">
                  {c.pending}
                </span>
              </button>
              {canPublish && (
                <span className="flex items-center gap-1.5 shrink-0">
                  <button
                    type="button"
                    onClick={() => bulkConfirm.mutate(c.topic)}
                    disabled={bulkConfirm.isPending}
                    data-testid={`topics-confirm-${c.topic}`}
                    className="rounded-md bg-green-600 text-white px-2 py-1 text-[11px] hover:bg-green-700 disabled:opacity-40"
                  >
                    Confirm bucket
                  </button>
                  <button
                    type="button"
                    onClick={() => bulkReject.mutate(c.topic)}
                    disabled={bulkReject.isPending}
                    className="rounded-md border border-red-200 text-red-600 px-2 py-1 text-[11px] disabled:opacity-40"
                  >
                    Reject
                  </button>
                </span>
              )}
            </div>
            {openBucket === c.topic && (
              <ul className="mt-1 divide-y divide-gray-50 border-t border-gray-100">
                {(byBucket.get(c.topic) ?? []).map((w) => (
                  <WordRow
                    key={w.id}
                    word={w}
                    canPublish={canPublish}
                    onDone={onDone}
                  />
                ))}
              </ul>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}
