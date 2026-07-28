import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Annotatable from '../features/contribute/Annotatable'
import { useReviewModeStore } from '../stores/reviewModeStore'

vi.mock('../api/contribute', async () => {
  const actual = await vi.importActual<
    typeof import('../api/contribute')
  >('../api/contribute')
  return {
    getMyRoles: vi.fn(),
    createChangeRequest: vi.fn(),
    canSuggestForLanguage: actual.canSuggestForLanguage,
  }
})
import { getMyRoles, createChangeRequest } from '../api/contribute'

const mockRoles = getMyRoles as ReturnType<typeof vi.fn>
const mockCreate = createChangeRequest as ReturnType<typeof vi.fn>

const LANG = 'lang-es'
const REVIEWER = { roles: [{ language_id: LANG, role: 'reviewer' }], is_admin: false }

function renderIt(props: Partial<React.ComponentProps<typeof Annotatable>> = {}) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <Annotatable
        languageId={LANG}
        targetType="drill"
        targetId="drill-1"
        targetLabel="El gato come pescado."
        source="learn"
        {...props}
      >
        <p>El gato come pescado.</p>
      </Annotatable>
    </QueryClientProvider>,
  )
}

/** Select a substring of the rendered region's text. */
function selectText(sub: string) {
  const node = screen.getByText('El gato come pescado.').firstChild as Text
  const full = node.textContent ?? ''
  const at = full.indexOf(sub)
  const range = document.createRange()
  range.setStart(node, at)
  range.setEnd(node, at + sub.length)
  const sel = window.getSelection()!
  sel.removeAllRanges()
  sel.addRange(range)
  fireEvent.mouseUp(document)
}

describe('Annotatable (Review Mode)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockRoles.mockResolvedValue(REVIEWER)
    mockCreate.mockResolvedValue({ id: 'req-1' })
    useReviewModeStore.setState({ reviewMode: true })
  })

  it('is inert with Review Mode off — no chrome for a reviewer just studying', async () => {
    useReviewModeStore.setState({ reviewMode: false })
    renderIt()
    expect(screen.queryByTestId('annotatable')).toBeNull()
    expect(screen.queryByRole('button', { name: /flag/i })).toBeNull()
    // Not even a roles request: nothing to decide.
    expect(mockRoles).not.toHaveBeenCalled()
  })

  it('is inert for a learner even with the flag flipped', async () => {
    mockRoles.mockResolvedValue({ roles: [], is_admin: false })
    renderIt()
    await waitFor(() => expect(mockRoles).toHaveBeenCalled())
    expect(screen.queryByTestId('annotatable')).toBeNull()
  })

  it('is inert for a reviewer of a DIFFERENT language', async () => {
    mockRoles.mockResolvedValue({
      roles: [{ language_id: 'lang-tr', role: 'reviewer' }], is_admin: false,
    })
    renderIt()
    await waitFor(() => expect(mockRoles).toHaveBeenCalled())
    expect(screen.queryByTestId('annotatable')).toBeNull()
  })

  it('selecting a span opens the flag popover showing that span', async () => {
    renderIt()
    await screen.findByTestId('annotatable')
    selectText('come pescado')
    const popover = await screen.findByTestId('flag-popover')
    expect(popover.textContent).toContain('come pescado')
  })

  it('one tap on a reason sends the flag with the quote and its offsets', async () => {
    renderIt()
    await screen.findByTestId('annotatable')
    selectText('come pescado')
    await screen.findByTestId('flag-popover')

    fireEvent.click(screen.getByRole('button', { name: 'Unnatural' }))

    await waitFor(() => expect(mockCreate).toHaveBeenCalled())
    const body = mockCreate.mock.calls[0][0]
    expect(body.quote).toBe('come pescado')
    expect(body.issue).toBe('Grammatical but not idiomatic')
    expect(body.target_type).toBe('drill')
    expect(body.target_id).toBe('drill-1')
    expect(body.quote_context.source).toBe('learn')
    // Offsets bracket the quote inside the full region text.
    const { start, end, source_text } = body.quote_context
    expect(source_text.slice(start, end)).toBe('come pescado')
  })

  it('the corner flag needs no selection — the whole region is the quote', async () => {
    renderIt()
    await screen.findByTestId('annotatable')
    fireEvent.click(screen.getByRole('button', { name: /flag this text/i }))
    await screen.findByTestId('flag-popover')
    fireEvent.click(screen.getByRole('button', { name: 'Wrong' }))

    await waitFor(() => expect(mockCreate).toHaveBeenCalled())
    expect(mockCreate.mock.calls[0][0].quote).toBe('El gato come pescado.')
  })

  it('a note and a suggested fix ride along when the reviewer wants to explain', async () => {
    renderIt()
    await screen.findByTestId('annotatable')
    selectText('gato')
    await screen.findByTestId('flag-popover')

    fireEvent.click(screen.getByRole('button', { name: /add a note or a fix/i }))
    fireEvent.change(screen.getByLabelText(/what's wrong/i), {
      target: { value: 'should be feminine here' },
    })
    fireEvent.change(screen.getByLabelText(/suggested fix/i), {
      target: { value: 'La gata come pescado.' },
    })
    fireEvent.click(screen.getByRole('button', { name: /send to review board/i }))

    await waitFor(() => expect(mockCreate).toHaveBeenCalled())
    const body = mockCreate.mock.calls[0][0]
    expect(body.issue).toBe('should be feminine here')
    expect(body.suggestion).toBe('La gata come pescado.')
    expect(body.quote).toBe('gato')
  })

  it('confirms after sending, so a volunteer knows it landed', async () => {
    renderIt()
    await screen.findByTestId('annotatable')
    selectText('gato')
    await screen.findByTestId('flag-popover')
    fireEvent.click(screen.getByRole('button', { name: 'Typo' }))
    expect(await screen.findByText(/sent to the review board/i)).toBeDefined()
  })

  it('a tutor reply flags with no target id — the quote IS the record', async () => {
    renderIt({ targetType: 'tutor_message', targetId: null, source: 'tutor' })
    await screen.findByTestId('annotatable')
    selectText('gato')
    await screen.findByTestId('flag-popover')
    fireEvent.click(screen.getByRole('button', { name: 'Wrong' }))

    await waitFor(() => expect(mockCreate).toHaveBeenCalled())
    const body = mockCreate.mock.calls[0][0]
    expect(body.target_type).toBe('tutor_message')
    expect(body.target_id).toBeNull()
    expect(body.quote).toBe('gato')
  })
})
