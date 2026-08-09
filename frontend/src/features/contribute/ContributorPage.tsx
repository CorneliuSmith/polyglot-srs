import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getLanguages } from '../../api/profile'
import {
  PUBLISH_POLICIES,
  POLICY_LABELS,
  POLICY_HELP,
  normalizePolicy,
  type PublishPolicy,
} from '../../lib/publishPolicy'
import {
  approveGrammar,
  createGrammarPoint,
  getGrammarForLanguage,
  runAiCheck,
  runAiCheckBatch,
  saveGrammarExplanation,
  setLanguagePolicy,
} from '../../api/contribute'
import type { GrammarPointEdit } from '../../api/contribute'
import { usePrefsStore } from '../../stores/prefsStore'
import DrillsEditor from './DrillsEditor'
import VocabReviewPanel from './VocabReviewPanel'
import FeedbackPanel from './FeedbackPanel'
import IssuesPanel from './IssuesPanel'
import ChangeRequestsPanel from './ChangeRequestsPanel'
import SuggestionsPanel from './SuggestionsPanel'
import SuggestionMetricsPanel from './SuggestionMetricsPanel'
import RolesPanel from './RolesPanel'
import AccountsPanel from './AccountsPanel'
import TrialRequestsPanel from './TrialRequestsPanel'
import AnalyticsPanel from './AnalyticsPanel'
import EngagementPanel from './EngagementPanel'
import LanguageVisibilityPanel from './LanguageVisibilityPanel'
import GeneratedDrillsPanel from './GeneratedDrillsPanel'
import ReviewInbox from './ReviewInbox'
import GymDrillsPanel from './GymDrillsPanel'
import AiLevelsPanel from './AiLevelsPanel'
import GenerationPanel from './GenerationPanel'
import TranslationReviewsPanel from './TranslationReviewsPanel'
import { useAuthStore } from '../../stores/authStore'
import {
  flagPointIssue,
  getTutorUsage,
  setLanguageTutorModel,
  TUTOR_MODELS,
} from '../../api/contribute'
import { useViewAsKey } from '../../stores/viewAsStore'

/** Admin-only per-language tutor model override (WP15a). */
export function TutorModelControl({
  languageId,
  languageName,
  current,
  defaultModel,
  onChanged,
}: {
  languageId: string
  languageName?: string
  current: string | null
  defaultModel?: string
  onChanged: () => void
}) {
  const modelMutation = useMutation({
    mutationFn: ({ model, all }: { model: string | null; all?: boolean }) =>
      setLanguageTutorModel(languageId, model, all),
    onSuccess: onChanged,
  })
  const appliedAll = modelMutation.isSuccess && modelMutation.variables?.all
  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-4">
      {/* The scope is in the title — this control looked global, so every
          language switch read as the setting "resetting" (owner report). */}
      <h2 className="text-sm font-semibold text-gray-800">
        Tutor model{languageName ? ` — ${languageName}` : ''}
      </h2>
      <p className="text-xs text-gray-500 mb-2">
        Which Claude model powers the {languageName ?? 'active language'}{' '}
        tutor. Each language has its own setting; newly added languages start
        on the default. Pick a cheaper model for high-resource languages, the
        strongest for the low-resource ones.
      </p>
      <select
        value={current ?? ''}
        onChange={(e) => modelMutation.mutate({ model: e.target.value || null })}
        disabled={modelMutation.isPending}
        aria-label="Tutor model"
        className="rounded-lg border border-gray-300 px-2 py-1.5 text-sm bg-white"
      >
        <option value="">
          Default{defaultModel ? ` (${defaultModel})` : ' (server setting)'}
        </option>
        {TUTOR_MODELS.map((m) => (
          <option key={m} value={m}>{m}</option>
        ))}
      </select>
      <p className="mt-2 text-xs text-gray-400">
        <button
          type="button"
          onClick={() => {
            if (
              window.confirm(
                `Apply ${current ?? 'the default'} to ALL languages? This overwrites every language's tutor-model setting.`,
              )
            )
              modelMutation.mutate({ model: current, all: true })
          }}
          disabled={modelMutation.isPending}
          className="text-lang hover:underline disabled:opacity-50"
        >
          {appliedAll ? 'Applied to all languages ✓' : 'Apply this choice to all languages'}
        </button>
      </p>
      {modelMutation.isError && (
        <p className="text-xs text-red-500 mt-1">Couldn’t save — try again.</p>
      )}
    </div>
  )
}

/** Admin-only tutor cost monitor (WP9b): token rollups across ALL languages,
 * priced at list rates — the data behind per-language model choices. Rows are
 * per (language, model, KIND) — chat vs Gym generation vs summaries — which
 * is why a language/model pair can appear more than once. */
