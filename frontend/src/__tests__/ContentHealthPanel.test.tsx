import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ContentHealthPanel from '../features/contribute/ContentHealthPanel'

vi.mock('../api/contribute', async (orig) => ({
  ...(await orig<typeof import('../api/contribute')>()),
  getContentHealth: vi.fn(),
  getContentHealthCourse: vi.fn(),
  disposeVerdict: vi.fn(),
}))

import {
  getContentHealth,
  getContentHealthCourse,
  disposeVerdict,
  type ContentHealthCourse,
  type ContentHealthResponse,
} from '../api/contribute'
const mockHealth = getContentHealth as ReturnType<typeof vi.fn>
const mockCourse = getContentHealthCourse as ReturnType<typeof vi.fn>
const mockDispose = disposeVerdict as ReturnType<typeof vi.fn>

const TARGETS = { judge_enabled: true, max_bad_card_pct: 15, max_judge_flag_pct: 5 }
const JUDGE_CLEAN = {
  judged: 400, population: 2000, judged_pct: 20, flagged: 8, flag_pct: 2, calibrated: true,
}
// Nothing judged yet, which is what four of the five questions look like on
// every course until a gold set is labelled.
const JUDGE_NONE = {
  judged: 0, population: 2000, judged_pct: null, flagged: 0, flag_pct: null, calibrated: false,
}
// The five questions content_judge.QUESTIONS holds. The server emits ONE
// ENTRY PER QUESTION for every course, judged or not — a fixture with one key
// hides both how dense the real cell is and the branches that render the
// unjudged ones.
const QUESTIONS = ['register', 'sense', 'gloss', 'scripture', 'card_shape'] as const
function judgeBlock(over: Record<string, typeof JUDGE_CLEAN> = {}) {
  return Object.fromEntries(
    QUESTIONS.map((q) => [q, over[q] ?? JUDGE_NONE]),
  ) as ContentHealthCourse['judge']
}

function course(over: Partial<ContentHealthCourse>): ContentHealthCourse {
  return {
    code: 'xx', name: 'Course', language_id: 'l-xx', status: 'green', targets: TARGETS,
    bad_card_pct: 10, top_band_covered_pct: 97, audit_fail_delta: 0, audit_fails: 3,
    judge: judgeBlock({ register: JUDGE_CLEAN }),
    queues: { pending_drills: 2, change_requests: 1 },
    reconcile: { gloss: 3, gone: 1, run_at: '2026-09-17T02:00:00Z' },
    last_audited: '2026-09-17T02:00:00Z', last_judged: '2026-09-17T02:00:00Z',
    ...over,
  }
}

// The server's order is the contract: red, amber, green, grey, then code.
const HEALTH: ContentHealthResponse = {
  generated_at: '2026-09-18T02:10:00Z',
  available: {
    quality_runs: true, content_verdicts: true, quality_settings: true,
    language_quality_targets: true,
  },
  settings: {
    judge_enabled: true, judge_rows_per_cycle: 200, judge_daily_token_cap: 1_500_000,
    judge_model: null,
  },
  spent_today: 12_000,
  courses: [
    course({
      code: 'ar', name: 'Arabic', status: 'red', bad_card_pct: 22, audit_fail_delta: 3,
      judge: judgeBlock({ register: { ...JUDGE_CLEAN, flagged: 40, flag_pct: 10 } }),
    }),
    course({
      code: 'ko', name: 'Korean', status: 'amber', top_band_covered_pct: 82,
      // Judged, but the sense question has no gold set yet.
      judge: judgeBlock({ sense: { ...JUDGE_CLEAN, calibrated: false } }),
    }),
    course({
      code: 'es', name: 'Spanish', status: 'green',
      judge: judgeBlock({ sense: { ...JUDGE_NONE, calibrated: true } }),
    }),
    course({
      code: 'sw', name: 'Swahili', status: 'grey', bad_card_pct: null,
      top_band_covered_pct: null, audit_fail_delta: null, audit_fails: null,
      judge: judgeBlock({}), queues: {}, reconcile: { run_at: null },
      last_audited: null, last_judged: null,
    }),
  ],
}

