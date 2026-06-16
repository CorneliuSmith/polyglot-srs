import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import NotesPage from '../features/notes/NotesPage'

vi.mock('../api/profile', () => ({ getLanguages: vi.fn() }))
vi.mock('../api/notes', () => ({
  extractText: vi.fn(),
  createPersonalCard: vi.fn(),
  saveNote: vi.fn(),
}))
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn(() => 'lang-es'),
}))

import { getLanguages } from '../api/profile'
import { extractText, createPersonalCard, saveNote } from '../api/notes'

const mockGetLanguages = getLanguages as ReturnType<typeof vi.fn>
const mockExtract = extractText as ReturnType<typeof vi.fn>
const mockCreate = createPersonalCard as ReturnType<typeof vi.fn>
const mockSaveNote = saveNote as ReturnType<typeof vi.fn>

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <NotesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('NotesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetLanguages.mockResolvedValue([{ id: 'lang-es', code: 'es', name: 'Spanish', rtl: false }])
  })

  it('analyzes text and turns a clicked word into a card', async () => {
    mockExtract.mockResolvedValue([
      {
        sentence: 'El gato duerme.',
        words: [
          { word: 'El', normalized: 'el', known: true, definition: null },
          { word: 'gato', normalized: 'gato', known: false, definition: null },
          { word: 'duerme', normalized: 'duerme', known: true, definition: 'sleeps' },
        ],
      },
    ])
    mockCreate.mockResolvedValue({ id: 'card-1', sentence: 'El {{answer}} duerme.' })
    mockSaveNote.mockResolvedValue({ id: 'note-1' })

    renderPage()

    // Wait for the language to load, then paste + analyze.
    const textarea = await screen.findByPlaceholderText(/paste spanish text/i)
    fireEvent.change(textarea, { target: { value: 'El gato duerme.' } })
    fireEvent.click(screen.getByRole('button', { name: /analyze/i }))

    // The new word renders as a clickable button; pick it.
    const gato = await screen.findByRole('button', { name: 'gato' })
    fireEvent.click(gato)

    fireEvent.change(screen.getByPlaceholderText(/translation/i), {
      target: { value: 'The cat sleeps.' },
    })
    fireEvent.click(screen.getByRole('button', { name: /add card/i }))

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          languageId: 'lang-es',
          languageCode: 'es',
          sentence: 'El gato duerme.',
          answer: 'gato',
          translation: 'The cat sleeps.',
          noteId: 'note-1',
        }),
      )
    })
    // The source passage is saved once and the card links back to it.
    expect(mockSaveNote).toHaveBeenCalledWith('lang-es', 'El gato duerme.', 'El gato duerme.')
    expect(await screen.findByText(/added 1 card/i)).toBeDefined()
  })

  it('prompts to pick a language when none is active', async () => {
    const { usePrefsStore } = await import('../stores/prefsStore')
    ;(usePrefsStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue(null)
    renderPage()
    expect(await screen.findByText(/pick a language on the dashboard/i)).toBeDefined()
  })
})
