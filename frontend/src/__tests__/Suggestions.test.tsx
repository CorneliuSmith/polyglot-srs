import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import SuggestionsPanel from '../features/contribute/SuggestionsPanel'
import SuggestionMetricsPanel from '../features/contribute/SuggestionMetricsPanel'
import SuggestEditModal from '../features/contribute/SuggestEditModal'

vi.mock('../api/contribute', () => ({
  getSuggestions: vi.fn(),
  approveSuggestion: vi.fn(),
  rejectSuggestion: vi.fn(),
  submitSuggestion: vi.fn(),
  getSuggestionMetrics: vi.fn(),
}))
vi.mock('../components/LanguageWrapper', () => ({
  default: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))
import {
  getSuggestions,
  approveSuggestion,
  rejectSuggestion,
  submitSuggestion,
  getSuggestionMetrics,
} from '../api/contribute'

const mockGet = getSuggestions as ReturnType<typeof vi.fn>
const mockApprove = approveSuggestion as ReturnType<typeof vi.fn>
const mockReject = rejectSuggestion as ReturnType<typeof vi.fn>
const mockSubmit = submitSuggestion as ReturnType<typeof vi.fn>
const mockMetrics = getSuggestionMetrics as ReturnType<typeof vi.fn>

function wrap(node: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{node}</QueryClientProvider>)
}

describe('SuggestionsPanel', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows a current → proposed diff and approves', async () => {
    mockGet.mockResolvedValue([
      {
        id: 's1', entity_type: 'vocabulary', entity_id: 'v1', card_title: 'a',
        current: { definition: 'bishop' }, proposed: { definition: 'to; at' },
        note: 'wrong sense', status: 'pending', created_at: null,
      },
    ])
    mockApprove.mockResolvedValue(undefined)
    wrap(<SuggestionsPanel languageId="lang-es" />)
    await waitFor(() => expect(screen.getByTestId('suggestions')).toBeDefined())
    expect(screen.getByText('bishop')).toBeDefined()
    expect(screen.getByText('to; at')).toBeDefined()
    fireEvent.click(screen.getByText('Approve'))
    await waitFor(() => expect(mockApprove).toHaveBeenCalledWith('s1'))
  })

  it('renders nothing when the queue is empty', async () => {
    mockGet.mockResolvedValue([])
    const { container } = wrap(<SuggestionsPanel languageId="lang-es" />)
    await waitFor(() => expect(mockGet).toHaveBeenCalled())
    expect(container.querySelector('[data-testid="suggestions"]')).toBeNull()
  })

  it('declines a suggestion', async () => {
    mockGet.mockResolvedValue([
      { id: 's2', entity_type: 'vocabulary', entity_id: 'v2', card_title: 'mi',
        current: {}, proposed: { definition: 'my' }, note: null,
        status: 'pending', created_at: null },
    ])
    mockReject.mockResolvedValue(undefined)
    wrap(<SuggestionsPanel languageId="lang-es" />)
    await waitFor(() => expect(screen.getByText('Decline')).toBeDefined())
    fireEvent.click(screen.getByText('Decline'))
    await waitFor(() => expect(mockReject).toHaveBeenCalledWith('s2'))
  })

  it('badges a doc re-seed proposal and filters to it', async () => {
    mockGet.mockResolvedValue([
      { id: 'c1', entity_type: 'vocabulary', entity_id: 'v1', card_title: 'uno',
        current: { definition: 'one' }, proposed: { definition: 'a, one' },
        note: null, status: 'pending', source: 'contributor', origin: null,
        created_at: null },
      { id: 'e1', entity_type: 'vocabulary', entity_id: 'v2', card_title: 'dos',
        current: { part_of_speech: 'noun' }, proposed: { part_of_speech: 'num' },
        note: null, status: 'pending', source: 'extraction',
        origin: 'document re-seed (es)', created_at: null },
    ])
    wrap(<SuggestionsPanel languageId="lang-es" />)
    await waitFor(() => expect(screen.getByTestId('suggestions')).toBeDefined())
    // the extraction row carries the AI · doc badge
    expect(screen.getByText('AI · doc', { selector: 'span' })).toBeDefined()
    // both cards visible under "All"
    expect(screen.getByText('uno')).toBeDefined()
    expect(screen.getByText('dos')).toBeDefined()
    // filtering to the doc chip hides the contributor card
    fireEvent.click(screen.getByRole('button', { name: /AI · doc \(1\)/ }))
    await waitFor(() => expect(screen.queryByText('uno')).toBeNull())
    expect(screen.getByText('dos')).toBeDefined()
  })
})

describe('SuggestionMetricsPanel', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows the acceptance rate for doc AI recommendations', async () => {
    mockMetrics.mockResolvedValue({
      total: 10, pending: 2, approved: 6, rejected: 2, resolved: 8,
      acceptance_rate: 0.75,
    })
    wrap(<SuggestionMetricsPanel />)
    await waitFor(() => expect(screen.getByTestId('suggestion-metrics')).toBeDefined())
    expect(screen.getByText('75%')).toBeDefined()
  })

  it('renders nothing when there are no doc recommendations', async () => {
    mockMetrics.mockResolvedValue({
      total: 0, pending: 0, approved: 0, rejected: 0, resolved: 0,
      acceptance_rate: null,
    })
    const { container } = wrap(<SuggestionMetricsPanel />)
    await waitFor(() => expect(mockMetrics).toHaveBeenCalled())
    expect(container.querySelector('[data-testid="suggestion-metrics"]')).toBeNull()
  })
})

describe('SuggestEditModal', () => {
  beforeEach(() => vi.clearAllMocks())

  it('live-previews edits and submits only changed fields', async () => {
    mockSubmit.mockResolvedValue({ id: 'new' })
    wrap(
      <SuggestEditModal
        entityType="vocabulary" entityId="v1" word="a" languageCode="es"
        current={{ definition: 'bishop', part_of_speech: 'noun', usage_note: '' }}
        onClose={() => {}}
      />,
    )
    const defInput = screen.getByDisplayValue('bishop')
    fireEvent.change(defInput, { target: { value: 'to; at' } })
    // preview reflects the edited definition
    const preview = screen.getByTestId('card-preview')
    await waitFor(() => expect(preview.textContent).toContain('to; at'))
    fireEvent.click(screen.getByText(/Submit/))
    await waitFor(() => expect(mockSubmit).toHaveBeenCalled())
    const arg = mockSubmit.mock.calls[0][0]
    expect(arg.proposed.definition).toBe('to; at')
    // part_of_speech unchanged → not in the patch
    expect(arg.proposed.part_of_speech).toBeUndefined()
  })
})
