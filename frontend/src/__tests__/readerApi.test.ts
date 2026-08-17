import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

const { get, post } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }))
vi.mock('../api/client', () => ({ default: { get, post } }))

import { generateReading } from '../api/reader'

/**
 * The Reader's write is asynchronous now. A graded, once-rewritten C2 text
 * is two full generations, and holding one request open through that is
 * what DigitalOcean's gateway killed at about a minute — the owner's
 * "Couldn't write that one" on Theoretical Physics at C2. The POST starts
 * the write and this polls for the result.
 */
describe('generateReading — start, then poll', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
    post.mockResolvedValue({ data: { generating: true } })
  })
  afterEach(() => vi.useRealTimers())

  /** Let the poll loop run without waiting on real time. */
  async function drain(promise: Promise<unknown>) {
    for (let i = 0; i < 12; i++) {
      await vi.advanceTimersByTimeAsync(3000)
    }
    return promise
  }

  /** Rejection cases attach the expectation BEFORE the clock moves —
   * otherwise the promise rejects with nobody listening and vitest
   * (rightly) reports an unhandled rejection. */
  async function drainRejecting(promise: Promise<unknown>, message: string) {
    const settled = expect(promise).rejects.toThrow(message)
    for (let i = 0; i < 12; i++) {
      await vi.advanceTimersByTimeAsync(3000)
    }
    await settled
  }

  it('starts the write and keeps asking until the text lands', async () => {
    const reading = { title: 'Física', sentences: [], new_words: [], structures: [] }
    get
      .mockResolvedValueOnce({ data: { generating: true } })
      .mockResolvedValueOnce({ data: { generating: true } })
      .mockResolvedValueOnce({
        data: {
          generating: false,
          id: 'r-1',
          reading,
          level: 'C2',
          allowance: { unlimited: true },
        },
      })

    const promise = generateReading('lang-en', 'en', 'theoretical physics', {
      complexity: 'C2',
    })
    const result = await drain(promise)

    // The POST carries the options and returns immediately…
    expect(post).toHaveBeenCalledWith('/api/reader/generate', {
      language_id: 'lang-en',
      language_code: 'en',
      topic: 'theoretical physics',
      complexity: 'C2',
    })
    // …and the answer arrived over the status endpoint.
    expect(get).toHaveBeenCalledWith('/api/reader/generate/status')
    expect(get).toHaveBeenCalledTimes(3)
    expect(result).toMatchObject({ id: 'r-1', level: 'C2' })
  })

  it('surfaces the server’s reason rather than a shrug', async () => {
    get.mockResolvedValue({
      data: { generating: false, error: 'Ran past the token limit' },
    })
    await drainRejecting(
      generateReading('lang-en', 'en', 'physics'),
      'Ran past the token limit',
    )
  })

  it('gives up when the write vanishes (a restart mid-generation)', async () => {
    get.mockResolvedValue({ data: { generating: false } })
    await drainRejecting(
      generateReading('lang-en', 'en', 'physics'),
      'stopped being written',
    )
  })
})
