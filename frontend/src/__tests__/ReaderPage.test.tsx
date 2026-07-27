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
vi.mock('../api/tutor', () => ({
  getUsageAllowance: vi.fn(() =>
    Promise.resolve({ available: false, allowance: null }),
  ),
}))

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
  // TTS language → the text is held back behind the listen-first prompt.
  await screen.findByTestId('listen-first')
  fireEvent.click(screen.getByRole('button', { name: /show me the text/i }))
  await screen.findByText('El gato')
}

describe('ReaderPage (WP21)', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows the usage meter next to the write-it form when AI is enabled', async () => {
    const { getUsageAllowance } = await import('../api/tutor')
    ;(getUsageAllowance as ReturnType<typeof vi.fn>).mockResolvedValue({
      available: true,
      allowance: {
        tier: 'free', unlimited: false, entitled: false,
        limit: 20, used: 10, remaining: 10, resets_at: '2026-08-01T00:00:00+00:00',
      },
    })
    renderPage()
    expect(await screen.findByTestId('usage-meter')).toBeDefined()
  })

  it('text options shape the request: length, style, challenge', async () => {
    mockGenerate.mockResolvedValue({
      id: 'r-1', reading, level: 'A1', allowance: { unlimited: true },
    })
    renderPage()
    const input = await screen.findByPlaceholderText(/street food/i)
    fireEvent.change(input, { target: { value: 'cats' } })
    fireEvent.click(screen.getByRole('button', { name: /^short$/i }))
    fireEvent.click(screen.getByRole('button', { name: /^dialogue$/i }))
    fireEvent.click(screen.getByRole('button', { name: /^stretch$/i }))
    fireEvent.click(screen.getByRole('button', { name: /write it/i }))
    await screen.findByTestId('listen-first')
    expect(mockGenerate).toHaveBeenCalledWith('lang-es', 'es', 'cats', {
      length: 'short',
      voice: 'dialogue',
      complexity: 'stretch',
    })
  })

  it('listen-first holds the text back until the learner chooses', async () => {
    mockGenerate.mockResolvedValue({
      id: 'r-1', reading, level: 'A1', allowance: { unlimited: true },
    })
    renderPage()
    const input = await screen.findByPlaceholderText(/street food/i)
    fireEvent.change(input, { target: { value: 'cats' } })
    fireEvent.click(screen.getByRole('button', { name: /write it/i }))

    // The text is NOT shown — the choice comes first.
    await screen.findByTestId('listen-first')
    expect(screen.queryByText('El gato')).toBeNull()

    // Ear mode: numbered play-only lines, text still hidden.
    fireEvent.click(screen.getByRole('button', { name: /listen first/i }))
    expect(await screen.findByTestId('listen-lines')).toBeDefined()
    expect(screen.queryByText('El gato')).toBeNull()

    // Reveal → normal guess stage.
    fireEvent.click(screen.getByRole('button', { name: /show the text/i }))
    expect(await screen.findByText('El gato')).toBeDefined()
    expect(screen.getByTestId('guess-banner')).toBeDefined()
  })

  it('stage 1 forces guessing: two tries before the gloss ever shows', async () => {
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
    // First guess NEVER auto-reveals — it's locked in for a second thought.
    fireEvent.click(screen.getByRole('button', { name: /lock it in/i }))
    expect(await screen.findByTestId('second-chance')).toBeDefined()
    expect(screen.getByText(/“window\?”/)).toBeDefined()
    expect(screen.queryByText(/\(window\)/)).toBeNull()
    // Second submit reveals.
    fireEvent.click(screen.getByRole('button', { name: /reveal/i }))
    expect(await screen.findByText(/\(window\)/)).toBeDefined()
  })

  it('the second chance can be waived: standing by the first guess reveals', async () => {
    await generate()
    fireEvent.click(screen.getByRole('button', { name: 'ventana.' }))
    await screen.findByTestId('guess-panel')
    fireEvent.change(screen.getByPlaceholderText(/your guess/i), {
      target: { value: 'door' },
    })
    fireEvent.click(screen.getByRole('button', { name: /lock it in/i }))
    fireEvent.click(
      await screen.findByRole('button', { name: /standing by my first guess/i }),
    )
    expect(await screen.findByText(/\(window\)/)).toBeDefined()
  })

  it('an empty guess (just show me) reveals without the second-chance loop', async () => {
    await generate()
    fireEvent.click(screen.getByRole('button', { name: 'ventana.' }))
    await screen.findByTestId('guess-panel')
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
    fireEvent.click(screen.getAllByRole('button', { name: /^grammar$/i })[0])
    expect(await screen.findByTestId('sentence-explanation')).toBeDefined()
    expect(mockExplain).toHaveBeenCalledWith('r-1', 0)

    // Hide-able (owner feedback) — the same pill toggles, never refetches.
    fireEvent.click(screen.getAllByRole('button', { name: /^grammar$/i })[0])
    expect(screen.queryByTestId('sentence-explanation')).toBeNull()
    fireEvent.click(screen.getAllByRole('button', { name: /^grammar$/i })[0])
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
          // The gloss rides along as the fallback prompt for inflected words.
          gloss: 'window',
        }),
      ),
    )
    expect(await screen.findByTestId('word-added')).toBeDefined()
  })

  it('a failed add surfaces an error and offers a retry (no silent 422)', async () => {
    mockAddCard.mockRejectedValue(new Error('422'))
    await generate()
    fireEvent.click(
      screen.getByRole('button', { name: /unlock translations/i }),
    )
    fireEvent.click(
      await screen.findByRole('button', { name: /add to reviews/i }),
    )
    expect(await screen.findByText(/couldn't add/i)).toBeDefined()
    expect(screen.getByRole('button', { name: /retry/i })).toBeDefined()
  })
})
