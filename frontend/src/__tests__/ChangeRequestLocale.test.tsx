import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import SuggestChange from '../features/contribute/SuggestChange'
import Annotatable from '../features/contribute/Annotatable'
import { useReviewModeStore } from '../stores/reviewModeStore'

vi.mock('../api/contribute', async (orig) => {
  const actual = await orig<typeof import('../api/contribute')>()
  return { ...actual, getMyRoles: vi.fn(), createChangeRequest: vi.fn() }
})
import { createChangeRequest, getMyRoles } from '../api/contribute'

const mockRoles = getMyRoles as ReturnType<typeof vi.fn>
const mockCreate = createChangeRequest as ReturnType<typeof vi.fn>

const LANG = 'lang-es'
const REVIEWER = { roles: [{ language_id: LANG, role: 'reviewer' }], is_admin: false }

/**
 * Migration 20261030 gave card_change_requests a locale column, because the
 * board could not tell a complaint about the French hint from one about the
 * sentence. Neither staff form has a locale prop and neither fetches one:
 * both read the profile the app already holds under ['profile'], so these
 * tests seed that cache the way a loaded page would have.
 */
function wrap(ui: React.ReactElement, profile?: Record<string, unknown>) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  if (profile) qc.setQueryData(['profile'], profile)
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

async function sendSuggestion() {
  fireEvent.click(await screen.findByRole('button', { name: /suggest a change/i }))
  fireEvent.change(screen.getByPlaceholderText(/what's wrong/i), {
    target: { value: 'the hint is off' },
  })
  fireEvent.click(screen.getByRole('button', { name: /send to review board/i }))
  await waitFor(() => expect(mockCreate).toHaveBeenCalled())
  return mockCreate.mock.calls[0][0]
}

describe('change requests carry the locale the reviewer was reading', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockRoles.mockResolvedValue(REVIEWER)
    mockCreate.mockResolvedValue({ id: 'cr-1' })
    useReviewModeStore.setState({ reviewMode: true })
  })

  it('SuggestChange sends the explicit support locale', async () => {
    wrap(<SuggestChange languageId={LANG} targetType="drill" targetId="d1" />, {
      support_locale: 'fr',
      ui_language: 'en',
    })
    expect((await sendSuggestion()).locale).toBe('fr')
  })

  it('SuggestChange falls back to the interface language, English spelled out', async () => {
    // 'en', not null: in the column NULL means "not recorded", and a row
    // written before the migration must not read as an English reviewer.
    wrap(<SuggestChange languageId={LANG} targetType="drill" targetId="d1" />, {
      support_locale: null,
      ui_language: 'en',
    })
    expect((await sendSuggestion()).locale).toBe('en')
  })

  it('SuggestChange sends null when no profile is cached — unknown is not English', async () => {
    wrap(<SuggestChange languageId={LANG} targetType="drill" targetId="d1" />)
    expect((await sendSuggestion()).locale).toBeNull()
  })

  it('a Review Mode flag carries the locale too', async () => {
    wrap(
      <Annotatable languageId={LANG} targetType="drill" targetId="d1" targetLabel="El gato" source="learn">
        <p>El gato</p>
      </Annotatable>,
      { support_locale: 'ar', ui_language: 'en' },
    )
    fireEvent.click(await screen.findByRole('button', { name: /flag this text for review/i }))
    fireEvent.click(await screen.findByRole('button', { name: 'Unnatural' }))
    await waitFor(() => expect(mockCreate).toHaveBeenCalled())
    const body = mockCreate.mock.calls[0][0]
    expect(body.locale).toBe('ar')
    expect(body.quote_context.whole).toBe(true)
  })
})
