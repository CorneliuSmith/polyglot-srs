import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { LETTERS } from '../features/letters/lettersData'
import LettersPage from '../features/letters/LettersPage'

vi.mock('../api/profile', () => ({
  getProfile: vi.fn(),
  getLanguages: vi.fn(),
}))

import { getLanguages, getProfile } from '../api/profile'

const mockGetProfile = getProfile as ReturnType<typeof vi.fn>
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
    vi.clearAllMocks()
    mockGetProfile.mockResolvedValue({ active_language_id: 'lang-es' })
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
