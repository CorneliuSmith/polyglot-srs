import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getAiLevels,
  confirmVocabLevel,
  type AiLeveledWord,
} from '../../api/contribute'

const LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'] as const

function LevelRow({
  word,
  canPublish,
  onDone,
}: {
  word: AiLeveledWord
  canPublish: boolean
  onDone: () => void
}) {
  const [level, setLevel] = useState(word.level ?? 'A1')
  const confirm = useMutation({
    mutationFn: () => confirmVocabLevel(word.id, level),
    onSuccess: onDone,
  })
  return (
    <li className="flex items-center justify-between gap-3 py-2">
      <div className="min-w-0">
        <span className="text-sm font-medium text-gray-800">{word.word}</span>
        {word.part_of_speech && (
          <span className="ml-1 text-[11px] italic text-gray-400">
            {word.part_of_speech}
          </span>
        )}
        {word.definition && (
          <span className="block text-xs text-gray-500 truncate">
            {word.definition}
          </span>
        )}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {canPublish ? (
          <>
            <select
              value={level}
              onChange={(e) => setLevel(e.target.value)}
              aria-label={`Level for ${word.word}`}
              className="rounded-lg border border-gray-300 px-2 py-1 text-xs"
            >
              {LEVELS.map((l) => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => confirm.mutate()}
              disabled={confirm.isPending}
              className="rounded-md bg-green-600 text-white px-2 py-1 text-[11px] hover:bg-green-700 disabled:opacity-40"
            >
              Confirm
            </button>
          </>
        ) : (
          <span className="text-[11px] uppercase tracking-wide rounded bg-amber-50 text-amber-600 px-1.5 py-0.5">
            provisional {word.level}
          </span>
        )}
      </div>
    </li>
  )
}

/**
 * Contributor › Review: words carrying a provisional AI-estimated CEFR level.
 * A reviewer confirms or adjusts each — which also finalises its deck placement
 * (decks resolve by level). Trial reviewers see them, flagged provisional.
 * Hidden when there are none.
 */
export default function AiLevelsPanel({ languageId }: { languageId: string }) {
  const qc = useQueryClient()
  const { data } = useQuery({
    queryKey: ['ai-levels', languageId],
    queryFn: () => getAiLevels(languageId),
    enabled: !!languageId,
    retry: false,
  })
  const onDone = () => qc.invalidateQueries({ queryKey: ['ai-levels', languageId] })

  const words = data?.words
  if (!words || words.length === 0) return null

  return (
    <div
      className="bg-white rounded-2xl border border-gray-100 p-4 text-sm space-y-2"
      data-testid="ai-levels-panel"
    >
      <div className="flex items-baseline justify-between">
        <h2 className="text-sm font-semibold text-gray-800">
          AI-estimated levels · awaiting confirmation
        </h2>
        <span className="text-xs text-amber-600">{words.length} pending</span>
      </div>
      <p className="text-xs text-gray-500">
        {data?.can_publish
          ? 'These words had no frequency-based level, so the model estimated one. Confirm or adjust each — that also places it in the matching deck.'
          : 'These words carry a provisional AI-estimated level. A full reviewer confirms them.'}
      </p>
      <ul className="divide-y divide-gray-50">
        {words.map((w) => (
          <LevelRow
            key={w.id}
            word={w}
            canPublish={data?.can_publish ?? false}
            onDone={onDone}
          />
        ))}
      </ul>
    </div>
  )
}
