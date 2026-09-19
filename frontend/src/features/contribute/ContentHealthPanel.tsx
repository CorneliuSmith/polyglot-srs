import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  disposeVerdict,
  getContentHealth,
  getContentHealthCourse,
  type ContentHealthCourse,
  type ContentHealthDetail,
  type ContentHealthJudge,
  type ContentHealthStatus,
  type TrendPoint,
  type VerdictDisposition,
} from '../../api/contribute'
import { ago } from '../../lib/ago'

/**
 * Content health: one row per course, worst first (owner: "something to
 * showcase errors and problems like this" — plan §6).
 *
 * Every defect that reached a learner this month passed every automated
 * check, because each check asked whether a row was well-formed and none
 * asked whether it was right. The instruments that did find them — the
 * register judge, the sense and gloss audits — ran by hand and were thrown
 * away. This panel is where their numbers now land with a date on them:
 * the nightly loop's `quality_runs` and the judge's `content_verdicts`,
 * read back through /api/contribute/admin/content-health.
 *
 * Read-mostly by design. The one write, Agree / Disagree on a verdict,
 * records an opinion and touches no card (decision #5 is open).
 */

const STATUS_CLASS: Record<ContentHealthStatus, string> = {
  red: 'bg-red-100 text-red-800 border-red-200',
  amber: 'bg-amber-100 text-amber-800 border-amber-200',
  green: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  grey: 'bg-gray-100 text-gray-600 border-gray-200',
}

function pct(v: number | null | undefined): string {
  if (v == null || !Number.isFinite(v)) return '—'
  return `${Number.isInteger(v) ? v : v.toFixed(1)}%`
}

function StatusPill({ status }: { status: ContentHealthStatus }) {
  return (
    <span
      className={`inline-block rounded-full border px-2 py-0.5 text-[11px] font-medium ${STATUS_CLASS[status]}`}
      data-testid="content-health-status"
    >
      {status === 'grey' ? 'no data yet' : status}
    </span>
  )
}

/** "62% judged, 4% flagged" per question. A question nothing has judged
 * says so instead of showing a hollow 0/0; an uncalibrated one carries the
 * label so its flags are read as a report and not a verdict. */
function judgeLine(j: ContentHealthJudge): string {
  const body =
    j.judged === 0
      ? '0% judged'
      : `${pct(j.judged_pct)} judged, ${pct(j.flag_pct)} flagged`
  return j.calibrated ? body : `${body} · not calibrated`
}

/** A plain-SVG sparkline: no chart library for a 30-day line (the same
 * shape AnalyticsPanel draws). Percent series, so the axis is fixed at
 * 0–100 rather than stretched to the data — a course at 2% and one at 40%
 * must not look alike. */
function Sparkline({
  points,
  label,
  color,
}: {
  points: TrendPoint[]
  label: string
  color: string
}) {
  const w = 240
  const h = 40
  if (points.length === 0) {
    return (
      <div className="text-xs text-gray-500">
        {label}: <span className="italic">no trend yet</span>
      </div>
    )
  }
  const step = points.length > 1 ? w / (points.length - 1) : w
  const y = (v: number) => h - (Math.min(100, Math.max(0, v)) / 100) * h
  const path = points
    .map((p, i) => `${(i * step).toFixed(1)},${y(p.value).toFixed(1)}`)
    .join(' ')
  const last = points[points.length - 1]
  return (
    <div>
      <div className="flex items-baseline justify-between text-xs text-gray-500">
        <span>{label}</span>
        <span className="tabular-nums">now {pct(last.value)}</span>
      </div>
      <svg
        viewBox={`0 0 ${w} ${h + 2}`}
        className="mt-0.5 w-full"
        role="img"
        aria-label={`${label} over ${points.length} runs`}
        preserveAspectRatio="none"
        style={{ height: 40 }}
        data-testid="content-health-sparkline"
      >
        <polyline points={path} fill="none" stroke={color} strokeWidth="2" />
      </svg>
    </div>
  )
}

