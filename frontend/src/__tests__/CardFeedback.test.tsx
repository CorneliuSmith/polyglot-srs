import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import CardFeedback from '../features/review/CardFeedback'

vi.mock('../api/review', () => ({ submitCardFeedback: vi.fn() }))

import { submitCardFeedback } from '../api/review'

const mockSubmit = submitCardFeedback as ReturnType<typeof vi.fn>

function renderFeedback() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <CardFeedback cardId="card-1" />
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
      expect(mockSubmit).toHaveBeenCalledWith('card-1', 'The answer should be evde.')
    })
    expect(await screen.findByText(/your feedback was sent/i)).toBeDefined()
  })

  it('disables send until there is a message', () => {
    renderFeedback()
    fireEvent.click(screen.getByRole('button', { name: /report an issue/i }))
    const send = screen.getByRole('button', { name: /send feedback/i }) as HTMLButtonElement
    expect(send.disabled).toBe(true)
  })
})
