import { describe, it, expect, vi, beforeEach } from 'vitest'

// The remap reads the prefs store; mock the network client and the store.
const post = vi.fn()
vi.mock('../api/client', () => ({ default: { post: (...a: unknown[]) => post(...a) } }))
vi.mock('../stores/prefsStore', () => ({
  usePrefsStore: { getState: vi.fn() },
}))

import { validateAnswer } from '../api/review'
import { usePrefsStore } from '../stores/prefsStore'

const getState = (usePrefsStore as unknown as { getState: ReturnType<typeof vi.fn> })
  .getState

const req = { language_code: 'es', user_input: 'quien', correct_answer: 'quién' }

describe('validateAnswer — accents optional', () => {
  beforeEach(() => vi.clearAllMocks())

  it('promotes correct_sloppy to correct when accents are optional', async () => {
    post.mockResolvedValue({
      data: { answer_result: 'correct_sloppy', feedback: 'Almost — check the accents.' },
    })
    getState.mockReturnValue({ accentsOptional: true })
    const res = await validateAnswer(req)
    expect(res.answer_result).toBe('correct')
    expect(res.feedback).toBeNull()
  })

  it('leaves correct_sloppy alone when accents are required', async () => {
    post.mockResolvedValue({
      data: { answer_result: 'correct_sloppy', feedback: 'Almost — check the accents.' },
    })
    getState.mockReturnValue({ accentsOptional: false })
    const res = await validateAnswer(req)
    expect(res.answer_result).toBe('correct_sloppy')
    expect(res.feedback).toContain('Almost')
  })

  it('never touches a genuinely wrong answer', async () => {
    post.mockResolvedValue({ data: { answer_result: 'wrong', feedback: null } })
    getState.mockReturnValue({ accentsOptional: true })
    const res = await validateAnswer(req)
    expect(res.answer_result).toBe('wrong')
  })
})
