import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getVocabForLanguage } from '../../api/contribute'
import type { VocabItemEdit } from '../../api/contribute'
import LanguageWrapper from '../../components/LanguageWrapper'
import SuggestChange from './SuggestChange'

/** One vocab entry: word, gloss, and its supporting-content counts, with an
 * inline votable suggestion. Thin entries (no definition / no examples) are
 * called out so reviewers can target them. */
function VocabRow({
  item,
  languageId,
  languageCode,
}: {
  item: VocabItemEdit
  languageId: string
  languageCode: string
}) {
  const [open, setOpen] = useState(false)
  const thin = !item.definition || item.example_count === 0
  return (
    <div className="border-t border-gray-100 first:border-t-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="w-full px-4 py-3 text-left flex items-center justify-between gap-3 hover:bg-gray-50"
      >
        <span className="min-w-0">
          <LanguageWrapper languageCode={languageCode}>
            <span className="text-sm font-medium text-gray-800">{item.word}</span>
          </LanguageWrapper>
          <span className="block text-xs text-gray-500 truncate">
            {item.definition ?? <span className="text-amber-600">no definition</span>}
          </span>
        </span>
        <span className="flex items-center gap-2 shrink-0">
          {item.level && (
            <span className="text-[10px] uppercase tracking-wide bg-gray-100 text-gray-500 rounded px-1.5 py-0.5">
              {item.level}
            </span>
          )}
          {thin && (
            <span className="text-[10px] uppercase tracking-wide bg-amber-50 text-amber-600 rounded px-1.5 py-0.5">
              thin
            </span>
          )}
          <span className="text-gray-300">{open ? '▴' : '▾'}</span>
        </span>
      </button>
      {open && (
        <div className="px-4 pb-4 space-y-2 text-xs text-gray-600">
          <p>
            {item.part_of_speech && <span className="italic">{item.part_of_speech}</span>}
            {item.reading && <span> · {item.reading}</span>}
            {item.frequency_rank != null && (
              <span className="text-gray-400"> · rank #{item.frequency_rank}</span>
            )}
          </p>
          <p className={item.example_count === 0 ? 'text-amber-600' : undefined}>
            {item.example_count} example {item.example_count === 1 ? 'sentence' : 'sentences'}
          </p>
          <SuggestChange
            languageId={languageId}
            targetType="vocabulary"
            targetId={item.id}
            targetLabel={item.word}
            defaultField="translation"
          />
        </div>
      )}
    </div>
  )
}

/**
 * Vocab review surface for the Contributor workspace — the counterpart to the
 * grammar-point list. Read-only browse with an inline, votable "suggest a
 * change" on every word; accepted suggestions are applied from the change-
 * request board. Searchable and level-filterable so a reviewer can work a
 * level at a time.
 */
export default function VocabReviewPanel({
  languageId,
  languageCode,
}: {
  languageId: string
  languageCode: string
}) {
  const [search, setSearch] = useState('')
  const [level, setLevel] = useState<string>('all')

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['contribute-vocab', languageId],
    queryFn: () => getVocabForLanguage(languageId),
    enabled: !!languageId,
    retry: false,
  })

  const forbidden =
    isError && (error as { response?: { status?: number } })?.response?.status === 403

  const levels = useMemo(() => {
    const set = new Set<string>()
    for (const it of data?.items ?? []) if (it.level) set.add(it.level)
    return ['all', ...Array.from(set).sort()]
  }, [data])

  const filtered = useMemo(() => {
    const items = data?.items ?? []
    const q = search.trim().toLowerCase()
    return items.filter(
      (it) =>
        (level === 'all' || it.level === level) &&
        (!q ||
          it.word.toLowerCase().includes(q) ||
          (it.definition ?? '').toLowerCase().includes(q)),
    )
  }, [data, search, level])

  if (isLoading) return <p className="text-gray-500 text-sm">Loading vocab…</p>
  if (forbidden) {
    return (
      <div className="bg-white rounded-2xl border border-gray-100 p-6 text-gray-600">
        You don’t have a contributor role for this language.
      </div>
    )
  }

  return (
    <div className="space-y-3" data-testid="vocab-review">
      <div className="flex items-center gap-2">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search vocab"
          aria-label="Search vocab"
          className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-lang bg-white"
        />
        <select
          value={level}
          onChange={(e) => setLevel(e.target.value)}
          aria-label="Filter by level"
          className="rounded-lg border border-gray-300 px-2 py-2 text-sm bg-white"
        >
          {levels.map((l) => (
            <option key={l} value={l}>
              {l === 'all' ? 'All levels' : l}
            </option>
          ))}
        </select>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        {filtered.map((item) => (
          <VocabRow
            key={item.id}
            item={item}
            languageId={languageId}
            languageCode={languageCode}
          />
        ))}
        {filtered.length === 0 && (
          <p className="px-4 py-3 text-sm text-gray-500">
            {(data?.items.length ?? 0) === 0
              ? 'No vocabulary for this language yet.'
              : 'No words match.'}
          </p>
        )}
      </div>
    </div>
  )
}