const DETAIL = {
  ...HEALTH.courses[0],
  trends: {
    bad_card_pct: [
      { run_at: '2026-09-16T02:00:00Z', value: 20 },
      { run_at: '2026-09-17T02:00:00Z', value: 22 },
    ],
    judge_flag_pct: { register: [{ run_at: '2026-09-17T02:00:00Z', value: 10 }] },
  },
  audit: [
    { rule: 'leak_hard', value: 5, baseline: 2, delta: 3, population: 2000 },
    { rule: 'wrong_sense', value: 0, baseline: 0, delta: 0, population: 1000 },
  ],
  verdicts: [
    {
      id: 'v1', judged_at: '2026-09-17T02:00:00Z', entity_type: 'vocabulary',
      entity_id: 'e1', field: 'definition', question: 'register', verdict: 'dialect',
      category: 'lexeme', evidence: ['شاف'], confidence: 0.91, expected: 'رأى',
      note: null, judge: 'claude-sonnet-5', disposition: 'open', locale: null,
    },
    {
      id: 'v2', judged_at: '2026-09-17T02:00:00Z', entity_type: 'example_sentence',
      entity_id: 'e2', field: 'sentence', question: 'scripture', verdict: 'scripture',
      category: null, evidence: ['18:24'], confidence: 0.8, expected: null,
      note: null, judge: 'claude-sonnet-5', disposition: 'open', locale: null,
    },
  ],
}

function renderPanel() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <ContentHealthPanel />
    </QueryClientProvider>,
  )
}

