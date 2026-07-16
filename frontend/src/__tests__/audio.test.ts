import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('../api/client', () => ({
  default: { post: vi.fn() },
}))

import apiClient from '../api/client'
import { getTTSUrl } from '../api/audio'

const mockPost = apiClient.post as ReturnType<typeof vi.fn>

// Module-level caches persist across tests — every test uses its own text.

describe('getTTSUrl', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    globalThis.URL.createObjectURL = vi.fn(() => 'blob:local-clip')
  })

  it('returns the CDN url and memoizes it', async () => {
    mockPost.mockResolvedValue({
      data: { url: 'https://cdn/tts/sw/a.mp3', cached: true },
    })
    expect(await getTTSUrl('sw', 'Si ya maana.')).toBe('https://cdn/tts/sw/a.mp3')
    expect(await getTTSUrl('sw', 'Si ya maana.')).toBe('https://cdn/tts/sw/a.mp3')
    expect(mockPost).toHaveBeenCalledTimes(1)
  })

  it('plays inline audio when the server cache is unavailable', async () => {
    // Storage down ≠ browser voice: the backend ships the clip inline.
    mockPost.mockResolvedValue({
      data: { url: null, cached: false, audio_b64: btoa('mp3bytes') },
    })
    expect(await getTTSUrl('sw', 'Habari gani?')).toBe('blob:local-clip')
    expect(globalThis.URL.createObjectURL).toHaveBeenCalledTimes(1)
  })

  it('a 404 (no voice / unknown text) is remembered for the session', async () => {
    mockPost.mockRejectedValue({ response: { status: 404 } })
    expect(await getTTSUrl('yo', 'bawo ni')).toBeNull()
    expect(await getTTSUrl('yo', 'bawo ni')).toBeNull()
    expect(mockPost).toHaveBeenCalledTimes(1)
  })

  it('transient failures do NOT blacklist the clip', async () => {
    // Regression: a single 429/502 used to condemn a sentence to the
    // browser voice for the whole session.
    mockPost.mockRejectedValueOnce({ response: { status: 502 } })
    expect(await getTTSUrl('sw', 'Karibu sana.')).toBeNull()
    mockPost.mockResolvedValueOnce({
      data: { url: 'https://cdn/tts/sw/b.mp3', cached: true },
    })
    expect(await getTTSUrl('sw', 'Karibu sana.')).toBe('https://cdn/tts/sw/b.mp3')
    expect(mockPost).toHaveBeenCalledTimes(2)
  })
})
