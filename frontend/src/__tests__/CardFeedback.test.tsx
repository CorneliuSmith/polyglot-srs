import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import CardFeedback from '../features/review/CardFeedback'

vi.mock('../api/review', () => ({ submitCardFeedback: vi.fn() }))

import { submitCardFeedback } from '../api/review'

const mockSubmit = submitCardFeedback as ReturnType<typeof vi.fn>

function renderFeedback(props: Partial<React.ComponentProps<typeof CardFeedback>> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <CardFeedback cardId="card-1" {...props} />
    </QueryClientProvider>,
  )
}

describe('CardFeedback', () => {
  beforeEach(() => vi.clearAllMocks())

  it('opens, submits, and thanks the learner', async () => {
    mockSubmit.mockResolvedValue(undefined)
    renderFeedback()

    fireEvent.click(screen.getByRole('button', { name: /report an issue/i }))
    fireEvent.change(screen.getByPlaceholderText(/what looks wrong/i), {
      target: { value: 'The answer should be evde.' },
    })
    fireEvent.click(screen.getByRole('button', { name: /send feedback/i }))

    await waitFor(() => {
      // No chip chosen and nothing known about the session: every label
      // null, and the message still goes — the chips are a courtesy.
      expect(mockSubmit).toHaveBeenCalledWith('card-1', 'The answer should be evde.', {
        field: null,
        drill_id: null,
        locale: null,
      })
    })
    expect(await screen.findByText(/your feedback was sent/i)).toBeDefined()
  })

  it('disables send until there is a message', () => {
    renderFeedback()
    fireEvent.click(screen.getByRole('button', { name: /report an issue/i }))
    const send = screen.getByRole('button', { name: /send feedback/i }) as HTMLButtonElement
    expect(send.disabled).toBe(true)
  })

  it('offers six field chips with none selected', () => {
    renderFeedback()
    fireEvent.click(screen.getByRole('button', { name: /report an issue/i }))
    // Only the chips carry aria-pressed; Send and Cancel do not match.
    const chips = screen.getAllByRole('button', { pressed: false })
    expect(chips.map((c) => c.textContent)).toEqual([
      'Sentence',
      'Hint',
      'Translation',
      'Definition',
      'Explanation',
      'Other',
    ])
    expect(screen.queryByRole('button', { pressed: true })).toBeNull()
  })

  it('sends the chosen field with the locale and drill the session knows', async () => {
    mockSubmit.mockResolvedValue(undefined)
    renderFeedback({ locale: 'fr', drillId: 'drill-9' })
    fireEvent.click(screen.getByRole('button', { name: /report an issue/i }))
    fireEvent.click(screen.getByRole('button', { name: 'Hint' }))
    expect(screen.getByRole('button', { name: 'Hint' }).getAttribute('aria-pressed')).toBe('true')
    fireEvent.change(screen.getByPlaceholderText(/what looks wrong/i), {
      target: { value: 'The hint gives the answer away.' },
    })
    fireEvent.click(screen.getByRole('button', { name: /send feedback/i }))

    await waitFor(() => {
      expect(mockSubmit).toHaveBeenCalledWith('card-1', 'The hint gives the answer away.', {
        field: 'hint',
        drill_id: 'drill-9',
        locale: 'fr',
      })
    })
  })

  it('a second tap on a chip clears it — none is a valid answer', () => {
    renderFeedback()
    fireEvent.click(screen.getByRole('button', { name: /report an issue/i }))
    const hint = screen.getByRole('button', { name: 'Hint' })
    fireEvent.click(hint)
    fireEvent.click(hint)
    expect(hint.getAttribute('aria-pressed')).toBe('false')
    expect(screen.queryByRole('button', { pressed: true })).toBeNull()
  })
})
