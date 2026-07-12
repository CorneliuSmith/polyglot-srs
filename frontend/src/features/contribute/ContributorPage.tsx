import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getLanguages } from '../../api/profile'
import {
  approveGrammar,
  createGrammarPoint,
  getGrammarForLanguage,
  runAiCheck,
  saveGrammarExplanation,
  setLanguagePolicy,
} from '../../api/contribute'
import type { GrammarPointEdit } from '../../api/contribute'
import { usePrefsStore } from '../../stores/prefsStore'
import DrillsEditor from './DrillsEditor'
import FeedbackPanel from './FeedbackPanel'
import IssuesPanel from './IssuesPanel'
import RolesPanel from './RolesPanel'
import {
  flagPointIssue,
  getTutorUsage,
  setLanguageTutorModel,
  TUTOR_MODELS,
} from '../../api/contribute'

/** Admin-only per-language tutor model override (WP15a). */
function TutorModelControl({
  languageId,
  current,
  onChanged,
}: {
  languageId: string
  current: string | null
  onChanged: () => void
}) {
  const modelMutation = useMutation({
    mutationFn: (model: string | null) => setLanguageTutorModel(languageId, model),
    onSuccess: onChanged,
  })
  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-4">
      <h2 className="text-sm font-semibold text-gray-800">Tutor model</h2>
      <p className="text-xs text-gray-500 mb-2">
        Which Claude model powers this language's tutor. Default follows the
        server setting; pick a cheaper model for high-resource languages,
        the strongest for the low-resource ones.
      </p>
      <select
        value={current ?? ''}
        onChange={(e) => modelMutation.mutate(e.target.value || null)}
        disabled={modelMutation.isPending}
        aria-label="Tutor model"
        className="rounded-lg border border-gray-300 px-2 py-1.5 text-sm bg-white"
      >
        <option value="">Default (server setting)</option>
        {TUTOR_MODELS.map((m) => (
          <option key={m} value={m}>{m}</option>
        ))}
      </select>
      {modelMutation.isError && (
        <p className="text-xs text-red-500 mt-1">Couldn’t save — try again.</p>
      )}
    </div>
  )
}

/** Admin-only tutor cost monitor (WP9b): token rollups across ALL languages,
 * priced at list rates — the data behind per-language model choices. */
