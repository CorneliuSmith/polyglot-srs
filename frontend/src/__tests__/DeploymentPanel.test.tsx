import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import DeploymentPanel from '../features/settings/DeploymentPanel'

vi.mock('../api/health', () => ({
  getBuildInfo: vi.fn(),
  getSchemaHealth: vi.fn(),
}))
import { getBuildInfo, getSchemaHealth } from '../api/health'
const mockBuild = getBuildInfo as ReturnType<typeof vi.fn>
const mockSchema = getSchemaHealth as ReturnType<typeof vi.fn>

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

describe('DeploymentPanel', () => {
  beforeEach(() => vi.clearAllMocks())

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
})
