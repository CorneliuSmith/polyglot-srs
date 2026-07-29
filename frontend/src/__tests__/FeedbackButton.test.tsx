import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

vi.mock('../api/feedback', async () => {
  const actual =
    await vi.importActual<typeof import('../api/feedback')>('../api/feedback')
  return { ...actual, sendFeedback: vi.fn() }
})
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn(
    (selector: (s: Record<string, unknown>) => unknown) =>
      selector({ activeLanguageId: 'lang-ar' }),
  ),
}))

import FeedbackButton from '../features/feedback/FeedbackButton'
import { sendFeedback } from '../api/feedback'

const mockSend = sendFeedback as ReturnType<typeof vi.fn>

function renderButton(page = 'dashboard') {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <FeedbackButton page={page} />
    </QueryClientProvider>,
  )
}

const openForm = () => fireEvent.click(screen.getByTestId('feedback-open'))
const type = (text: string) =>
  fireEvent.change(screen.getByLabelText('Your feedback'), {
    target: { value: text },
  })

describe('FeedbackButton', () => {
  beforeEach(() => vi.clearAllMocks())

  it('starts collapsed so it costs the home page one line', () => {
    renderButton()
    expect(screen.getByTestId('feedback-open')).toBeDefined()
    expect(screen.queryByTestId('feedback-form')).toBeNull()
  })

  it('sends the message with the page and language attached', async () => {
    mockSend.mockResolvedValue('fb-1')
    renderButton('reader')
    openForm()
    type('The keyboard is cut off')
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))

    await waitFor(() => expect(mockSend).toHaveBeenCalled())
    expect(mockSend).toHaveBeenCalledWith({
      category: 'bug',
      message: 'The keyboard is cut off',
      languageId: 'lang-ar',
      page: 'reader',
    })
  })

  it('can be sent without choosing a category', async () => {
    // A pre-selected default is the difference between one tap and three.
    mockSend.mockResolvedValue('fb-1')
    renderButton()
    openForm()
    type('Something is off')
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() => expect(mockSend).toHaveBeenCalled())
    expect(mockSend.mock.calls[0][0].category).toBe('bug')
  })

  it('records the category the user picks', async () => {
    mockSend.mockResolvedValue('fb-1')
    renderButton()
    openForm()
    fireEvent.click(screen.getByRole('button', { name: 'I have an idea' }))
    type('Add a map view')
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() => expect(mockSend).toHaveBeenCalled())
    expect(mockSend.mock.calls[0][0].category).toBe('idea')
  })

  it('will not send an empty message', () => {
    renderButton()
    openForm()
    const send = screen.getByRole('button', { name: 'Send' }) as HTMLButtonElement
    expect(send.disabled).toBe(true)
    type('  ')
    expect((screen.getByRole('button', { name: 'Send' }) as HTMLButtonElement).disabled)
      .toBe(true)
  })

  it('confirms it arrived rather than just closing', async () => {
    mockSend.mockResolvedValue('fb-1')
    renderButton()
    openForm()
    type('Thanks for the app')
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() => expect(screen.getByText(/Sent — thank you/)).toBeDefined())
  })

  it('keeps what you wrote when the send fails', async () => {
    mockSend.mockRejectedValue(new Error('offline'))
    renderButton()
    openForm()
    type('Long and carefully written report')
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))

    await waitFor(() => expect(screen.getByText(/didn’t send/)).toBeDefined())
    // Throwing away someone's typing because the network blipped is the
    // fastest way to never hear from them again.
    expect(
      (screen.getByLabelText('Your feedback') as HTMLTextAreaElement).value,
    ).toBe('Long and carefully written report')
  })
})
