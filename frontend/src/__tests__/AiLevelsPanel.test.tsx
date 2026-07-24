import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AiLevelsPanel from '../features/contribute/AiLevelsPanel'

vi.mock('../api/contribute', async (orig) => ({
  ...(await orig<typeof import('../api/contribute')>()),
  getAiLevels: vi.fn(),
  confirmVocabLevel: vi.fn(() => Promise.resolve()),
}))

import { getAiLevels, confirmVocabLevel } from '../api/contribute'
const mockGet = getAiLevels as ReturnType<typeof vi.fn>
const mockConfirm = confirmVocabLevel as ReturnType<typeof vi.fn>

function renderPanel() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  render(
    <QueryClientProvider client={qc}>
      <AiLevelsPanel languageId="lang-sw" />
    </QueryClientProvider>,
  )
}

const WORD = {
  id: 'v1', word: 'kupanga', level: 'B1', part_of_speech: 'verb',
  definition: 'to arrange',
}

describe('AiLevelsPanel', () => {
  beforeEach(() => vi.clearAllMocks())

  it('is hidden when nothing is pending', async () => {
    mockGet.mockResolvedValue({ words: [], can_publish: true })
    renderPanel()
    await waitFor(() => expect(mockGet).toHaveBeenCalled())
    expect(screen.queryByTestId('ai-levels-panel')).toBeNull()
  })

  it('lets a reviewer confirm/adjust a level', async () => {
    mockGet.mockResolvedValue({ words: [WORD], can_publish: true })
    renderPanel()
    await screen.findByTestId('ai-levels-panel')
    fireEvent.change(screen.getByLabelText(/level for kupanga/i), {
      target: { value: 'A2' },
    })
    fireEvent.click(screen.getByRole('button', { name: /confirm/i }))
    await waitFor(() => expect(mockConfirm).toHaveBeenCalledWith('v1', 'A2'))
  })

  it('shows trial reviewers a provisional flag, no confirm', async () => {
    mockGet.mockResolvedValue({ words: [WORD], can_publish: false })
    renderPanel()
    await screen.findByTestId('ai-levels-panel')
    expect(screen.getByText(/provisional B1/i)).toBeDefined()
    expect(screen.queryByRole('button', { name: /confirm/i })).toBeNull()
  })
})
