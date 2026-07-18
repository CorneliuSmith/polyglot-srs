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
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn(
    (selector: (s: Record<string, unknown>) => unknown) =>
      selector({ activeLanguageId: 'lang-es', qwertyTranslit: {} }),
  ),
}))

import { getLanguages } from '../api/profile'

const mockGetLanguages = getLanguages as ReturnType<typeof vi.fn>

const ALL_CODES = [
  'ar', 'ca', 'de', 'el', 'en', 'es', 'fr', 'ha', 'hi', 'it', 'jam',
  'mi', 'pt', 'ro', 'ru', 'sw', 'tr', 'xh', 'yo',
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
    for (const code of ['ru', 'el', 'ar', 'hi']) {
      const withRoman = LETTERS[code].sections
        .flatMap((s) => s.rows)
        .filter((r) => r.roman)
      expect(withRoman.length, code).toBeGreaterThan(5)
    }
  })
})

describe('LettersPage', () => {
  beforeEach(() => {
    mockGetLanguages.mockResolvedValue([
      { id: 'lang-es', code: 'es', name: 'Spanish', rtl: false },
    ])
  })

  it('renders the active language sections with example words', async () => {
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
    await waitFor(() => {
      expect(screen.getAllByTestId('letters-section').length).toBeGreaterThan(1)
    })
    expect(screen.getByText('ñ')).toBeDefined()
    expect(screen.getByText(/canyon/)).toBeDefined()
  })
})
