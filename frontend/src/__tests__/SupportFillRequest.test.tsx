import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import SupportFillRequest from '../features/settings/SupportFillRequest'

vi.mock('../api/profile', () => ({
  getTranslationRequest: vi.fn(),
  requestTranslation: vi.fn(),
}))
import { getTranslationRequest, requestTranslation } from '../api/profile'
const mockState = getTranslationRequest as ReturnType<typeof vi.fn>
const mockAsk = requestTranslation as ReturnType<typeof vi.fn>

const OFF = {
  available: true,
  locale: 'es',
  locale_name: 'Spanish',
  auto_translate_enabled: false,
  can_ask: true,
  request: null,
}

function renderAsk() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <SupportFillRequest languageId="lang-nl" />
    </QueryClientProvider>,
  )
}

describe('SupportFillRequest', () => {
  beforeEach(() => vi.clearAllMocks())

  it('offers the ask on a course whose backlog is not draining, and says what already happens', async () => {
    mockState.mockResolvedValue(OFF)
    renderAsk()
    expect(await screen.findByTestId('support-fill-ask')).toBeInTheDocument()
    expect(screen.getByTestId('support-fill-button').textContent).toContain('Spanish')
    // The honest half: what they study is translated either way.
    expect(screen.getByText(/translated when you get to it/i)).toBeInTheDocument()
  })

  it('sends the note and shows the asked state without a refetch', async () => {
    mockState.mockResolvedValue(OFF)
    mockAsk.mockResolvedValue({
      ...OFF,
      can_ask: false,
      request: { status: 'open', requested_at: '2026-09-17T00:00:00Z', decided_at: null },
      result: 'created',
    })
    renderAsk()
    fireEvent.change(await screen.findByTestId('support-fill-note'), {
      target: { value: 'most of my cards are English' },
    })
    fireEvent.click(screen.getByTestId('support-fill-button'))
    await waitFor(() =>
      expect(mockAsk).toHaveBeenCalledWith('lang-nl', 'most of my cards are English'),
    )
    expect(await screen.findByTestId('support-fill-asked')).toHaveTextContent(/asked for Spanish/i)
  })

  it('says so once the course is being filled', async () => {
    mockState.mockResolvedValue({
      ...OFF,
      can_ask: false,
      request: { status: 'fulfilled', requested_at: '2026-09-01T00:00:00Z', decided_at: '2026-09-17T00:00:00Z' },
    })
    renderAsk()
    expect(await screen.findByTestId('support-fill-asked')).toHaveTextContent(/being filled in/i)
  })

  it('renders nothing when there is nothing to offer', async () => {
    // English help, a course already draining, and a pre-migration server.
    for (const state of [
      { ...OFF, locale: null, locale_name: null, can_ask: false },
      { ...OFF, auto_translate_enabled: true, can_ask: false },
      { ...OFF, available: false, can_ask: false },
    ]) {
      mockState.mockResolvedValue(state)
      const { container, unmount } = renderAsk()
      await waitFor(() => expect(mockState).toHaveBeenCalled())
      expect(container.querySelector('[data-testid^="support-fill"]')).toBeNull()
      unmount()
      vi.clearAllMocks()
    }
  })
})