const USAGE_KIND_LABEL: Record<string, string> = {
  chat: 'Chat',
  gym_gen: 'Gym drills',
  gym_chart: 'Gym charts',
  summary: 'Summaries',
}

export function TutorCostsPanel() {
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
            <tr className="text-start text-gray-500">
              <th className="py-1 font-medium">Language</th>
              <th className="py-1 font-medium">Kind</th>
              <th className="py-1 font-medium">Model</th>
              <th className="py-1 font-medium text-end">Msgs</th>
              <th className="py-1 font-medium text-end">Tokens in/out</th>
              <th className="py-1 font-medium text-end">Est. cost</th>
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row, i) => (
              <tr key={i} className="border-t border-gray-50 text-gray-700">
                <td className="py-1">{row.language_name ?? '—'}</td>
                <td className="py-1 text-gray-500">
                  {USAGE_KIND_LABEL[row.kind] ?? row.kind}
                </td>
                <td className="py-1 font-mono text-[11px]">{row.model ?? '—'}</td>
                <td className="py-1 text-end">{row.messages}</td>
                <td className="py-1 text-end">
                  {fmtTokens(row.input_tokens + row.cache_write_tokens + row.cache_read_tokens)}
                  {' / '}
                  {fmtTokens(row.output_tokens)}
                </td>
                <td className="py-1 text-end">${row.est_cost_usd.toFixed(2)}</td>
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

export function NewPointForm({
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
          {point.level && <span className="text-xs text-gray-400 ms-2">{point.level}</span>}
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

export function ReviewPolicyControl({
  languageId,
  languageName,
  policy,
  uncheckedPoints = 0,
  onChanged,
}: {
  languageId: string
  languageName?: string
  policy: string
  /** Points invisible under 'ai_ok' because no check verdict exists yet. */
  uncheckedPoints?: number
  onChanged: () => void
}) {
  const mutation = useMutation({
    mutationFn: (next: PublishPolicy) => setLanguagePolicy(languageId, next),
    onSuccess: onChanged,
  })

  // The bulk check: loop batch requests until nothing is left, narrating
  // progress. Owner-reported gap: they switched the policy to Open, nothing
  // appeared, and the panel neither said why nor offered the fix — the
  // check verdict is the other half of the visibility gate, and the only
  // way to produce one was a per-point button, forty times.
  const [checkProgress, setCheckProgress] = useState<string | null>(null)
  const [checkError, setCheckError] = useState(false)
  const bulkCheck = useMutation({
    mutationFn: async () => {
      setCheckError(false)
      let done = 0
      let concerns = 0
      for (;;) {
        const result = await runAiCheckBatch(languageId)
        done += result.checked
        concerns += result.concerns
        if (result.remaining <= 0 || result.checked === 0) break
        setCheckProgress(`Checked ${done} — ${result.remaining} to go…`)
      }
      return { done, concerns }
    },
    onSuccess: ({ concerns }) => {
      setCheckProgress(
        concerns > 0
          ? `Done — ${concerns} point${concerns === 1 ? '' : 's'} flagged with concerns for review; the rest are now visible to learners.`
          : 'Done — all points passed and are now visible to learners.',
      )
      onChanged()
    },
    onError: () => {
      // Batches already checked stayed checked — a retry resumes.
      setCheckError(true)
      setCheckProgress(null)
    },
  })

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-4 text-sm">
      <div className="font-semibold text-gray-700 mb-1">
        AI content policy{languageName ? ` — ${languageName}` : ''} (admin)
      </div>
      <p className="text-xs text-gray-500 mb-2">
        Where the line sits between what your reviewers can see and what your
        learners can. Staff always see everything for this language — this
        setting only decides what gets published past them.
      </p>
      <div className="space-y-1.5">
        {PUBLISH_POLICIES.map((p) => {
          const active = normalizePolicy(policy) === p
          return (
            <button
              key={p}
              type="button"
              onClick={() => mutation.mutate(p)}
              disabled={mutation.isPending || active}
              className={
                'w-full rounded-lg border px-3 py-2 text-start ' +
                (active
                  ? 'border-lang bg-lang-soft'
                  : 'border-gray-200 hover:bg-gray-50')
              }
            >
              <span
                className={
                  'block text-xs font-semibold ' +
                  (active ? 'text-lang-dark' : 'text-gray-700')
                }
              >
                {POLICY_LABELS[p]}
                {active && ' — current'}
              </span>
              <span className="block text-[11px] text-gray-500">
                {POLICY_HELP[p]}
              </span>
            </button>
          )
        })}
      </div>

      {policy === 'ai_ok' && uncheckedPoints > 0 && (
        <div
          className="mt-3 rounded-xl border border-amber-200 bg-amber-50 p-3 space-y-2"
          data-testid="unchecked-warning"
        >
          <p className="text-xs text-amber-900">
            <span className="font-semibold">
              {uncheckedPoints} grammar point{uncheckedPoints === 1 ? '' : 's'}
              {' '}are still hidden.
            </span>{' '}
            Open shows AI content that has <em>passed the automated check</em>,
            and these haven’t been checked yet — the policy is only half the
            gate. Run the check and they appear as each one passes.
          </p>
          <button
            type="button"
            onClick={() => {
              setCheckProgress('Starting…')
              bulkCheck.mutate()
            }}
            disabled={bulkCheck.isPending}
            className="rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-700 disabled:opacity-50"
          >
            {bulkCheck.isPending ? 'Checking…' : `Check all ${uncheckedPoints} now`}
          </button>
        </div>
      )}
      {checkProgress && (
        <p className="mt-2 text-xs text-gray-600" data-testid="check-progress">
          {checkProgress}
        </p>
      )}
      {checkError && (
        <p className="mt-2 text-xs text-red-600">
          The check stopped partway — everything already checked is saved, so
          running it again picks up where it left off.
        </p>
      )}
    </div>
  )
}

/** Deep link support (/contribute?point=<id>): float the linked point to
 * the top so a reviewer lands directly on the card they came to fix. */
function orderedPoints<T extends { id: string }>(
  points: T[],
  focusId: string | null,
): T[] {
  if (!focusId) return points
  const hit = points.find((p) => p.id === focusId)
  if (!hit) return points
  return [hit, ...points.filter((p) => p.id !== focusId)]
}

type WorkspaceTab = 'contribute' | 'review' | 'admin'

export default function ContributorPage() {
  const [searchParams] = useSearchParams()
  const focusPointId = searchParams.get('point')
  const selfId = useAuthStore((s) => s.session?.user?.id ?? null)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)
  const [tab, setTab] = useState<WorkspaceTab>('contribute')
  // Grammar points have a full authoring surface; vocab is browse + votable
  // suggestions (WP32). The toggle scopes the Contribute/Review content list.
  const [contentKind, setContentKind] = useState<'grammar' | 'vocab'>('grammar')

  const { data: languages = [] } = useQuery({ queryKey: ['languages'], queryFn: getLanguages })
  const language = languages.find((l) => l.id === activeLanguageId)
  const languageCode = language?.code ?? 'en'

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['contribute-grammar', activeLanguageId, useViewAsKey()],
    queryFn: () => getGrammarForLanguage(activeLanguageId!),
    enabled: !!activeLanguageId,
    retry: false,
  })

  const refresh = () =>
    queryClient.invalidateQueries({ queryKey: ['contribute-grammar', activeLanguageId] })

  // A pure trial reviewer has no Contribute tab; land them on Review instead
  // of a tab they can't see.
  const canContribute = (data?.can_contribute ?? false) || (data?.is_admin ?? false)
  useEffect(() => {
    if (data && tab === 'contribute' && !canContribute) setTab('review')
  }, [data, tab, canContribute])

  // A 403 means the user has no contributor role for this language.
  const forbidden =
    isError && (error as { response?: { status?: number } })?.response?.status === 403

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-8 space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">
            Contribute · {language?.name ?? ''}
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
            {/* Role tiers (beta request): Contribute for drafting, Review
                for approvals + reader feedback, Admin for accounts,
                controls, and costs. Tabs render only for roles the account
                holds; learners without a role never reach this content. */}
            <div
              className="flex rounded-xl border border-gray-200 bg-white overflow-hidden text-sm"
              role="tablist"
              aria-label="Workspace"
            >
              {(
                [
                  // Drafting surface — contributors and admins only. A pure
                  // trial reviewer has no Contribute tab (nothing to draft).
                  ['contribute', 'Contribute', (data.can_contribute ?? false) || data.is_admin],
                  // Contributors have all reviewer permissions on the
                  // change-request board, so they get the Review tab too.
                  ['review', 'Review',
                    (data.can_review ?? data.is_admin) ||
                    (data.can_contribute ?? false) ||
                    (data.can_trial_review ?? false)],
                  ['admin', 'Admin', data.is_admin],
                ] as [WorkspaceTab, string, boolean][]
              )
                .filter(([, , show]) => show)
                .map(([key, label]) => (
                  <button
                    key={key}
                    type="button"
                    role="tab"
                    aria-selected={tab === key}
                    onClick={() => setTab(key)}
                    className={`flex-1 px-4 py-2 font-semibold transition-colors ${
                      tab === key
                        ? 'bg-lang text-lang-on'
                        : 'text-gray-500 hover:bg-gray-50'
                    }`}
                  >
                    {label}
                  </button>
                ))}
            </div>

            {/* Content switch: grammar points vs vocabulary. Grammar keeps its
                full authoring/approval surface; vocab is browse + votable
                suggestions. Hidden on the Admin tab (controls, not content). */}
            {tab !== 'admin' && (
              <div
                className="flex rounded-lg border border-gray-200 bg-white overflow-hidden text-sm w-fit"
                role="tablist"
                aria-label="Content type"
              >
                {(['grammar', 'vocab'] as const).map((k) => (
                  <button
                    key={k}
                    type="button"
                    role="tab"
                    aria-selected={contentKind === k}
                    onClick={() => setContentKind(k)}
                    className={`px-4 py-1.5 font-medium capitalize transition-colors ${
                      contentKind === k
                        ? 'bg-lang text-lang-on'
                        : 'text-gray-500 hover:bg-gray-50'
                    }`}
                  >
                    {k}
                  </button>
                ))}
              </div>
            )}

            {tab === 'admin' && data.is_admin && (
              <>
                <AnalyticsPanel />
                <EngagementPanel />
                <LanguageVisibilityPanel />
                <SuggestionMetricsPanel />
                <GenerationPanel />
                <TranslationReviewsPanel />
                <TrialRequestsPanel />
                <AccountsPanel languages={languages} selfId={selfId} />
                <RolesPanel languages={languages} />
                <ReviewPolicyControl
                  languageId={activeLanguageId}
                  languageName={language?.name}
                  policy={data.review_policy}
                  uncheckedPoints={data.unchecked_points ?? 0}
                  onChanged={refresh}
                />
                <TutorModelControl
                  languageId={activeLanguageId}
                  languageName={language?.name}
                  current={data.tutor_model ?? null}
                  defaultModel={data.default_tutor_model}
                  onChanged={refresh}
                />
                <TutorCostsPanel />
              </>
            )}
            {tab === 'review' && (
              <>
                {/* One roll-up of everything awaiting review action, above the
                    individual queue panels. */}
                <ReviewInbox languageId={activeLanguageId} />
                {/* Generated grammar drills awaiting review. Full reviewers
                    approve/reject; trial reviewers recommend. Hidden when none
                    pending. */}
                {(data.can_trial_review ?? false) && (
                  <GeneratedDrillsPanel languageId={activeLanguageId} />
                )}
                {/* Words the model gave a provisional CEFR level — confirm to
                    finalise the level and the deck placement. */}
                {(data.can_trial_review ?? false) && (
                  <AiLevelsPanel languageId={activeLanguageId} />
                )}
                {/* Gym corpus, browsable by form category — view/edit the drills
                    the Gym serves, not just the ones pending review above. */}
                <GymDrillsPanel
                  languageId={activeLanguageId}
                  canEdit={data.can_review ?? data.is_admin}
                />
                {/* Change requests: everyone with a role sees and votes;
                    only admins accept/reject (server-enforced). */}
                <ChangeRequestsPanel languageId={activeLanguageId} />
                {(data.can_review ?? data.is_admin) && (
                  <SuggestionsPanel languageId={activeLanguageId} />
                )}
                {(data.can_review ?? data.is_admin) && (
                  <>
                    <IssuesPanel
                      languageId={activeLanguageId}
                      canResolve={data.can_review ?? data.is_admin}
                    />
                    <FeedbackPanel languageId={activeLanguageId} />
                  </>
                )}
              </>
            )}
            {tab === 'contribute' && contentKind === 'grammar' && (
              <NewPointForm languageId={activeLanguageId} onCreated={refresh} />
            )}

            {/* Vocab review surface (WP32): browse + votable suggestions,
                shown for both Contribute and Review when Vocab is selected. */}
            {contentKind === 'vocab' && (
              <VocabReviewPanel
                languageId={activeLanguageId}
                languageCode={languageCode}
                canEdit={data.can_trial_review ?? false}
              />
            )}
          </>
        )}

        {data && tab !== 'admin' && contentKind === 'grammar' &&
          data.points.length === 0 && (
            <p className="text-gray-500">No grammar points for this language yet.</p>
          )}

        {data && tab !== 'admin' && contentKind === 'grammar' &&
          orderedPoints(data.points, focusPointId).map((point) => (
            <div
              key={point.id}
              id={`edit-point-${point.id}`}
              className={
                point.id === focusPointId
                  ? 'ring-2 ring-lang rounded-2xl'
                  : undefined
              }
            >
              <PointEditor
                point={point}
                canReview={tab === 'review' && (data.can_review ?? data.is_admin)}
                onSaved={refresh}
              />
            </div>
          ))}
      </div>
    </div>
  )
}
