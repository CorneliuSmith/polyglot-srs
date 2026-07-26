import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { LETTERS } from '../features/letters/lettersData'
import LettersPage from '../features/letters/LettersPage'

vi.mock('../api/profile', () => ({
  getLanguages: vi.fn(),
}))
// The page reads the LIVE active language from the prefs store (the cached
// profile query lagged language switches — the ru/tr/ar leak from beta).
let mockActiveId = 'lang-es'
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn(
    (selector: (s: Record<string, unknown>) => unknown) =>
      selector({ activeLanguageId: mockActiveId, qwertyTranslit: {} }),
  ),
}))

import { getLanguages } from '../api/profile'

const mockGetLanguages = getLanguages as ReturnType<typeof vi.fn>

const ALL_CODES = [
  'ar', 'ca', 'de', 'el', 'en', 'es', 'fr', 'ha', 'hi', 'it', 'jam',
  'ko', 'mi', 'nl', 'pt', 'ro', 'ru', 'sw', 'th', 'tr', 'xh', 'yo',
]

describe('Letters & Sounds data', () => {
  it('covers every seeded language', () => {
    for (const code of ALL_CODES) {
      expect(LETTERS[code], `letters data missing for ${code}`).toBeDefined()
    }
  })

  it('every row is complete', () => {
    for (const [code, lang] of Object.entries(LETTERS)) {
      expect(lang.sections.length, code).toBeGreaterThan(0)
      for (const section of lang.sections) {
        expect(section.rows.length, `${code}/${section.title}`).toBeGreaterThan(0)
        for (const row of section.rows) {
          expect(row.char.trim(), `${code}/${section.title}`).not.toBe('')
          expect(row.example.trim(), `${code}/${section.title}`).not.toBe('')
          expect(row.sound.trim(), `${code}/${section.title}`).not.toBe('')
        }
      }
    }
  })

  it('the script languages carry typing keys', () => {
    for (const code of ['ru', 'el', 'ar', 'hi', 'th', 'ko']) {
      const withRoman = LETTERS[code].sections
        .flatMap((s) => s.rows)
        .filter((r) => r.roman)
      expect(withRoman.length, code).toBeGreaterThan(5)
    }
  })

  it('Arabic letter sections carry positional forms, one letter per row', () => {
    const positional = LETTERS.ar.sections.filter((s) => s.positions)
    // The full 28-letter inventory lives in positional sections.
    expect(positional.flatMap((s) => s.rows).length).toBeGreaterThanOrEqual(28)
    for (const section of positional) {
      for (const row of section.rows) {
        // Joiner shaping only works on a single letter.
        expect(Array.from(row.char).length, `${section.title}/${row.char}`).toBe(1)
      }
    }
  })

  it('Russian documents the print-vs-italics shape shifts', () => {
    const italics = LETTERS.ru.sections.find((s) => s.italics)
    expect(italics).toBeDefined()
    // The classic traps are all covered.
    const chars = italics!.rows.map((r) => r.char)
    for (const ch of ['т', 'и', 'п', 'д', 'г']) {
      expect(chars, `missing italic note for ${ch}`).toContain(ch)
    }
  })
})

describe('LettersPage', () => {
  beforeEach(() => {
    mockActiveId = 'lang-es'
    mockGetLanguages.mockResolvedValue([
      { id: 'lang-es', code: 'es', name: 'Spanish', rtl: false },
      { id: 'lang-ar', code: 'ar', name: 'Arabic', rtl: true },
      { id: 'lang-ru', code: 'ru', name: 'Russian', rtl: false },
    ])
  })

  function renderPage() {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <LettersPage />
        </MemoryRouter>
      </QueryClientProvider>,
    )
  }

  it('renders the active language sections with example words', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getAllByTestId('letters-section').length).toBeGreaterThan(1)
    })
    expect(screen.getByText('ñ')).toBeDefined()
    expect(screen.getByText(/canyon/)).toBeDefined()
  })

  it('Arabic rows show the four positional shapes with labels', async () => {
    mockActiveId = 'lang-ar'
    renderPage()
    await waitFor(() => {
      expect(screen.getAllByTestId('letter-positions').length).toBeGreaterThan(20)
    })
    const strip = screen.getAllByTestId('letter-positions')[0]
    for (const label of ['alone', 'start', 'middle', 'end']) {
      expect(strip.textContent).toContain(label)
    }
    // Joiner shaping: the start shape is the letter + a zero-width joiner.
    expect(strip.textContent).toContain('‍')
  })

  it('Russian italic-shape rows render an italic twin beside the letter', async () => {
    mockActiveId = 'lang-ru'
    renderPage()
    await waitFor(() => {
      expect(screen.getAllByTestId('italic-twin').length).toBeGreaterThanOrEqual(5)
    })
    const twin = screen.getAllByTestId('italic-twin')[0]
    expect(twin.className).toContain('italic')
  })
})
