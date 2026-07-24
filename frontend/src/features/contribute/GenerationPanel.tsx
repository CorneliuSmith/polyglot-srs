import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getGenerationCoverage,
  getPendingExamples,
  reviewExample,
  reviewExamplesBulk,
  runGeneration,
  type GenerationDryRun,
  type GenerationResult,
} from '../../api/contribute'

/** Admin content-generation panel (WP42): fill example-sentence and drill gaps
 * with the server's Anthropic key. Coverage + model recommendation + a ranked
 * "do next", then an idempotent run with a dry-run cost preview so the bill is
 * visible before it's paid. Everything generated is tagged source='ai' and
 * left for human review. */
export default function GenerationPanel() {
  const qc = useQueryClient()
  const { data } = useQuery({
    queryKey: ['generation-coverage'],
    queryFn: getGenerationCoverage,
    retry: false,
  })

  const [languageId, setLanguageId] = useState<string>('')
  const [kind, setKind] = useState<'vocab' | 'grammar'>('vocab')
  const [target, setTarget] = useState(3)
  const [maxItems, setMaxItems] = useState(25)
  const [preview, setPreview] = useState<GenerationDryRun | null>(null)
  const [result, setResult] = useState<GenerationResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const rows = data?.coverage ?? []
  // Default the selector to the top "do next" language once data lands.
  const selectedId = languageId || data?.recommended_next[0]?.language_id || ''
  const selected = useMemo(
    () => rows.find((r) => r.language_id === selectedId),
    [rows, selectedId],
  )

  const mutation = useMutation({
    mutationFn: (dryRun: boolean) =>
      runGeneration({
        languageId: selectedId,
        languageCode: selected!.language_code,
        kind,
        targetPerItem: target,
        maxItems,
        dryRun,
      }),
    onSuccess: (res) => {
      setError(null)
      if (res.dry_run) {
        setPreview(res)
        setResult(null)
      } else {
        setResult(res)
        setPreview(null)
        qc.invalidateQueries({ queryKey: ['generation-coverage'] })
      }
    },
    onError: (err: unknown) => {
      const status = (err as { response?: { status?: number } })?.response?.status
      setError(
        status === 503
          ? 'The server has no Anthropic key configured — generation is unavailable here.'
          : 'Generation failed. Please try again.',
      )
    },
  })

  const { data: pending } = useQuery({
    queryKey: ['generation-pending', selectedId],
    queryFn: () => getPendingExamples(selectedId),
    enabled: !!selectedId,
    retry: false,
  })

  const reviewMutation = useMutation({
    mutationFn: ({ id, approve }: { id: string; approve: boolean }) =>
      reviewExample(id, approve),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['generation-pending', selectedId] })
      qc.invalidateQueries({ queryKey: ['generation-coverage'] })
    },
  })

  const bulkMutation = useMutation({
    mutationFn: (approve: boolean) => reviewExamplesBulk(selectedId, approve),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['generation-pending', selectedId] })
      qc.invalidateQueries({ queryKey: ['generation-coverage'] })
    },
  })

  if (!data) return null

  const gap = selected
    ? kind === 'vocab'
      ? selected.vocab_no_examples
      : selected.grammar_no_drills
    : 0
  const model = selected
    ? kind === 'vocab'
      ? selected.sentence_model
      : selected.grammar_model
    : ''

  const doPreview = () => {
    setResult(null)
    mutation.mutate(true)
  }
  const doGenerate = () => {
    const cost = preview ? ` (~$${preview.est_cost_usd.toFixed(2)})` : ''
    if (
      !window.confirm(
        `Generate ${kind} content for ${selected?.language_name} now${cost}? ` +
          'This uses the server Anthropic key and spends real credit.',
      )
    )
      return
    mutation.mutate(false)
  }

  return (
    <div
      className="bg-white rounded-2xl border border-gray-100 p-4 text-sm space-y-3"
      data-testid="generation-panel"
    >
      <div className="flex items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold text-gray-800">
          Content generation
        </h2>
        <span
          className={`text-xs ${data.available ? 'text-green-600' : 'text-amber-600'}`}
        >
          {data.available ? 'Key ready' : 'No server key'}
        </span>
      </div>
      <p className="text-xs text-gray-500">
        Fill example-sentence and drill gaps with the maker-checker generator.
        Runs are idempotent — only words/points still under target are touched,
        so re-running never double-spends. Everything is tagged “ai” for review.
      </p>

      {/* "Do next" — biggest gaps first, low-resource prioritized. */}
      {data.recommended_next.length > 0 && (
        <div className="rounded-xl bg-gray-50 p-3">
          <div className="text-xs font-medium text-gray-600 mb-1">
            Suggested next
          </div>
          <div className="flex flex-wrap gap-1.5">
            {data.recommended_next.map((n) => (
              <button
                key={n.language_id}
                type="button"
                onClick={() => setLanguageId(n.language_id)}
                className={`rounded-full px-2.5 py-1 text-xs transition-colors ${
                  n.language_id === selectedId
                    ? 'bg-lang text-lang-on'
                    : 'bg-white border border-gray-200 text-gray-600 hover:border-lang/50'
                }`}
              >
                {n.language_name}
                <span className="ml-1 opacity-70 tabular-nums">{n.unfilled}</span>
                {n.low_resource && <span className="ml-1">·low-res</span>}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Coverage table */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-gray-500">
              <th className="py-1 font-medium">Language</th>
              <th className="py-1 font-medium text-right">Vocab w/o ex.</th>
              <th className="py-1 font-medium text-right">Grammar w/o drills</th>
              <th className="py-1 font-medium text-right">AI so far</th>
              <th className="py-1 font-medium text-right">Pending</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr
                key={r.language_id}
                onClick={() => setLanguageId(r.language_id)}
                className={`border-t border-gray-50 cursor-pointer ${
                  r.language_id === selectedId
                    ? 'bg-lang-soft text-gray-900'
                    : 'text-gray-700 hover:bg-gray-50'
                }`}
              >
                <td className="py-1">
                  {r.language_name}
                  {r.low_resource && (
                    <span className="ml-1 text-[10px] text-lang">·low-res</span>
                  )}
                </td>
                <td className="py-1 text-right tabular-nums">
                  {r.vocab_no_examples}/{r.vocab_total}
                </td>
                <td className="py-1 text-right tabular-nums">
                  {r.grammar_no_drills}/{r.grammar_total}
                </td>
                <td className="py-1 text-right tabular-nums text-gray-400">
                  {r.ai_examples + r.ai_drills}
                </td>
                <td className="py-1 text-right tabular-nums">
                  {r.pending_examples > 0 ? (
                    <span className="text-amber-600">{r.pending_examples}</span>
                  ) : (
                    <span className="text-gray-300">0</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Run controls */}
      {selected && (
        <div className="rounded-xl border border-gray-100 p-3 space-y-2">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
            <span className="font-medium text-gray-700">
              {selected.language_name}
            </span>
            <div className="flex rounded-lg border border-gray-200 overflow-hidden">
              {(['vocab', 'grammar'] as const).map((k) => (
                <button
                  key={k}
                  type="button"
                  onClick={() => {
                    setKind(k)
                    setPreview(null)
                  }}
                  aria-pressed={kind === k}
                  className={`px-3 py-1 capitalize transition-colors ${
                    kind === k
                      ? 'bg-lang text-lang-on'
                      : 'bg-white text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  {k}
                </button>
              ))}
            </div>
            <label className="flex items-center gap-1 text-gray-500">
              target/each
              <input
                type="number"
                min={1}
                max={data.limits.max_per_item}
                value={target}
                onChange={(e) => setTarget(Math.max(1, Number(e.target.value) || 1))}
                className="w-14 rounded border border-gray-200 px-1.5 py-1 tabular-nums"
              />
            </label>
            <label className="flex items-center gap-1 text-gray-500">
              max items
              <input
                type="number"
                min={1}
                max={data.limits.max_items}
                value={maxItems}
                onChange={(e) => setMaxItems(Math.max(1, Number(e.target.value) || 1))}
                className="w-16 rounded border border-gray-200 px-1.5 py-1 tabular-nums"
              />
            </label>
          </div>

          <div className="text-xs text-gray-500">
            {gap} {kind === 'vocab' ? 'words without examples' : 'points without drills'}{' '}
            · model <span className="font-mono">{model}</span>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={doPreview}
              disabled={mutation.isPending || gap === 0}
              className="rounded-lg border border-gray-200 px-3 py-1.5 text-gray-700 hover:bg-gray-50 disabled:opacity-40"
            >
              {mutation.isPending ? 'Working…' : 'Preview cost'}
            </button>
            <button
              type="button"
              onClick={doGenerate}
              disabled={mutation.isPending || gap === 0 || !data.available}
              className="rounded-lg bg-lang text-lang-on px-3 py-1.5 font-semibold hover:bg-lang-dark disabled:opacity-40"
            >
              Generate now
            </button>
          </div>

          {preview && (
            <p className="text-xs text-gray-600">
              Would process <b>{preview.items_to_process}</b>{' '}
              {kind === 'vocab' ? 'words' : 'points'}, attempt{' '}
              <b>{preview.sentences_to_attempt}</b> sentences — est.{' '}
              <b>~${preview.est_cost_usd.toFixed(2)}</b>.
            </p>
          )}
          {result && (
            <p className="text-xs text-green-700" role="status">
              Done: processed {result.items_processed}, saved{' '}
              <b>{result.sentences_persisted}</b> new{' '}
              {kind === 'vocab' ? 'examples' : 'drills'}
              {result.duplicates_skipped > 0 &&
                ` (${result.duplicates_skipped} duplicate${
                  result.duplicates_skipped === 1 ? '' : 's'
                } skipped)`}{' '}
              · est. ~${result.est_cost_usd.toFixed(2)}. They’re tagged “ai” and
              await review.
            </p>
          )}
          {error && (
            <p className="text-xs text-amber-600" role="alert">
              {error}
            </p>
          )}
        </div>
      )}

      {/* Review gate: generated examples are hidden from learners until an
          admin approves them here. Reject deletes. */}
      {selected && pending && pending.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50/50 p-3 space-y-2">
          <div className="flex items-start justify-between gap-2">
            <div className="text-xs font-medium text-amber-800">
              {pending.length} generated example{pending.length === 1 ? '' : 's'}{' '}
              awaiting review — hidden from learners until you approve.
            </div>
            <div className="flex shrink-0 gap-1">
              <button
                type="button"
                onClick={() => {
                  if (
                    window.confirm(
                      `Approve all pending ${selected.language_name} examples? ` +
                        'Flagged ones are skipped. They go live to learners.',
                    )
                  )
                    bulkMutation.mutate(true)
                }}
                disabled={bulkMutation.isPending}
                className="rounded-md bg-green-600 text-white px-2 py-1 text-[11px] font-medium hover:bg-green-700 disabled:opacity-40"
              >
                Approve all
              </button>
              <button
                type="button"
                onClick={() => {
                  if (
                    window.confirm(
                      `Reject (delete) all ${pending.length} pending ` +
                        `${selected.language_name} examples? This cannot be undone.`,
                    )
                  )
                    bulkMutation.mutate(false)
                }}
                disabled={bulkMutation.isPending}
                className="rounded-md border border-gray-200 text-gray-600 px-2 py-1 text-[11px] hover:bg-gray-50 disabled:opacity-40"
              >
                Reject all
              </button>
            </div>
          </div>
          <ul className="space-y-1.5">
            {pending.map((p) => (
              <li
                key={p.id}
                className="flex items-start justify-between gap-2 rounded-lg bg-white border border-gray-100 px-2.5 py-1.5"
              >
                <div className="min-w-0">
                  <div className="text-xs text-gray-800">
                    <span className="font-medium">{p.word}</span> · {p.sentence}
                  </div>
                  {p.translation && (
                    <div className="text-[11px] text-gray-400">{p.translation}</div>
                  )}
                </div>
                <div className="flex shrink-0 gap-1">
                  <button
                    type="button"
                    onClick={() =>
                      reviewMutation.mutate({ id: p.id, approve: true })
                    }
                    disabled={reviewMutation.isPending}
                    className="rounded-md bg-green-600 text-white px-2 py-1 text-[11px] hover:bg-green-700 disabled:opacity-40"
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      reviewMutation.mutate({ id: p.id, approve: false })
                    }
                    disabled={reviewMutation.isPending}
                    className="rounded-md border border-gray-200 text-gray-600 px-2 py-1 text-[11px] hover:bg-gray-50 disabled:opacity-40"
                  >
                    Reject
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
