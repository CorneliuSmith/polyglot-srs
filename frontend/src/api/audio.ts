import apiClient from './client'

// One synth per (language, text) per session — after the first play the
// backend serves the same CDN URL forever, so a tiny memo avoids even the
// cache-hit round trip on replays.
const urlCache = new Map<string, string>()
const misses = new Set<string>()

/**
 * Resolve a cached neural-TTS URL for one of OUR sentences/words.
 * Returns null when the language has no voice or the text is unknown —
 * callers fall back to browser speechSynthesis.
 */
export async function getTTSUrl(
  languageCode: string,
  text: string,
): Promise<string | null> {
  const key = `${languageCode}\u0000${text}`
  const hit = urlCache.get(key)
  if (hit) return hit
  if (misses.has(key)) return null
  try {
    const response = await apiClient.post<{ url: string }>('/api/audio/tts', {
      language_code: languageCode,
      text,
    })
    urlCache.set(key, response.data.url)
    return response.data.url
  } catch {
    misses.add(key)
    return null
  }
}
