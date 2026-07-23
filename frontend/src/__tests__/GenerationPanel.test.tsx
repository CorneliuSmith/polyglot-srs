import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import GenerationPanel from '../features/contribute/GenerationPanel'

vi.mock('../api/contribute', async (orig) => ({
  ...(await orig<typeof import('../api/contribute')>()),
  getGenerationCoverage: vi.fn(),
  runGeneration: vi.fn(),
}))

import { getGenerationCoverage, runGeneration } from '../api/contribute'
const mockCoverage = getGenerationCoverage as ReturnType<typeof vi.fn>
const mockRun = runGeneration as ReturnType<typeof vi.fn>

const COVERAGE = {
  available: true,
  coverage: [
    {
      language_id: 'l-sw', language_code: 'sw', language_name: 'Swahili',
      vocab_total: 100, vocab_no_examples: 80, grammar_total: 20,
      grammar_no_drills: 5, ai_examples: 0, ai_drills: 0, low_resource: true,
      sentence_model: 'claude-opus-4-8', grammar_model: 'claude-opus-4-8',
      unfilled: 85,
    },
    {
      language_id: 'l-es', language_code: 'es', language_name: 'Spanish',
      vocab_total: 500, vocab_no_examples: 10, grammar_total: 40,
      grammar_no_drills: 0, ai_examples: 3, ai_drills: 1, low_resource: false,
      sentence_model: 'claude-sonnet-5', grammar_model: 'claude-sonnet-5',
      unfilled: 10,
    },
  ],
  recommended_next: [
    { language_id: 'l-sw', language_code: 'sw', language_name: 'Swahili', unfilled: 85, low_resource: true },
    { language_id: 'l-es', language_code: 'es', language_name: 'Spanish', unfilled: 10, low_resource: false },
  ],
  limits: { max_items: 100, max_per_item: 10 },
}

function renderPanel() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={qc}>
      <GenerationPanel />
    </QueryClientProvider>,
  )
}

describe('GenerationPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockCoverage.mockResolvedValue(COVERAGE)
  })

  it('shows coverage, model rec, and defaults to the top suggested language', async () => {
    renderPanel()
    expect(await screen.findByText(/content generation/i)).toBeDefined()
    expect(screen.getByText('Key ready')).toBeDefined()
    // Both languages listed; Swahili (top suggested) is the default selection,
    // so its low-resource model shows in the run controls.
    expect(screen.getAllByText('Swahili').length).toBeGreaterThan(0)
    expect(screen.getByText('claude-opus-4-8')).toBeDefined()
    // 80 vocab words without examples for the default (Swahili, vocab kind)
    expect(screen.getByText(/80 words without examples/i)).toBeDefined()
  })

  it('previews cost via a dry run without generating', async () => {
    mockRun.mockResolvedValue({
      dry_run: true, kind: 'vocab', model: 'claude-opus-4-8', target_per_item: 3,
      items_to_process: 25, sentences_to_attempt: 75, est_cost_usd: 0.42,
    })
    renderPanel()
    await screen.findByText(/content generation/i)
    fireEvent.click(screen.getByRole('button', { name: /preview cost/i }))
    await waitFor(() => expect(mockRun).toHaveBeenCalled())
    expect(mockRun.mock.calls[0][0].dryRun).toBe(true)
    expect(await screen.findByText(/~\$0\.42/)).toBeDefined()
  })

  it('generates for real after confirm, then reports the analysis', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    mockRun.mockResolvedValue({
      dry_run: false, kind: 'vocab', language_code: 'sw', language_name: 'Swahili',
      model: 'claude-opus-4-8', target_per_item: 3, items_processed: 25,
      sentences_attempted: 75, sentences_accepted: 60, sentences_persisted: 58,
      duplicates_skipped: 2, est_cost_usd: 0.31,
    })
    renderPanel()
    await screen.findByText(/content generation/i)
    fireEvent.click(screen.getByRole('button', { name: /generate now/i }))
    await waitFor(() => expect(mockRun).toHaveBeenCalled())
    expect(mockRun.mock.calls[0][0].dryRun).toBe(false)
    expect(await screen.findByText(/saved/i)).toBeDefined()
    expect(screen.getByText(/58/)).toBeDefined()
  })

  it('does not generate if the confirm is dismissed', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    renderPanel()
    await screen.findByText(/content generation/i)
    fireEvent.click(screen.getByRole('button', { name: /generate now/i }))
    expect(mockRun).not.toHaveBeenCalled()
  })

  it('disables real generation when the server has no key', async () => {
    mockCoverage.mockResolvedValue({ ...COVERAGE, available: false })
    renderPanel()
    await screen.findByText(/content generation/i)
    expect(screen.getByText('No server key')).toBeDefined()
    expect(
      (screen.getByRole('button', { name: /generate now/i }) as HTMLButtonElement)
        .disabled,
    ).toBe(true)
  })
})