function TutorCostsPanel() {
  const { data } = useQuery({
    queryKey: ['tutor-usage'],
    queryFn: () => getTutorUsage(30),
    retry: false,
  })
  if (!data) return null
  const fmtTokens = (n: number) =>
    n >= 1_000_000 ? `${(n / 1_000_000).toFixed(1)}M` : n.toLocaleString()
  return (
    <div
      className="bg-white rounded-2xl border border-gray-100 p-4 text-sm"
      data-testid="tutor-costs"
    >
      <div className="flex items-baseline justify-between">
        <h2 className="text-sm font-semibold text-gray-800">
          Tutor costs · last {data.days} days
        </h2>
        <span className="text-xs text-gray-500">
          {data.total_messages} messages · ~${data.total_est_cost_usd.toFixed(2)}
        </span>
      </div>
      <p className="text-xs text-gray-500 mb-2">
        Estimates at Anthropic list pricing (cache reads discounted). All
        languages, all users — learners always pay flat tiers.
      </p>
      {data.rows.length === 0 ? (
        <p className="text-xs text-gray-400">No tutor usage recorded yet.</p>
      ) : (
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-gray-500">
              <th className="py-1 font-medium">Language</th>
              <th className="py-1 font-medium">Model</th>
              <th className="py-1 font-medium text-right">Msgs</th>
              <th className="py-1 font-medium text-right">Tokens in/out</th>
              <th className="py-1 font-medium text-right">Est. cost</th>
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row, i) => (
              <tr key={i} className="border-t border-gray-50 text-gray-700">
                <td className="py-1">
                  {row.language_name ?? '—'}
                  {row.kind === 'summary' && (
                    <span className="text-gray-400"> (summaries)</span>
                  )}
                </td>
                <td className="py-1 font-mono text-[11px]">{row.model ?? '—'}</td>
                <td className="py-1 text-right">{row.messages}</td>
                <td className="py-1 text-right">
                  {fmtTokens(row.input_tokens + row.cache_write_tokens + row.cache_read_tokens)}
                  {' / '}
                  {fmtTokens(row.output_tokens)}
                </td>
                <td className="py-1 text-right">${row.est_cost_usd.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

/** "Flag an issue" — a reviewer note for problems you can't (or shouldn't)
 * fix on the spot: regional-form doubts, tone-mark questions, and the like. */
function FlagIssueBox({ pointId }: { pointId: string }) {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [note, setNote] = useState('')
  const flagMutation = useMutation({
    mutationFn: () => flagPointIssue(pointId, note.trim()),
    onSuccess: () => {
      setNote('')
      setOpen(false)
      queryClient.invalidateQueries({ queryKey: ['review-notes'] })
    },
  })
  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="text-xs text-amber-700 hover:underline"
      >
        Flag an issue
      </button>
    )
  }
  return (
    <div className="w-full space-y-2">
      <textarea
        value={note}
        onChange={(e) => setNote(e.target.value)}
        rows={2}
        placeholder="What's wrong or doubtful about this point? (visible to reviewers and the admin)"
        aria-label="Issue description"
        className="w-full rounded-lg border border-amber-300 px-3 py-2 text-sm"
      />
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => flagMutation.mutate()}
          disabled={note.trim().length < 3 || flagMutation.isPending}
          className="bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white font-semibold rounded-lg px-3 py-1.5 text-xs"
        >
          {flagMutation.isPending ? 'Flagging…' : 'File issue'}
        </button>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="text-xs text-gray-500 hover:underline"
        >
          Cancel
        </button>
      </div>
      {flagMutation.isError && (
        <p className="text-xs text-red-500">Couldn’t file the issue — try again.</p>
      )}
    </div>
  )
}

function NewPointForm({
  languageId,
  onCreated,
}: {
  languageId: string
  onCreated: () => void
}) {
  const [title, setTitle] = useState('')
  const [level, setLevel] = useState('A1')

  const createMutation = useMutation({
    mutationFn: () => createGrammarPoint({ language_id: languageId, title, level }),
    onSuccess: () => {
      setTitle('')
      onCreated()
    },
  })

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-4 flex flex-wrap items-end gap-2">
      <div className="flex-1 min-w-[180px]">
        <label className="block text-xs font-medium text-gray-500">New grammar point</label>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g. Dative case"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
        />
      </div>
      <select
        value={level}
        onChange={(e) => setLevel(e.target.value)}
        className="rounded-lg border border-gray-300 px-2 py-2 text-sm"
      >
        {['A1', 'A2', 'B1', 'B2', 'C1', 'C2'].map((l) => (
          <option key={l} value={l}>{l}</option>
        ))}
      </select>
      <button
        type="button"
        onClick={() => createMutation.mutate()}
        disabled={!title.trim() || createMutation.isPending}
        className="bg-lang hover:bg-lang-dark disabled:opacity-50 text-lang-on font-semibold rounded-lg px-4 py-2 text-sm"
      >
        Create
      </button>
      {createMutation.isError && (
        <span className="text-xs text-red-500 w-full">
          Could not create (the title may already exist).
        </span>
      )}
    </div>
  )
}

function PointEditor({
  point,
  canReview,
  onSaved,
}: {
  point: GrammarPointEdit
  canReview: boolean
  onSaved: () => void
}) {
  const [explanation, setExplanation] = useState(point.explanation ?? '')
  const [cultureNote, setCultureNote] = useState(point.culture_note ?? '')
  // One "Title | https://url" per line — parsed on save.
  const [refsText, setRefsText] = useState(
    (point.references ?? []).map((r) => `${r.title} | ${r.url}`).join('\n'),
  )

  const parseRefs = () =>
    refsText
      .split('\n')
      .map((line) => {
        const i = line.indexOf('|')
        if (i === -1) return null
        const title = line.slice(0, i).trim()
        const url = line.slice(i + 1).trim()
        return title && url ? { title, url } : null
      })
      .filter((r): r is { title: string; url: string } => r !== null)

  const saveMutation = useMutation({
    mutationFn: () =>
      saveGrammarExplanation(point.id, explanation, cultureNote, parseRefs()),
    onSuccess: onSaved,
  })
  const approveMutation = useMutation({
    mutationFn: () => approveGrammar(point.id),
    onSuccess: onSaved,
  })
  const aiCheckMutation = useMutation({
    mutationFn: () => runAiCheck(point.id),
    onSuccess: onSaved,
  })

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-gray-900">
          {point.title}
          {point.level && <span className="text-xs text-gray-400 ml-2">{point.level}</span>}
        </h2>
        <span
          className={
            point.reviewed
              ? 'text-xs rounded-full px-2 py-0.5 bg-green-100 text-green-700'
              : 'text-xs rounded-full px-2 py-0.5 bg-amber-100 text-amber-700'
          }
        >
          {point.reviewed ? 'reviewed' : 'pending review'} · {point.explanation_source}
        </span>
      </div>

      {/* Checks: AI semantic review (advisory) + required human linguist review */}
      <div className="rounded-lg bg-gray-50 border border-gray-100 p-3 space-y-2 text-xs">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-semibold text-gray-600">AI semantic check:</span>
          {point.ai_check_status === 'pass' && (
            <span className="rounded-full px-2 py-0.5 bg-green-100 text-green-700">passed</span>
          )}
          {point.ai_check_status === 'concerns' && (
            <span className="rounded-full px-2 py-0.5 bg-amber-100 text-amber-800">concerns</span>
          )}
          {!point.ai_check_status && <span className="text-gray-400">not run</span>}
          <button
            type="button"
            onClick={() => aiCheckMutation.mutate()}
            disabled={aiCheckMutation.isPending}
            className="text-lang hover:underline disabled:opacity-50"
          >
            {aiCheckMutation.isPending ? 'Checking…' : 'Run AI check'}
          </button>
          {aiCheckMutation.isError && <span className="text-red-500">AI check unavailable</span>}
        </div>
        {point.ai_check_notes && (
          <p className="text-gray-600 whitespace-pre-wrap">{point.ai_check_notes}</p>
        )}
        <div>
          <span className="font-semibold text-gray-600">Human linguist review:</span>{' '}
          {point.reviewed ? (
            <span className="text-green-700">
              signed off{point.reviewed_at ? ` (${point.reviewed_at.slice(0, 10)})` : ''}
            </span>
          ) : (
            <span className="text-amber-700">
              required — not yet reviewed (learners won’t see this until approved)
            </span>
          )}
        </div>
      </div>

      <label className="block text-xs font-medium text-gray-500">Explanation</label>
      <textarea
        value={explanation}
        onChange={(e) => setExplanation(e.target.value)}
        rows={4}
        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-lang"
      />

      <label className="block text-xs font-medium text-gray-500">Culture note (optional)</label>
      <textarea
        value={cultureNote}
        onChange={(e) => setCultureNote(e.target.value)}
        rows={2}
        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-lang"
      />

      <label className="block text-xs font-medium text-gray-500">
        References (one per line: Title | https://url)
      </label>
      <textarea
        value={refsText}
        onChange={(e) => setRefsText(e.target.value)}
        rows={2}
        placeholder="Wiktionary: locative case | https://en.wiktionary.org/..."
        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-lang"
      />

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => saveMutation.mutate()}
          disabled={!explanation.trim() || saveMutation.isPending}
          className="bg-lang hover:bg-lang-dark disabled:opacity-50 text-lang-on font-semibold rounded-lg px-4 py-2 text-sm"
        >
          {saveMutation.isPending ? 'Saving…' : 'Save (pending review)'}
        </button>
        {canReview && !point.reviewed && point.explanation && (
          <button
            type="button"
            onClick={() => approveMutation.mutate()}
            disabled={approveMutation.isPending}
            className="bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white font-semibold rounded-lg px-4 py-2 text-sm"
          >
            Approve (linguist sign-off)
          </button>
        )}
        {saveMutation.isError && (
          <span className="text-xs text-red-500">Save failed.</span>
        )}
        <FlagIssueBox pointId={point.id} />
      </div>

      <DrillsEditor pointId={point.id} canEdit={canReview} />
    </div>
  )
}

