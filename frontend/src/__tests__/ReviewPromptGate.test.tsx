import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ReviewPromptGate from '../features/dashboard/ReviewPromptGate'

vi.mock('../api/contribute', () => ({
  getReviewPrompt: vi.fn(),
  answerReviewPrompt: vi.fn(() =>
    Promise.resolve({ next_prompt_at: '2026-08-01T00:00:00Z' }),
  ),
}))
vi.mock('../api/profile', () => ({
  getLanguages: vi.fn(() => Promise.resolve([{ id: 'l-sw', code: 'sw', name: 'Swahili', rtl: false }])),
}))

import { getReviewPrompt, answerReviewPrompt } from '../api/contribute'
const mockGet = getReviewPrompt as ReturnType<typeof vi.fn>
const mockAnswer = answerReviewPrompt as ReturnType<typeof vi.fn>

const PROMPT = {
  target_type: 'drill' as const, target_id: 'd1', language_id: 'l-sw',
  context: 'Present tense', sentence: 'Yeye {{answer}} chai.', answer: 'anakunywa',
  translation: 'She drinks tea.', word: null,
  question: "Is this a correct, natural drill you'd approve for learners?",
}

function renderGate() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  render(
    <QueryClientProvider client={qc}>
      <ReviewPromptGate />
    </QueryClientProvider>,
  )
}

describe('ReviewPromptGate', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders nothing when no nudge is due', async () => {
    mockGet.mockResolvedValue({ due: false })
    renderGate()
    await waitFor(() => expect(mockGet).toHaveBeenCalled())
    expect(screen.queryByTestId('review-prompt-gate')).toBeNull()
  })

  it('shows the pending item + question when due, filling the drill blank', async () => {
    mockGet.mockResolvedValue({ due: true, prompt: PROMPT })
    renderGate()
    expect(await screen.findByTestId('review-prompt-gate')).toBeDefined()
    expect(screen.getByText(/approve for learners/i)).toBeDefined()
    // The {{answer}} blank is shown filled so the reviewer reads the whole drill.
    expect(screen.getByText(/【anakunywa】/)).toBeDefined()
  })

  it('records an approve recommendation, then confirms and lets the user continue', async () => {
    mockGet.mockResolvedValue({ due: true, prompt: PROMPT })
    renderGate()
    fireEvent.click(await screen.findByRole('button', { name: /looks good/i }))
    await waitFor(() =>
      expect(mockAnswer).toHaveBeenCalledWith(
        expect.objectContaining({ targetId: 'd1', recommendation: 'approve' }),
      ),
    )
    expect(await screen.findByText(/thanks/i)).toBeDefined()
    // Tells them contributing earns a longer gap.
    expect(screen.getByText(/less often/i)).toBeDefined()
    // Dismiss after answering removes the gate.
    fireEvent.click(screen.getByRole('button', { name: /continue to dashboard/i }))
    await waitFor(() => expect(screen.queryByTestId('review-prompt-gate')).toBeNull())
  })

  it('lets a reviewer skip when they can’t tell', async () => {
    mockGet.mockResolvedValue({ due: true, prompt: PROMPT })
    renderGate()
    fireEvent.click(await screen.findByRole('button', { name: /can't tell/i }))
    await waitFor(() =>
      expect(mockAnswer).toHaveBeenCalledWith(
        expect.objectContaining({ recommendation: 'skip' }),
      ),
    )
  })
})
