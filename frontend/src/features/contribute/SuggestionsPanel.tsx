import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getSuggestions, approveSuggestion, rejectSuggestion } from '../../api/contribute'
import type { Suggestion, SuggestionFields, SuggestionSource } from '../../api/contribute'

/** Reviewer queue: proposed card edits, each shown as a current → proposed
 * diff. Approve applies it to the live card; decline discards it. Proposals
 * come from two places — a contributor, or a document re-seed (the extractor
 * proposing values for a word a human already curated, rather than overwriting
 * it). Doc-sourced ones are badged and filterable, since they cost model spend
 * and admin tracks how often they land. */
export default function SuggestionsPanel({ languageId }: { languageId: string }) {
  const queryClient = useQueryClient()
  const [source, setSource] = useState<SuggestionSource | 'all'>('all')

  const { data: items = [] } = useQuery({
    queryKey: ['suggestions', languageId],
    queryFn: () => getSuggestions(languageId),
    retry: false,
  })

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['suggestions', languageId] })

  const approve = useMutation({
    mutationFn: (id: string) => approveSuggestion(id),
    onSuccess: invalidate,
  })
  const reject = useMutation({
    mutationFn: (id: string) => rejectSuggestion(id),
    onSuccess: invalidate,
  })

  if (items.length === 0) return null

  const docCount = items.filter((s: Suggestion) => s.source === 'extraction').length
  const shown =
    source === 'all' ? items : items.filter((s: Suggestion) => s.source === source)

  const FIELDS: [keyof SuggestionFields, string][] = [
    ['definition', 'Definition'],
    ['part_of_speech', 'Part of speech'],
    ['usage_note', 'Usage note'],
    ['function_note', 'Function'],
    ['explanation', 'Explanation'],
    ['culture_note', 'Culture note'],
  ]

  const filterChip = (value: SuggestionSource | 'all', label: string, count: number) => (
    <button
      type="button"
      onClick={() => setSource(value)}
      aria-pressed={source === value}
      className={
        'rounded-full px-2.5 py-0.5 text-xs transition-colors ' +
        (source === value
          ? 'bg-lang text-white'
          : 'bg-gray-100 text-gray-600 hover:bg-gray-200')
      }
    >
      {label} ({count})
    </button>
  )

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-lang/30 p-4 space-y-3" data-testid="suggestions">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <h2 className="text-sm font-semibold text-lang-dark">
          Suggested edits ({items.length})
        </h2>
        {docCount > 0 && (
          <div className="flex gap-1.5">
            {filterChip('all', 'All', items.length)}
            {filterChip('extraction', 'AI · doc', docCount)}
            {filterChip('contributor', 'Contributor', items.length - docCount)}
          </div>
        )}
      </div>
      {shown.map((s: Suggestion) => (
        <div key={s.id} className="border-t border-gray-100 pt-2 text-sm">
          <div className="flex items-baseline justify-between gap-2">
            <span className="font-medium text-gray-800">{s.card_title ?? s.entity_id}</span>
            <span className="flex items-center gap-1.5">
              {s.source === 'extraction' && (
                <span
                  className="rounded-full bg-amber-100 text-amber-700 px-1.5 py-0.5 text-[10px] font-semibold"
                  title={s.origin ?? 'Proposed by a document re-seed'}
                >
                  AI · doc
                </span>
              )}
              <span className="text-xs text-gray-400">{s.entity_type}</span>
            </span>
          </div>
          <div className="mt-1 space-y-1">
            {FIELDS.filter(([k]) => s.proposed[k] !== undefined).map(([k, label]) => (
              <div key={k} className="text-xs">
                <span className="text-gray-400">{label}: </span>
                <span className="text-red-500 line-through">{s.current[k] || '∅'}</span>
                <span className="text-gray-400"> → </span>
                <span className="text-green-700 font-medium">{s.proposed[k]}</span>
              </div>
            ))}
          </div>
          {s.note && <p className="mt-1 text-xs italic text-gray-500">“{s.note}”</p>}
          <div className="mt-2 flex gap-3">
            <button
              type="button"
              onClick={() => approve.mutate(s.id)}
              disabled={approve.isPending}
              className="text-xs font-semibold text-green-700 hover:underline"
            >
              Approve
            </button>
            <button
              type="button"
              onClick={() => reject.mutate(s.id)}
              disabled={reject.isPending}
              className="text-xs text-gray-500 hover:underline"
            >
              Decline
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