describe('ContentHealthPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockHealth.mockResolvedValue(HEALTH)
    mockCourse.mockResolvedValue(DETAIL)
    mockDispose.mockResolvedValue({ id: 'v1', disposition: 'accepted', disposed_at: 'now' })
  })

  it('renders one row per course in the order given, worst first', async () => {
    renderPanel()
    const rows = await screen.findAllByTestId('content-health-row')
    expect(rows.map((r) => within(r).getByText(/Arabic|Korean|Spanish|Swahili/).textContent))
      .toEqual(['Arabic', 'Korean', 'Spanish', 'Swahili'])
    // The header carries the clock and the spend in one line.
    expect(screen.getByTestId('content-health-header').textContent).toContain('judge on')
    expect(screen.getByTestId('content-health-header').textContent).toContain('12,000 of 1,500,000')
  })

  it('names the status; grey reads as "no data yet" rather than a colour', async () => {
    renderPanel()
    const pills = await screen.findAllByTestId('content-health-status')
    expect(pills.map((p) => p.textContent)).toEqual(['red', 'amber', 'green', 'no data yet'])
    // Bad cards against the target, the audit delta signed and only when > 0.
    const [ar] = screen.getAllByTestId('content-health-row')
    expect(ar.textContent).toContain('22% / 15%')
    expect(ar.textContent).toContain('+3')
  })

  it('says when the table is missing, and still draws the (grey) rows', async () => {
    mockHealth.mockResolvedValue({
      ...HEALTH,
      available: { ...HEALTH.available, quality_runs: false },
      courses: HEALTH.courses.map((c) => ({ ...c, status: 'grey' as const })),
    })
    renderPanel()
    expect(await screen.findByText(/migration 20261029/)).toBeDefined()
    expect(screen.getByText(/Rollouts → Deployment/)).toBeDefined()
    expect(screen.getAllByTestId('content-health-row')).toHaveLength(4)
    // The migration banner explains the grey; the "not written yet" line
    // would be a second, wrong explanation.
    expect(screen.queryByText(/nightly cycle has not written/)).toBeNull()
  })

  it('explains an empty table by the loop that has not run yet', async () => {
    mockHealth.mockResolvedValue({
      ...HEALTH,
      courses: HEALTH.courses.map((c) => ({ ...c, status: 'grey' as const })),
    })
    renderPanel()
    expect(await screen.findByText(/nightly cycle has not written anything yet/)).toBeDefined()
    expect(screen.queryByText(/migration 20261029/)).toBeNull()
  })

  it('labels an uncalibrated question, and folds the ones nothing has judged', async () => {
    renderPanel()
    expect((await screen.findByTestId('judge-ko-sense')).textContent).toContain('not calibrated')
    expect(screen.getByTestId('judge-ko-sense').textContent).toContain('20% judged, 2% flagged')
    // Calibrated and judged: no label.
    expect(screen.getByTestId('judge-ar-register').textContent).not.toContain('not calibrated')
    // The server sends all five questions for every course. Four of them have
    // no gold set, so on 27 courses that is four identical "0% judged" lines
    // burying the one that carries a number: they fold into one, which still
    // names them for anyone who looks.
    const folded = screen.getByTestId('judge-es-unjudged')
    expect(folded.textContent).toBe('5 never judged')
    expect(folded.getAttribute('title')).toBe(
      'Never judged: register, sense, gloss, scripture, card_shape',
    )
    // A course with one measured question folds only the other four.
    expect(screen.getByTestId('judge-ko-unjudged').textContent).toBe('4 never judged')
    // And a course nothing has ever touched folds all five, not an em dash.
    expect(screen.getByTestId('judge-sw-unjudged').textContent).toBe('5 never judged')
  })

  it('expands a row into its drill-down: trend, audit rules and open verdicts', async () => {
    renderPanel()
    fireEvent.click(await screen.findByText('Arabic'))
    await waitFor(() => expect(mockCourse).toHaveBeenCalledWith('ar'))
    const detail = await screen.findByTestId('content-health-detail-ar')
    expect(within(detail).getAllByTestId('content-health-sparkline')).toHaveLength(2)
    expect(within(detail).getByText('leak_hard')).toBeDefined()
    expect(within(detail).getAllByTestId('content-health-verdict')).toHaveLength(2)
    expect(within(detail).getByText(/dialect/)).toBeDefined()
    expect(within(detail).getByText(/شاف/)).toBeDefined()
    expect(within(detail).getByText(/nothing is applied to the card/)).toBeDefined()
  })

  it('Agree records the disposition and drops the row; nothing else changes', async () => {
    renderPanel()
    fireEvent.click(await screen.findByText('Arabic'))
    const detail = await screen.findByTestId('content-health-detail-ar')
    const [first] = await within(detail).findAllByTestId('content-health-verdict')
    fireEvent.click(within(first).getByRole('button', { name: 'Agree' }))
    await waitFor(() => expect(mockDispose).toHaveBeenCalledWith('v1', 'accepted'))
    await waitFor(() =>
      expect(within(detail).getAllByTestId('content-health-verdict')).toHaveLength(1),
    )
    const [left] = within(detail).getAllByTestId('content-health-verdict')
    expect(left.textContent).toContain('scripture')
    expect(left.textContent).not.toContain('dialect')
    // The summary re-reads so the flagged counts follow.
    await waitFor(() => expect(mockHealth).toHaveBeenCalledTimes(2))
  })

  it('Disagree is the other disposition, with the same effect on the list', async () => {
    mockDispose.mockResolvedValue({ id: 'v2', disposition: 'rejected', disposed_at: 'now' })
    renderPanel()
    fireEvent.click(await screen.findByText('Arabic'))
    const detail = await screen.findByTestId('content-health-detail-ar')
    const [, second] = await within(detail).findAllByTestId('content-health-verdict')
    fireEvent.click(within(second).getByRole('button', { name: 'Disagree' }))
    await waitFor(() => expect(mockDispose).toHaveBeenCalledWith('v2', 'rejected'))
    await waitFor(() =>
      expect(within(detail).getAllByTestId('content-health-verdict')).toHaveLength(1),
    )
  })
})
