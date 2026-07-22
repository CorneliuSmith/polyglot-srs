import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import DrillsEditor from '../features/contribute/DrillsEditor'

vi.mock('../api/contribute', () => ({
  getDrills: vi.fn(),
  addDrill: vi.fn(),
  deleteDrill: vi.fn(),
}))

import { getDrills, addDrill } from '../api/contribute'

const mockGetDrills = getDrills as ReturnType<typeof vi.fn>
const mockAddDrill = addDrill as ReturnType<typeof vi.fn>

function renderEditor() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <DrillsEditor pointId="p1" />
    </QueryClientProvider>,
  )
}

describe('DrillsEditor', () => {
  beforeEach(() => vi.clearAllMocks())

  it('is collapsed and does not fetch until opened', () => {
    renderEditor()
    expect(mockGetDrills).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: /edit sentences/i })).toBeDefined()
  })

  it('lists drills and adds a new one', async () => {
    mockGetDrills.mockResolvedValue([
      { id: 'd1', sentence: 'Kitap {{answer}}.', answer: 'masada', translation: 'on the table', hint: null, display_order: 1 },
    ])
    mockAddDrill.mockResolvedValue({ id: 'd2' })
    renderEditor()

    fireEvent.click(screen.getByRole('button', { name: /edit sentences/i }))
    expect(await screen.findByText(/Kitap \{\{answer\}\}\./)).toBeDefined()

    fireEvent.change(screen.getByPlaceholderText(/sentence with/i), {
      target: { value: 'Araba {{answer}}.' },
    })
    fireEvent.change(screen.getByPlaceholderText("Answer (e.g. masada)"), {
      target: { value: 'garajda' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Add' }))

    await waitFor(() => {
      expect(mockAddDrill).toHaveBeenCalledWith('p1', {
        sentence: 'Araba {{answer}}.',
        answer: 'garajda',
        translation: '',
      })
    })
  })

  it('badges each drill by provenance (ours / imported / edited)', async () => {
    mockGetDrills.mockResolvedValue([
      { id: 'd1', sentence: 'A {{answer}}.', answer: 'x', translation: null, hint: null, display_order: 1, source: 'seed', is_modified: false },
      { id: 'd2', sentence: 'B {{answer}}.', answer: 'y', translation: null, hint: null, display_order: 2, source: 'tatoeba', is_modified: false },
      { id: 'd3', sentence: 'C {{answer}}.', answer: 'z', translation: null, hint: null, display_order: 3, source: 'seed', is_modified: true },
    ])
    renderEditor()
    fireEvent.click(screen.getByRole('button', { name: /edit sentences/i }))
    // seed → "ours"; tatoeba → its source; an edited row → "edited" (wins).
    expect(await screen.findByText('ours')).toBeDefined()
    expect(screen.getByText('tatoeba')).toBeDefined()
    expect(screen.getByText('edited')).toBeDefined()
  })

  it('shows the server validation message when a drill is rejected', async () => {
    mockGetDrills.mockResolvedValue([])
    mockAddDrill.mockRejectedValue({
      response: { data: { detail: 'The sentence must contain the {{answer}} blank...' } },
    })
    renderEditor()

    fireEvent.click(screen.getByRole('button', { name: /edit sentences/i }))
    fireEvent.change(await screen.findByPlaceholderText(/sentence with/i), {
      target: { value: 'no blank' },
    })
    fireEvent.change(screen.getByPlaceholderText("Answer (e.g. masada)"), { target: { value: 'x' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add' }))

    expect(await screen.findByText(/must contain the/i)).toBeDefined()
  })
})
