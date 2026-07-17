import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import ReaderPage from '../features/reader/ReaderPage'

vi.mock('../api/reader', () => ({
  generateReading: vi.fn(),
  getReadings: vi.fn(() => Promise.resolve([])),
  getReading: vi.fn(),
  explainSentence: vi.fn(),
}))
vi.mock('../api/notes', () => ({ createPersonalCard: vi.fn() }))
vi.mock('../api/profile', () => ({
  getLanguages: vi.fn(() =>
    Promise.resolve([{ id: 'lang-es', code: 'es', name: 'Spanish', rtl: false }]),
  ),
}))
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn(() => 'lang-es'),
}))
vi.mock('../components/SpeakButton', () => ({ default: () => null }))

import { generateReading, explainSentence } from '../api/reader'
import { createPersonalCard } from '../api/notes'

const mockGenerate = generateReading as ReturnType<typeof vi.fn>
const mockExplain = explainSentence as ReturnType<typeof vi.fn>
const mockAddCard = createPersonalCard as ReturnType<typeof vi.fn>

const reading = {
  title: 'El gato',
  sentences: [
    {
      text: 'El gato duerme en la ventana.',
      translation: 'The cat sleeps in the window.',
      tokens: [
        { t: 'El', gloss: 'the' },
        { t: 'gato', gloss: 'cat' },
        { t: 'duerme', gloss: 'sleeps' },
        { t: 'en', gloss: 'in' },
        { t: 'la', gloss: 'the' },
        { t: 'ventana.', gloss: 'window', new: true },
      ],
    },
  ],
  new_words: [{ word: 'ventana', gloss: 'window', sentence_index: 0 }],
  structures: ['Present tense'],
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/read']}>
        <ReaderPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

async function generate() {
  mockGenerate.mockResolvedValue({
    id: 'r-1',
    reading,
    level: 'A1',
    allowance: { unlimited: true },
  })
  renderPage()
  const input = await screen.findByPlaceholderText(/street food/i)
  fireEvent.change(input, { target: { value: 'cats' } })
  fireEvent.click(screen.getByRole('button', { name: /write it/i }))
  await screen.findByText('El gato')
}

describe('ReaderPage (WP21)', () => {
  beforeEach(() => vi.clearAllMocks())

  it('stage 1 forces guessing: only new words tappable, gloss after a guess', async () => {
    await generate()
    expect(screen.getByTestId('guess-banner')).toBeDefined()
    // Known words are plain text, not buttons.
    expect(screen.queryByRole('button', { name: 'gato' })).toBeNull()
    // The seeded word is tappable.
    fireEvent.click(screen.getByRole('button', { name: 'ventana.' }))
    const panel = await screen.findByTestId('guess-panel')
    expect(panel.textContent).toContain('ventana')
    // Gloss is NOT visible until the guess is committed.
    expect(screen.queryByText(/\(window\)/)).toBeNull()
    fireEvent.change(screen.getByPlaceholderText(/your guess/i), {
      target: { value: 'window?' },
    })
    fireEvent.click(screen.getByRole('button', { name: /reveal/i }))
    expect(await screen.findByText(/\(window\)/)).toBeDefined()
  })

  it('stage 2 unlocks glosses and translations for everything', async () => {
    await generate()
    fireEvent.click(
      screen.getByRole('button', { name: /unlock translations/i }),
    )
    // Now every word is tappable.
    fireEvent.click(screen.getByRole('button', { name: 'gato' }))
    expect(await screen.findByText(/\(cat\)/)).toBeDefined()
    fireEvent.click(screen.getByRole('button', { name: /^translation$/i }))
    expect(
      await screen.findByText('The cat sleeps in the window.'),
    ).toBeDefined()
  })

  it('stage 3 explains on demand, then hides/shows without refetching', async () => {
    mockExplain.mockResolvedValue(
      'A simple statement.\nEl gato — the subject\nduerme — third person singular verb',
    )
    await generate()
    fireEvent.click(
      screen.getByRole('button', { name: /unlock translations/i }),
    )
    fireEvent.click(screen.getByRole('button', { name: /explain the grammar/i }))
    expect(await screen.findByTestId('sentence-explanation')).toBeDefined()
    expect(mockExplain).toHaveBeenCalledWith('r-1', 0)

    // Hide-able (owner feedback) — and toggling never refetches.
    fireEvent.click(screen.getByRole('button', { name: /hide explanation/i }))
    expect(screen.queryByTestId('sentence-explanation')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: /show explanation/i }))
    expect(screen.getByTestId('sentence-explanation')).toBeDefined()
    expect(mockExplain).toHaveBeenCalledTimes(1)

    // Formatted through ExplanationView: each chunk-line renders as its
    // own spaced paragraph, not one squashed blob.
    const paragraphs = screen
      .getByTestId('sentence-explanation')
      .querySelectorAll('p')
    expect(paragraphs.length).toBeGreaterThanOrEqual(3)
  })

  it('new words can be added to reviews with their own sentence', async () => {
    mockAddCard.mockResolvedValue({ id: 'c-1', sentence: 'x' })
    await generate()
    fireEvent.click(
      screen.getByRole('button', { name: /unlock translations/i }),
    )
    fireEvent.click(
      await screen.findByRole('button', { name: /add to reviews/i }),
    )
    await waitFor(() =>
      expect(mockAddCard).toHaveBeenCalledWith(
        expect.objectContaining({
          answer: 'ventana',
          sentence: 'El gato duerme en la ventana.',
        }),
      ),
    )
    expect(await screen.findByText(/in your reviews/i)).toBeDefined()
  })
})
