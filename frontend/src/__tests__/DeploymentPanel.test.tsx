import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import DeploymentPanel from '../features/settings/DeploymentPanel'

vi.mock('../api/health', () => ({
  getBuildInfo: vi.fn(),
  getSchemaHealth: vi.fn(),
}))
vi.mock('../api/contribute', async (orig) => ({
  ...(await orig<typeof import('../api/contribute')>()),
  getContentDeploy: vi.fn(),
}))
import { getBuildInfo, getSchemaHealth } from '../api/health'
import { getContentDeploy } from '../api/contribute'
const mockBuild = getBuildInfo as ReturnType<typeof vi.fn>
const mockSchema = getSchemaHealth as ReturnType<typeof vi.fn>
const mockDeploy = getContentDeploy as ReturnType<typeof vi.fn>

const BUILD = {
  sha: 'f61df76abcdef0123456',
  built_at: '2026-09-01T10:00:00Z',
  latest_migration: '20261012000000_show_glosses.sql',
  migrations_shipped: 116,
}

function renderPanel() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <DeploymentPanel />
    </QueryClientProvider>,
  )
}

const SURVEY = {
  build_sha: BUILD.sha,
  available: true,
  courses: [
    {
      code: 'yo', name: 'Yoruba', run_at: new Date(Date.now() - 3 * 3_600_000).toISOString(),
      build_sha: BUILD.sha, gone: 874, gone_with_cards: 12, new: 874, gloss: 3, pos: 1,
      retire: 0, unretire: 0, gp_retire: 0, no_translation: 2,
    },
    {
      code: 'ar', name: 'Arabic', run_at: new Date(Date.now() - 5 * 86_400_000).toISOString(),
      build_sha: 'older00000000', gone: 0, gone_with_cards: 0, new: 4, gloss: 0, pos: 0,
      retire: 2, unretire: 0, gp_retire: 1, no_translation: 0,
    },
  ],
}

describe('DeploymentPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockDeploy.mockResolvedValue(SURVEY)
  })

  it('names the build and the newest migration it expects', async () => {
    mockBuild.mockResolvedValue(BUILD)
    mockSchema.mockResolvedValue({ ok: true, initialized: true, missing_migrations: [], missing: [] })
    renderPanel()
    await waitFor(() =>
      expect(screen.getByTestId('deployment-sha').textContent).toBe('f61df76abcde'),
    )
    expect(screen.getByTestId('deployment-migration').textContent).toBe(
      '20261012000000_show_glosses.sql',
    )
    expect(screen.getByTestId('deployment-schema').textContent).toContain(
      'every migration',
    )
  })

  it('lists the migrations the database is missing, in order', async () => {
    mockBuild.mockResolvedValue(BUILD)
    mockSchema.mockResolvedValue({
      ok: false,
      initialized: true,
      missing_migrations: ['20261009000000_vocab_topic.sql', '20261012000000_show_glosses.sql'],
      missing: ['user_profiles.show_glosses (from 20261012000000_show_glosses.sql)'],
    })
    renderPanel()
    await waitFor(() =>
      expect(screen.getByTestId('deployment-schema').textContent).toContain('behind'),
    )
    const items = screen.getAllByRole('listitem').map((li) => li.textContent)
    expect(items[0]).toBe('20261009000000_vocab_topic.sql')
    expect(items[1]).toBe('20261012000000_show_glosses.sql')
  })

  it('says when the check is blind rather than pretending the schema is fine', async () => {
    // The deployed image shipped no migration files for weeks and the
    // check reported ok:true against a database that was behind.
    mockBuild.mockResolvedValue({ ...BUILD, migrations_shipped: 0, latest_migration: null })
    mockSchema.mockResolvedValue({
      ok: false, initialized: true, missing_migrations: [], missing: [],
      error: 'no migration files in this build',
    })
    renderPanel()
    await waitFor(() =>
      expect(screen.getByTestId('deployment-schema').textContent).toContain('cannot check'),
    )
    expect(screen.getByTestId('deployment-migration').textContent).toBe('none shipped')
  })

  it('does not invent a commit the platform never recorded', async () => {
    mockBuild.mockResolvedValue({ ...BUILD, sha: null })
    mockSchema.mockResolvedValue({ ok: true, initialized: true, missing_migrations: [], missing: [] })
    renderPanel()
    await waitFor(() =>
      expect(screen.getByTestId('deployment-sha').textContent).toContain('not recorded'),
    )
  })

  // The Content section: reconcile's survey persisted by the nightly loop
  // (plan §6) — the content answer to the schema question above it.
  it('tables the reconcile survey per course and dates the newest run', async () => {
    mockBuild.mockResolvedValue(BUILD)
    mockSchema.mockResolvedValue({ ok: true, initialized: true, missing_migrations: [], missing: [] })
    renderPanel()
    const yo = await screen.findByTestId('deployment-content-yo')
    const cells = yo.querySelectorAll('td')
    expect(cells[0].textContent).toContain('Yoruba')
    // gone, with the ones that have learner cards in parentheses
    expect(cells[1].textContent).toBe('874 (12 with cards)')
    expect(cells[2].textContent).toBe('874')
    // drift = gloss + pos
    expect(cells[3].textContent).toBe('4')
    expect(cells[4].textContent).toBe('0')
    const ar = screen.getByTestId('deployment-content-ar')
    expect(ar.querySelectorAll('td')[1].textContent).toBe('0')
    // Arabic's row was measured on a different build than the one serving.
    expect(ar.textContent).toContain('measured on an older build')
    expect(yo.textContent).not.toContain('older build')
    expect(screen.getByTestId('deployment-content-footer').textContent).toContain(
      'Reconcile last ran 3h ago',
    )
    expect(screen.getByText('Files versus database, since the last deploy')).toBeDefined()
  })

  it('names the missing migration instead of an empty content table', async () => {
    mockBuild.mockResolvedValue(BUILD)
    mockSchema.mockResolvedValue({ ok: true, initialized: true, missing_migrations: [], missing: [] })
    mockDeploy.mockResolvedValue({ build_sha: null, available: false, courses: [] })
    renderPanel()
    const content = await screen.findByTestId('deployment-content')
    await waitFor(() => expect(content.textContent).toContain('migration 20261107000000'))
    expect(content.querySelector('table')).toBeNull()
    expect(content.textContent).not.toContain('no reconcile survey yet')
  })

  it('says when the loop has not surveyed anything yet', async () => {
    mockBuild.mockResolvedValue(BUILD)
    mockSchema.mockResolvedValue({ ok: true, initialized: true, missing_migrations: [], missing: [] })
    mockDeploy.mockResolvedValue({ build_sha: BUILD.sha, available: true, courses: [] })
    renderPanel()
    const content = await screen.findByTestId('deployment-content')
    await waitFor(() => expect(content.textContent).toContain('no reconcile survey yet'))
    expect(content.textContent).not.toContain('Reconcile last ran')
  })
})