function ReviewPolicyControl({
  languageId,
  policy,
  onChanged,
}: {
  languageId: string
  policy: string
  onChanged: () => void
}) {
  const mutation = useMutation({
    mutationFn: (next: 'strict' | 'ai_ok') => setLanguagePolicy(languageId, next),
    onSuccess: onChanged,
  })
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-4 text-sm">
      <div className="font-semibold text-gray-700 mb-1">Review policy (admin)</div>
      <p className="text-xs text-gray-500 mb-2">
        {policy === 'strict'
          ? 'Strict: learners only see grammar a human has approved.'
          : 'Open: learners also see AI-passed grammar, labelled “pending expert review”, until approved.'}
      </p>
      <div className="flex gap-2">
        {(['strict', 'ai_ok'] as const).map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => mutation.mutate(p)}
            disabled={mutation.isPending || policy === p}
            className={
              policy === p
                ? 'rounded-lg px-3 py-1.5 text-xs bg-lang text-white'
                : 'rounded-lg px-3 py-1.5 text-xs border border-gray-300 text-gray-600 hover:bg-gray-50'
            }
          >
            {p === 'strict' ? 'Strict' : 'Open (review later)'}
          </button>
        ))}
      </div>
    </div>
  )
}

export default function ContributorPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)

  const { data: languages = [] } = useQuery({ queryKey: ['languages'], queryFn: getLanguages })
  const language = languages.find((l) => l.id === activeLanguageId)

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['contribute-grammar', activeLanguageId],
    queryFn: () => getGrammarForLanguage(activeLanguageId!),
    enabled: !!activeLanguageId,
    retry: false,
  })

  const refresh = () =>
    queryClient.invalidateQueries({ queryKey: ['contribute-grammar', activeLanguageId] })

  // A 403 means the user has no contributor role for this language.
  const forbidden =
    isError && (error as { response?: { status?: number } })?.response?.status === 403

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-8 space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">
            Contribute · {language?.name ?? ''} grammar
          </h1>
          <button
            type="button"
            onClick={() => navigate('/')}
            className="text-sm text-lang hover:underline"
          >
            Dashboard
          </button>
        </div>

        {isLoading && <p className="text-gray-500">Loading…</p>}

        {forbidden && (
          <div className="bg-white rounded-2xl border border-gray-100 p-6 text-gray-600">
            You don’t have a contributor role for {language?.name ?? 'this language'}.
            Ask an admin for access.
          </div>
        )}

        {data && activeLanguageId && (
          <>
            {data.is_admin && (
              <>
                <RolesPanel languages={languages} />
                <ReviewPolicyControl
                  languageId={activeLanguageId}
                  policy={data.review_policy}
                  onChanged={refresh}
                />
                <TutorModelControl
                  languageId={activeLanguageId}
                  current={data.tutor_model ?? null}
                  onChanged={refresh}
                />
                <TutorCostsPanel />
              </>
            )}
            <IssuesPanel
              languageId={activeLanguageId}
              canResolve={data.can_review ?? data.is_admin}
            />
            <FeedbackPanel languageId={activeLanguageId} />
            <NewPointForm languageId={activeLanguageId} onCreated={refresh} />
          </>
        )}

        {data && data.points.length === 0 && (
          <p className="text-gray-500">No grammar points for this language yet.</p>
        )}

        {data &&
          data.points.map((point) => (
            <PointEditor
              key={point.id}
              point={point}
              canReview={data.can_review ?? data.is_admin}
              onSaved={refresh}
            />
          ))}
      </div>
    </div>
  )
}
