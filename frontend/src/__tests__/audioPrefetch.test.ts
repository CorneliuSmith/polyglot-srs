import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

vi.mock('../api/client', () => ({
  default: { post: vi.fn() },
}))

import apiClient from '../api/client'
import { prefetchTTSMany, getTTSUrl, _resetPrefetchState } from '../api/audio'

const post = apiClient.post as ReturnType<typeof vi.fn>

/** Let the prefetch queue drain. */
const settle = () => new Promise((r) => setTimeout(r, 0))

const ok = (url: string) => Promise.resolve({ data: { url, cached: true } })

describe('bulk TTS prefetch', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    _resetPrefetchState()
  })
  afterEach(() => _resetPrefetchState())

  it('warms every clip on the page', async () => {
    post.mockImplementation(() => ok('https://cdn/x.mp3'))
    prefetchTTSMany('es', ['uno', 'dos', 'tres'])
    await settle()
    await settle()
    expect(post).toHaveBeenCalledTimes(3)
  })

  it('never exceeds the concurrency cap', async () => {
    // 30 synths/min server-side: a long reading fired all at once would trip
    // the limiter, and the clip the learner actually pressed would be the
    // one that failed.
    let inFlight = 0
    let peak = 0
    post.mockImplementation(
      () =>
        new Promise((resolve) => {
          inFlight += 1
          peak = Math.max(peak, inFlight)
          setTimeout(() => {
            inFlight -= 1
            resolve({ data: { url: 'https://cdn/x.mp3', cached: true } })
          }, 5)
        }),
    )
    prefetchTTSMany('es', ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'])
    await new Promise((r) => setTimeout(r, 120))
    expect(peak).toBeLessThanOrEqual(2)
    expect(post).toHaveBeenCalledTimes(8)
  })

  it('drains in order, so the sentences read first are ready first', async () => {
    const seen: string[] = []
    post.mockImplementation((_url: string, body: { text: string }) => {
      seen.push(body.text)
      return ok('https://cdn/x.mp3')
    })
    prefetchTTSMany('es', ['first', 'second', 'third'])
    await settle()
    await settle()
    expect(seen[0]).toBe('first')
  })

  it('stops the whole queue when the server says slow down', async () => {
    // 429 means "you are synthesizing too fast" — continuing would just
    // deepen the hole and starve the clips the learner clicks.
    post.mockImplementation(() =>
      Promise.reject({ response: { status: 429 } }),
    )
    prefetchTTSMany('es', ['a', 'b', 'c', 'd', 'e', 'f'])
    await new Promise((r) => setTimeout(r, 50))
    expect(post.mock.calls.length).toBeLessThan(6)
  })

  it('a 429 is not remembered as a dead clip — the click still retries', async () => {
    post.mockImplementationOnce(() => Promise.reject({ response: { status: 429 } }))
    expect(await getTTSUrl('es', 'hola')).toBeNull()
    post.mockImplementationOnce(() => ok('https://cdn/hola.mp3'))
    expect(await getTTSUrl('es', 'hola')).toBe('https://cdn/hola.mp3')
  })

  it('a 404 IS remembered — no point asking twice for a clip that does not exist', async () => {
    post.mockImplementationOnce(() => Promise.reject({ response: { status: 404 } }))
    expect(await getTTSUrl('es', 'nope')).toBeNull()
    post.mockClear()
    expect(await getTTSUrl('es', 'nope')).toBeNull()
    expect(post).not.toHaveBeenCalled()
  })

  it('skips languages with no neural voice', async () => {
    // yo/ha/xh/mi fall back to browser synthesis; a request would 404.
    prefetchTTSMany('yo', ['bawo', 'ni'])
    await settle()
    expect(post).not.toHaveBeenCalled()
  })

  it('skips text the server would reject as too long', async () => {
    post.mockImplementation(() => ok('https://cdn/x.mp3'))
    prefetchTTSMany('es', ['x'.repeat(301), 'corto'])
    await settle()
    await settle()
    expect(post).toHaveBeenCalledTimes(1)
    expect(post.mock.calls[0][1].text).toBe('corto')
  })

  it('de-duplicates repeated text within one page', async () => {
    post.mockImplementation(() => ok('https://cdn/x.mp3'))
    prefetchTTSMany('es', ['hola', 'hola', 'hola'])
    await settle()
    await settle()
    expect(post).toHaveBeenCalledTimes(1)
  })

  it('cancelling stops work for a page nobody is looking at', async () => {
    post.mockImplementation(
      () =>
        new Promise((resolve) =>
          setTimeout(() => resolve({ data: { url: 'u', cached: true } }), 5),
        ),
    )
    const cancel = prefetchTTSMany('es', ['a', 'b', 'c', 'd', 'e', 'f'])
    cancel()
    await new Promise((r) => setTimeout(r, 60))
    // The two already in flight finish; the rest are dropped.
    expect(post.mock.calls.length).toBeLessThanOrEqual(2)
  })

  it('never re-requests a clip already resolved', async () => {
    post.mockImplementation(() => ok('https://cdn/hola.mp3'))
    prefetchTTSMany('es', ['hola'])
    await settle()
    await settle()
    post.mockClear()
    prefetchTTSMany('es', ['hola'])
    await settle()
    expect(post).not.toHaveBeenCalled()
  })
})
