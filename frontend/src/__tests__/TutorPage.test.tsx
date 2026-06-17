import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import TutorPage from '../features/tutor/TutorPage'

vi.mock('../api/profile', () => ({
  getLanguages: vi.fn(),
}))

vi.mock('../api/tutor', () => ({
  getTutorStatus: vi.fn(),
  sendTutorMessage: vi.fn(),
  endTutorSession: vi.fn(),
}))

vi.mock('../api/billing', () => ({
  createCheckout: vi.fn(),
}))

vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: vi.fn(() => 'lang-tr'),
}))

import { getLanguages } from '../api/profile'
import { getTutorStatus, sendTutorMessage, endTutorSession } from '../api/tutor'
import { createCheckout } from '../api/billing'

const mockGetLanguages = getLanguages as ReturnType<typeof vi.fn>
const mockGetTutorStatus = getTutorStatus as ReturnType<typeof vi.fn>
const mockSendTutorMessage = sendTutorMessage as ReturnType<typeof vi.fn>
const mockEndTutorSession = endTutorSession as ReturnType<typeof vi.fn>
const mockCreateCheckout = createCheckout as ReturnType<typeof vi.fn>

const turkish = { id: 'lang-tr', code: 'tr', name: 'Turkish', rtl: false }

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/tutor']}>
        <TutorPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('TutorPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetLanguages.mockResolvedValue([turkish])
    mockEndTutorSession.mockResolvedValue(undefined)
  })

  it('shows the welcome message when entitled', async () => {
    mockGetTutorStatus.mockResolvedValue({ available: true, entitled: true })
    renderPage()
    expect(
      await screen.findByText(/I’m your Turkish tutor/i),
    ).toBeDefined()
  })

  it('shows the paywall when not entitled', async () => {
    mockGetTutorStatus.mockResolvedValue({ available: true, entitled: false })
    renderPage()
    expect(await screen.findByText(/paid add-on/i)).toBeDefined()
  })

  it('subscribe redirects to the Stripe Checkout URL', async () => {
    mockGetTutorStatus.mockResolvedValue({ available: true, entitled: false })
    mockCreateCheckout.mockResolvedValue({ granted: false, url: 'https://checkout.stripe/x' })
    const original = window.location
    Object.defineProperty(window, 'location', { value: { href: '' }, writable: true })
    renderPage()

    fireEvent.click(await screen.findByRole('button', { name: /subscribe to the/i }))
    await waitFor(() => {
      expect(mockCreateCheckout).toHaveBeenCalledWith('lang-tr')
      expect(window.location.href).toBe('https://checkout.stripe/x')
    })
    Object.defineProperty(window, 'location', { value: original, writable: true })
  })

  it('shows unavailable state when the tutor is not configured', async () => {
    mockGetTutorStatus.mockResolvedValue({ available: false, entitled: false })
    renderPage()
    expect(await screen.findByText(/isn’t available/i)).toBeDefined()
  })

  it('sends a message and renders the tutor reply', async () => {
    mockGetTutorStatus.mockResolvedValue({ available: true, entitled: true })
    mockSendTutorMessage.mockResolvedValue('Harika! Let’s drill the locative.')
    renderPage()

    const input = await screen.findByPlaceholderText(/message your tutor/i)
    fireEvent.change(input, { target: { value: 'Help me with -de' } })
    fireEvent.keyDown(input, { key: 'Enter' })

    expect(await screen.findByText('Help me with -de')).toBeDefined()
    expect(
      await screen.findByText(/Harika! Let’s drill the locative\./),
    ).toBeDefined()
    expect(mockSendTutorMessage).toHaveBeenCalledWith('lang-tr', 'tr', [
      { role: 'user', content: 'Help me with -de' },
    ])
  })

  it('flushes the session to memory when End session is clicked', async () => {
    mockGetTutorStatus.mockResolvedValue({ available: true, entitled: true })
    mockSendTutorMessage.mockResolvedValue('Harika!')
    renderPage()

    const input = await screen.findByPlaceholderText(/message your tutor/i)
    fireEvent.change(input, { target: { value: 'Help me with -de' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    await screen.findByText(/Harika!/)

    fireEvent.click(screen.getByRole('button', { name: /end session/i }))
    await waitFor(() => {
      expect(mockEndTutorSession).toHaveBeenCalledWith(
        'lang-tr',
        'tr',
        expect.arrayContaining([
          { role: 'user', content: 'Help me with -de' },
          { role: 'assistant', content: 'Harika!' },
        ]),
      )
    })
  })

  it('shows an error banner when sending fails', async () => {
    mockGetTutorStatus.mockResolvedValue({ available: true, entitled: true })
    mockSendTutorMessage.mockRejectedValue(new Error('network'))
    renderPage()

    const input = await screen.findByPlaceholderText(/message your tutor/i)
    fireEvent.change(input, { target: { value: 'hello' } })
    fireEvent.keyDown(input, { key: 'Enter' })

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeDefined()
    })
  })
})