function CourseDetail({ code }: { code: string }) {
  const qc = useQueryClient()
  const { data, isLoading, isError } = useQuery({
    queryKey: ['content-health', code],
    queryFn: () => getContentHealthCourse(code),
    retry: false,
  })

  // Agree / Disagree — the labels are deliberate. "Accept" on a change
  // request applies nothing today and reviewers act as if it did (plan
  // §2.2); until owner decision #5 lands, this button says what it does:
  // records that a person agreed with the judge. The row leaves the list
  // because the server closes it (disposition ≠ open), not because a card
  // changed.
  const dispose = useMutation({
    mutationFn: ({ id, disposition }: { id: string; disposition: VerdictDisposition }) =>
      disposeVerdict(id, disposition),
    onSuccess: (_res, { id }) => {
      qc.setQueryData<ContentHealthDetail>(['content-health', code], (old) =>
        old ? { ...old, verdicts: old.verdicts.filter((v) => v.id !== id) } : old,
      )
      // The flagged counts in the summary row are built from open verdicts.
      qc.invalidateQueries({ queryKey: ['content-health'], exact: true })
    },
  })

  if (isLoading) return <p className="text-xs text-gray-500">Loading {code}…</p>
  if (isError || !data)
    return <p className="text-xs text-red-600">Couldn’t load the {code} detail.</p>

  const reconcileMetrics = Object.entries(data.reconcile).filter(
    (entry): entry is [string, number] => entry[0] !== 'run_at' && typeof entry[1] === 'number',
  )
  const questions = Object.keys(data.trends.judge_flag_pct)

  return (
    <div className="space-y-3" data-testid={`content-health-detail-${code}`}>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Sparkline points={data.trends.bad_card_pct} label="Bad cards" color="#dc2626" />
        {questions.length === 0 ? (
          <div className="text-xs text-gray-500">
            Judge flags: <span className="italic">no judge runs yet</span>
          </div>
        ) : (
          questions.map((q) => (
            <Sparkline
              key={q}
              points={data.trends.judge_flag_pct[q]}
              label={`Judge flags · ${q}`}
              color="#d97706"
            />
          ))
        )}
      </div>

      {/* Audit rules against the committed baseline: the only column that
          can make a course red on its own. */}
      <div>
        <div className="text-xs font-medium text-gray-600">Audit rules vs baseline</div>
        {data.audit.length === 0 ? (
          <p className="text-xs text-gray-500">No audit rows yet.</p>
        ) : (
          <table className="mt-1 w-full text-xs">
            <thead>
              <tr className="text-start text-gray-500">
                <th className="py-0.5 font-medium">Rule</th>
                <th className="py-0.5 font-medium text-end">Value</th>
                <th className="py-0.5 font-medium text-end">Baseline</th>
                <th className="py-0.5 font-medium text-end">Δ</th>
              </tr>
            </thead>
            <tbody>
              {data.audit.map((r) => (
                <tr key={r.rule} className="border-t border-gray-50 text-gray-700">
                  <td className="py-0.5 font-mono">{r.rule}</td>
                  <td className="py-0.5 text-end tabular-nums">{r.value}</td>
                  <td className="py-0.5 text-end tabular-nums">{r.baseline ?? '—'}</td>
                  <td
                    className={`py-0.5 text-end tabular-nums ${
                      (r.delta ?? 0) > 0 ? 'text-red-600 font-medium' : ''
                    }`}
                  >
                    {r.delta == null ? '—' : r.delta > 0 ? `+${r.delta}` : r.delta}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div>
        <div className="text-xs font-medium text-gray-600">
          Reconcile survey{' '}
          <span className="font-normal text-gray-500">
            · {ago(data.reconcile.run_at)}
          </span>
        </div>
        {reconcileMetrics.length === 0 ? (
          <p className="text-xs text-gray-500">No survey yet.</p>
        ) : (
          <dl className="mt-1 flex flex-wrap gap-x-4 gap-y-0.5 text-xs">
            {reconcileMetrics.map(([metric, value]) => (
              <div key={metric} className="flex gap-1">
                <dt className="text-gray-500">{metric}</dt>
                <dd className="tabular-nums text-gray-800">{value}</dd>
              </div>
            ))}
          </dl>
        )}
      </div>

      <div>
        <div className="text-xs font-medium text-gray-600">
          Open verdicts ({data.verdicts.length})
        </div>
        {data.verdicts.length === 0 ? (
          <p className="text-xs text-gray-500">Nothing open for {data.name}.</p>
        ) : (
          <ul className="mt-1 space-y-1.5" data-testid="content-health-verdicts">
            {data.verdicts.map((v) => (
              <li
                key={v.id}
                className="flex items-start justify-between gap-2 rounded-lg border border-gray-100 bg-white px-2.5 py-1.5"
                data-testid="content-health-verdict"
              >
                <div className="min-w-0 text-xs">
                  <div className="text-gray-800">
                    <span className="font-medium">{v.question}</span> · {v.verdict}
                    {v.category && <span className="text-gray-500"> · {v.category}</span>}
                    <span className="ms-1 tabular-nums text-gray-500">
                      {v.confidence.toFixed(2)}
                    </span>
                    {v.locale && <span className="ms-1 text-gray-400">[{v.locale}]</span>}
                  </div>
                  {v.evidence.length > 0 && (
                    <div className="text-gray-600">“{v.evidence.join('” · “')}”</div>
                  )}
                  {v.expected && (
                    <div className="text-gray-500">
                      expected: <span className="text-gray-700">{v.expected}</span>
                    </div>
                  )}
                  {v.note && <div className="text-[11px] text-gray-400">{v.note}</div>}
                </div>
                <div className="flex shrink-0 gap-1">
                  <button
                    type="button"
                    onClick={() => dispose.mutate({ id: v.id, disposition: 'accepted' })}
                    disabled={dispose.isPending}
                    className="rounded-md bg-emerald-600 px-2 py-1 text-[11px] text-white hover:bg-emerald-700 disabled:opacity-40"
                  >
                    Agree
                  </button>
                  <button
                    type="button"
                    onClick={() => dispose.mutate({ id: v.id, disposition: 'rejected' })}
                    disabled={dispose.isPending}
                    className="rounded-md border border-gray-200 px-2 py-1 text-[11px] text-gray-600 hover:bg-gray-50 disabled:opacity-40"
                  >
                    Disagree
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
        <p className="mt-1 text-[11px] text-gray-500">
          Agree and Disagree record your view of the verdict; nothing is
          applied to the card. Fixes still go through the Workshop.
        </p>
        {dispose.isError && (
          <p className="text-xs text-red-600" role="alert">
            That didn’t save — the verdict may already be closed, or this
            deploy predates migration 20261107000000.
          </p>
        )}
      </div>
    </div>
  )
}

function CourseRow({
  course,
  expanded,
  onToggle,
}: {
  course: ContentHealthCourse
  expanded: boolean
  onToggle: () => void
}) {
  const queueEntries = Object.entries(course.queues)
  const queueTotal = queueEntries.reduce((sum, [, n]) => sum + n, 0)
  const queueTitle = queueEntries.map(([k, n]) => `${k}: ${n}`).join('\n')
  const badOver =
    course.bad_card_pct != null && course.bad_card_pct > course.targets.max_bad_card_pct
  const bandLow =
    course.top_band_covered_pct != null && course.top_band_covered_pct < 95
  const delta = course.audit_fail_delta
  // The server sends one entry per question for every course, judged or not
  // (five today). Until a question has a labelled gold set that is four
  // identical "0% judged - not calibrated" lines on all 27 rows, which buries
  // the one line that carries a number. Show what has been judged; fold the
  // rest into a single line that still names them.
  const questions = Object.entries(course.judge)
  const measured = questions.filter(([, j]) => j.judged > 0)
  const idle = questions.filter(([, j]) => j.judged === 0).map(([q]) => q)

  return (
    <>
      <tr
        onClick={onToggle}
        aria-expanded={expanded}
        data-testid="content-health-row"
        className={`border-t border-gray-50 cursor-pointer align-top ${
          expanded ? 'bg-lang-soft text-gray-900' : 'text-gray-700 hover:bg-gray-50'
        }`}
      >
        <td className="py-1.5 pe-2">
          <span className="font-medium">{course.name}</span>
          <span className="ms-1 font-mono text-[10px] text-gray-400">{course.code}</span>
        </td>
        <td className="py-1.5 pe-2">
          <StatusPill status={course.status} />
        </td>
        <td
          className={`py-1.5 pe-2 text-end tabular-nums ${badOver ? 'text-red-600 font-medium' : ''}`}
          title="Top-band words with no blankable sentence, against the course's target"
        >
          {pct(course.bad_card_pct)}
          <span className="text-gray-400"> / {course.targets.max_bad_card_pct}%</span>
        </td>
        <td
          className={`py-1.5 pe-2 text-end tabular-nums ${bandLow ? 'text-amber-600' : ''}`}
        >
          {pct(course.top_band_covered_pct)}
        </td>
        <td
          className={`py-1.5 pe-2 text-end tabular-nums ${
            delta != null && delta > 0 ? 'text-red-600 font-medium' : ''
          }`}
          title={course.audit_fails == null ? undefined : `${course.audit_fails} audit fails in total`}
        >
          {delta == null ? '—' : delta > 0 ? `+${delta}` : delta}
        </td>
        <td className="py-1.5 pe-2 text-[11px]">
          {questions.length === 0 ? (
            <span className="text-gray-400">—</span>
          ) : (
            <>
              {measured.map(([q, j]) => (
                <div
                  key={q}
                  className="whitespace-nowrap"
                  data-testid={`judge-${course.code}-${q}`}
                >
                  <span className="text-gray-500">{q}</span> {judgeLine(j)}
                </div>
              ))}
              {idle.length > 0 && (
                <div
                  className="whitespace-nowrap text-gray-400"
                  data-testid={`judge-${course.code}-unjudged`}
                  title={`Never judged: ${idle.join(', ')}`}
                >
                  {idle.length} never judged
                </div>
              )}
            </>
          )}
        </td>
        <td className="py-1.5 pe-2 text-end tabular-nums" title={queueTitle || undefined}>
          {queueEntries.length === 0 ? <span className="text-gray-400">—</span> : queueTotal}
        </td>
        <td className="py-1.5 pe-2 whitespace-nowrap text-gray-500">{ago(course.last_audited)}</td>
        <td className="py-1.5 whitespace-nowrap text-gray-500">{ago(course.last_judged)}</td>
      </tr>
      {expanded && (
        <tr className="bg-gray-50/60">
          <td colSpan={9} className="px-3 py-3">
            <CourseDetail code={course.code} />
          </td>
        </tr>
      )}
    </>
  )
}

export default function ContentHealthPanel() {
  const [openCode, setOpenCode] = useState<string | null>(null)
  const { data, isLoading, isError } = useQuery({
    queryKey: ['content-health'],
    queryFn: getContentHealth,
    retry: false,
  })

  const courses = data?.courses ?? []
  const noRows = courses.every((c) => c.status === 'grey')

  return (
    <div
      className="bg-white rounded-2xl border border-gray-100 p-4 text-sm space-y-3"
      data-testid="content-health-panel"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold text-gray-800">Content health</h2>
        {data && (
          <span className="text-xs text-gray-500 tabular-nums" data-testid="content-health-header">
            {new Date(data.generated_at).toLocaleString()} · judge{' '}
            <span className={data.settings.judge_enabled ? 'text-emerald-700' : 'text-gray-700'}>
              {data.settings.judge_enabled ? 'on' : 'off'}
            </span>{' '}
            · spent today {data.spent_today.toLocaleString()} of{' '}
            {data.settings.judge_daily_token_cap.toLocaleString()}
          </span>
        )}
      </div>
      <p className="text-xs text-gray-500">
        Whether each course’s content is <em>right</em>, not whether it exists —
        the nightly loop’s audit, coverage and drift numbers with the judge’s
        open verdicts. Worst course first. Click a row for its trend, audit
        rules and verdicts.
      </p>

      {isLoading && <p className="text-xs text-gray-500">Loading…</p>}
      {isError && <p className="text-sm text-red-600">Couldn’t load content health.</p>}

      {data && !data.available.quality_runs && (
        <p className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800" role="status">
          Content health needs migration 20261107000000 applied — see Rollouts → Deployment.
        </p>
      )}
      {data && data.available.quality_runs && noRows && (
        <p className="text-xs text-gray-500" role="status">
          The nightly cycle has not written anything yet (its first sweep is
          two minutes after a deploy).
        </p>
      )}

      {courses.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-start text-gray-500">
                <th className="py-1 font-medium">Course</th>
                <th className="py-1 font-medium">Status</th>
                <th className="py-1 font-medium text-end">Bad cards</th>
                <th className="py-1 font-medium text-end">Top band</th>
                <th className="py-1 font-medium text-end">Audit Δ</th>
                <th className="py-1 font-medium">Judge</th>
                <th className="py-1 font-medium text-end">Queues</th>
                <th className="py-1 font-medium">Audited</th>
                <th className="py-1 font-medium">Judged</th>
              </tr>
            </thead>
            <tbody>
              {courses.map((c) => (
                <CourseRow
                  key={c.code}
                  course={c}
                  expanded={openCode === c.code}
                  onToggle={() => setOpenCode(openCode === c.code ? null : c.code)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
