import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import TutorMemoryPanel from '../features/settings/TutorMemoryPanel'

vi.mock('../api/tutor', async (orig) => ({
  ...(await orig()),
  getTutorMemory: vi.fn(),
  deleteTutorMemoryFact: vi.fn(),
}))

import { getTutorMemory, deleteTutorMemoryFact } from '../api/tutor'

const mockGet = getTutorMemory as ReturnType<typeof vi.fn>
const mockDelete = deleteTutorMemoryFact as ReturnType<typeof vi.fn>

function renderPanel() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <TutorMemoryPanel />
    </QueryClientProvider>,
  )
}

describe('TutorMemoryPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows facts with their provenance badges', async () => {
    // The exact incident this panel exists for: an inferred
    // native_language the learner could not see, let alone correct.
    mockGet.mockResolvedValue({
      global: [
        { key: 'native_language', value: 'Russian', source: 'inferred' },
        { key: 'motivation', value: 'travel', source: 'stated' },
      ],
      languages: [
        {
          language_id: 'lang-pt',
          name: 'Portuguese',
          code: 'pt',
          facts: [
            { key: 'error_pattern', value: ['drops articles', 'wrong gender'], source: 'inferred' },
          ],
        },
      ],
    })

    renderPanel()

    expect(await screen.findByText(/what your tutor remembers/i)).toBeInTheDocument()
    expect(screen.getByText(/native language/)).toBeInTheDocument()
    // Both inferred facts wear the badge; the stated one wears its own.
    expect(screen.getAllByText(/tutor’s guess/i)).toHaveLength(2)
    expect(screen.getByText(/you told the tutor/i)).toBeInTheDocument()
    // Per-language group with a list value joined for reading.
    expect(screen.getByText('Portuguese')).toBeInTheDocument()
    expect(screen.getByText(/drops articles, wrong gender/)).toBeInTheDocument()
  })

  it('deletes a fact and refetches', async () => {
    mockGet.mockResolvedValue({
      global: [{ key: 'native_language', value: 'Russian', source: 'inferred' }],
      languages: [],
    })
    mockDelete.mockResolvedValue(undefined)

    renderPanel()

    const button = await screen.findByRole('button', {
      name: /forget .*native language/i,
    })
    fireEvent.click(button)

    await waitFor(() => expect(mockDelete).toHaveBeenCalled())
    // react-query appends its own context argument — check ours only.
    expect(mockDelete.mock.calls[0][0]).toEqual({
      scope: 'global',
      key: 'native_language',
    })
    // The list refetches so the fact disappears from the panel.
    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(2))
  })

  it('shows the empty state when the tutor knows nothing', async () => {
    mockGet.mockResolvedValue({ global: [], languages: [] })
    renderPanel()
    expect(await screen.findByText(/nothing yet/i)).toBeInTheDocument()
  })
})
