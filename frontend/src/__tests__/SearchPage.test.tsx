import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import SearchPage from '../features/search/SearchPage'

vi.mock('../api/profile', () => ({ getLanguages: vi.fn() }))
vi.mock('../api/curriculum', () => ({ searchContent: vi.fn() }))
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn(
    (selector: (s: { activeLanguageId: string }) => unknown) =>
      selector({ activeLanguageId: 'lang-tr' }),
  ),
}))

import { getLanguages } from '../api/profile'
import { searchContent } from '../api/curriculum'

const mockGetLanguages = getLanguages as ReturnType<typeof vi.fn>
const mockSearch = searchContent as ReturnType<typeof vi.fn>

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/search']}>
        <Routes>
          <Route path="/search" element={<SearchPage />} />
          <Route path="/grammar" element={<div data-testid="grammar-page" />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('SearchPage (WP13g)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetLanguages.mockResolvedValue([
      { id: 'lang-tr', code: 'tr', name: 'Turkish', rtl: false },
    ])
    mockSearch.mockResolvedValue({
      grammar: [{
        id: 'g1', title: 'Locative case', level: 'A1',
        function_note: 'in/at/on', learned: true,
      }],
      vocabulary: [{
        id: 'v1', word: 'evde', level: 'A1',
        part_of_speech: 'noun', definition: 'at home', learned: false,
      }],
    })
  })

  it('debounces, searches, and renders grammar + vocabulary sections', async () => {
    renderPage()
    fireEvent.change(screen.getByLabelText('Search'), { target: { value: 'ev' } })

    // Debounced fetch fires once and both sections render.
    await waitFor(() => {
      expect(mockSearch).toHaveBeenCalledWith('lang-tr', 'ev')
    })
    const grammar = await screen.findByTestId('search-grammar')
    expect(grammar.textContent).toContain('Locative case')
    expect(grammar.textContent).toContain('In reviews ✓')
    const vocab = screen.getByTestId('search-vocab')
    expect(vocab.textContent).toContain('evde')
    expect(vocab.textContent).toContain('at home')
  })

  it('a grammar hit deep-links into the path page', async () => {
    renderPage()
    fireEvent.change(screen.getByLabelText('Search'), { target: { value: 'loc' } })
    fireEvent.click(await screen.findByRole('button', { name: /locative case/i }))
    expect(screen.getByTestId('grammar-page')).toBeDefined()
  })

  it('does not search on a single character', async () => {
    renderPage()
    fireEvent.change(screen.getByLabelText('Search'), { target: { value: 'e' } })
    expect(await screen.findByText(/at least 2 characters/i)).toBeDefined()
    expect(mockSearch).not.toHaveBeenCalled()
  })

  it('says so when nothing matches', async () => {
    mockSearch.mockResolvedValue({ grammar: [], vocabulary: [] })
    renderPage()
    fireEvent.change(screen.getByLabelText('Search'), { target: { value: 'zz' } })
    expect(await screen.findByText(/no matches/i)).toBeDefined()
  })
})
