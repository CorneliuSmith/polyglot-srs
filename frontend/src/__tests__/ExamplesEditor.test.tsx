import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ExamplesEditor from '../features/contribute/ExamplesEditor'

vi.mock('../api/contribute', () => ({
  getVocabExamples: vi.fn(),
  editExampleSentence: vi.fn(() => Promise.resolve()),
  deleteExampleSentence: vi.fn(() => Promise.resolve()),
  acceptExampleTranslation: vi.fn(() => Promise.resolve()),
  dismissExampleTranslation: vi.fn(() => Promise.resolve()),
}))

import {
  getVocabExamples,
  editExampleSentence,
  acceptExampleTranslation,
} from '../api/contribute'
const mockGet = getVocabExamples as ReturnType<typeof vi.fn>
const mockEdit = editExampleSentence as ReturnType<typeof vi.fn>
const mockAccept = acceptExampleTranslation as ReturnType<typeof vi.fn>

function renderEditor() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <ExamplesEditor vocabularyId="v1" languageCode="nl" />
    </QueryClientProvider>,
  )
}

describe('ExamplesEditor', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows the sentences and a pending badge for unreviewed ones', async () => {
    mockGet.mockResolvedValue({ can_publish: true, examples: [
      { id: 'e1', sentence: 'De hond blaft.', translation: 'The dog barks.',
        source: 'human', reviewed: true, is_modified: false },
      { id: 'e2', sentence: 'Een nieuwe zin.', translation: null,
        source: 'ai', reviewed: false, is_modified: false },
    ] })
    renderEditor()
    expect(await screen.findByText('De hond blaft.')).toBeDefined()
    expect(screen.getByText('Een nieuwe zin.')).toBeDefined()
    expect(screen.getByText(/pending review/i)).toBeDefined()
  })

  it('lets a reviewer edit a sentence inline', async () => {
    mockGet.mockResolvedValue({ can_publish: true, examples: [
      { id: 'e1', sentence: 'De hond blaft.', translation: 'The dog barks.',
        source: 'human', reviewed: true, is_modified: false },
    ] })
    renderEditor()
    await screen.findByText('De hond blaft.')
    fireEvent.click(screen.getByRole('button', { name: /edit/i }))
    const box = screen.getByLabelText('Sentence')
    fireEvent.change(box, { target: { value: 'De grote hond blaft.' } })
    fireEvent.click(screen.getByRole('button', { name: /save/i }))
    await waitFor(() =>
      expect(mockEdit).toHaveBeenCalledWith('e1', 'De grote hond blaft.', 'The dog barks.'),
    )
  })

  it('shows an empty message when the word has no examples', async () => {
    mockGet.mockResolvedValue({ can_publish: true, examples: [] })
    renderEditor()
    expect(await screen.findByText(/no example sentences yet/i)).toBeDefined()
  })

  it('surfaces a flagged sentence with its audit reason', async () => {
    mockGet.mockResolvedValue({ can_publish: true, examples: [
      { id: 'e1', sentence: 'Rare zin hier.', translation: null,
        source: 'human', reviewed: true, is_modified: false,
        flagged: true, flag_reason: 'unnatural phrasing' },
    ] })
    renderEditor()
    await screen.findByText('Rare zin hier.')
    expect(screen.getByText(/^flagged$/i)).toBeDefined()
    expect(screen.getByText(/unnatural phrasing/i)).toBeDefined()
  })

  it('shows a suggested translation and lets a reviewer accept it', async () => {
    mockGet.mockResolvedValue({ can_publish: true, examples: [
      { id: 'e1', sentence: 'De hond blaft luid.', translation: 'dog thing',
        source: 'human', reviewed: true, is_modified: false,
        suggested_translation: 'The dog barks loudly.',
        suggestion_reason: 'current translation is vague' },
    ] })
    renderEditor()
    await screen.findByText('De hond blaft luid.')
    expect(screen.getByText(/The dog barks loudly\./)).toBeDefined()
    expect(screen.getByText(/current translation is vague/i)).toBeDefined()
    fireEvent.click(screen.getByRole('button', { name: /^accept$/i }))
    await waitFor(() => expect(mockAccept).toHaveBeenCalledWith('e1'))
  })

  it('hides accept/dismiss from trial reviewers', async () => {
    mockGet.mockResolvedValue({ can_publish: false, examples: [
      { id: 'e1', sentence: 'De hond blaft luid.', translation: 'dog thing',
        source: 'human', reviewed: true, is_modified: false,
        suggested_translation: 'The dog barks loudly.',
        suggestion_reason: 'vague' },
    ] })
    renderEditor()
    await screen.findByText('De hond blaft luid.')
    expect(screen.queryByRole('button', { name: /^accept$/i })).toBeNull()
    expect(screen.getByText(/awaiting a reviewer/i)).toBeDefined()
  })
})
