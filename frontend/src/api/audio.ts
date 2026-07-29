import apiClient from './client'

// One synth per (language, text) per session — after the first play the
// backend serves the same CDN URL forever, so a tiny memo avoids even the
// cache-hit round trip on replays.
const urlCache = new Map<string, string>()
// Only DEFINITIVE noes (404: no voice / unknown text) are remembered.
// Transient failures (rate limit, provider hiccup) must not condemn a
// clip to the browser voice for the whole session.
const misses = new Set<string>()

/** Languages with a neural TTS voice (mirrors the backend VOICES map) —
 * gates listening mode so it never runs on browser-voice languages. */
export const TTS_LANGUAGES = new Set([
  'en', 'es', 'fr', 'de', 'it', 'ca', 'pt', 'ro', 'el', 'ru', 'tr', 'ar', 'sw',
  'hi', 'nl', 'th', 'ko',
])

interface TTSResponse {
  url: string | null
  cached: boolean
  /** Inline clip when the storage cache is unavailable server-side. */
  audio_b64?: string
}

function blobUrlFromBase64(b64: string): string {
  const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0))
  return URL.createObjectURL(new Blob([bytes], { type: 'audio/mpeg' }))
}

/**
 * Resolve a neural-TTS URL for one of OUR sentences/words. The backend
 * returns a CDN URL when its storage cache works, or the clip inline when
 * it doesn't — either way the learner hears the neural voice. Returns null
 * only when there's genuinely no voice for it (callers fall back to
 * browser speechSynthesis).
 */
export async function getTTSUrl(
  languageCode: string,
  text: string,
): Promise<string | null> {
  const key = `${languageCode} ${text}`
  const hit = urlCache.get(key)
  if (hit) return hit
  if (misses.has(key)) return null
  try {
    const response = await apiClient.post<TTSResponse>('/api/audio/tts', {
      language_code: languageCode,
      text,
    })
    const { url, audio_b64 } = response.data
    const playable = url ?? (audio_b64 ? blobUrlFromBase64(audio_b64) : null)
    if (playable) {
      urlCache.set(key, playable)
      return playable
    }
    return null
  } catch (err) {
    const status = (err as { response?: { status?: number } })?.response?.status
    if (status === 404) misses.add(key)
    // 429 is "you are synthesizing too fast", never "this clip is bad" — so
    // it must not be memoized as a miss, and the bulk queue must stop.
    if (status === 429) noteThrottled()
    return null
  }
}

/** The backend rejects anything longer (MAX_TTS_CHARS) — skip rather than
 *  spend a request earning a 422. */
const MAX_TTS_CHARS = 300

function prefetchable(languageCode: string, text: string): boolean {
  if (!text || text.length > MAX_TTS_CHARS) return false
  if (!TTS_LANGUAGES.has(languageCode)) return false
  const key = `${languageCode} ${text}`
  return !urlCache.has(key) && !misses.has(key)
}

/**
 * Warm the TTS cache for a clip we expect the learner to reach for soon, so
 * the first click plays instantly instead of waiting on synthesis. Fire-and-
 * forget: it only resolves (and memoizes) the URL, never plays it — so it's
 * safe to call while the answer is still hidden; nothing is spoken. No-op for
 * languages without a neural voice, or a clip already cached/missed.
 */
export function prefetchTTS(languageCode: string, text: string): void {
  if (!prefetchable(languageCode, text)) return
  void getTTSUrl(languageCode, text)
}

// ── Bulk prefetch ────────────────────────────────────────────────────────
// A page full of speaker buttons (a reading, a grammar point's examples) used
// to leave every one of them cold: the learner pressed play and waited on a
// synth round trip. Warming them on load fixes that, but naively firing one
// request per sentence is worse than the problem — the server rate-limits
// synthesis at 30/min per user, so a long reading would trip it and the
// buttons the learner actually pressed would be the ones that failed.
//
// So: one shared queue, low concurrency, and a hard stop on 429. Cache HITS
// are not rate-limited server-side (the limiter sits after the cache lookup),
// which is why this is cheap for curriculum text everyone shares and only
// costs real quota for a learner's own generated reading.

const PREFETCH_CONCURRENCY = 2
type Job = { key: string; languageCode: string; text: string; cancelled: boolean }
const queue: Job[] = []
let active = 0
/** Set when the server says we're going too fast; the queue drains no
 *  further this session and clicks fall back to synthesizing on demand. */
let throttled = false

function pump(): void {
  while (!throttled && active < PREFETCH_CONCURRENCY && queue.length > 0) {
    const job = queue.shift()!
    if (job.cancelled || !prefetchable(job.languageCode, job.text)) continue
    active += 1
    void getTTSUrl(job.languageCode, job.text)
      .catch(() => undefined)
      .finally(() => {
        active -= 1
        pump()
      })
  }
}

/** Told by getTTSUrl when the server pushes back, so the queue stops instead
 *  of hammering a limiter it has already tripped. */
export function noteThrottled(): void {
  throttled = true
  queue.length = 0
}

/**
 * Warm every clip on a page, cheapest-first and politely.
 *
 * Returns a cancel function — call it on unmount so navigating away stops
 * work for a page nobody is looking at any more. Order matters: pass the
 * texts in the order the learner will meet them, because the queue drains in
 * order and the first sentences are the ones most likely to be played.
 */
export function prefetchTTSMany(
  languageCode: string,
  texts: readonly string[],
): () => void {
  const jobs: Job[] = []
  const seen = new Set<string>()
  for (const text of texts) {
    const key = `${languageCode} ${text}`
    if (seen.has(key) || !prefetchable(languageCode, text)) continue
    seen.add(key)
    const job: Job = { key, languageCode, text, cancelled: false }
    jobs.push(job)
    queue.push(job)
  }
  pump()
  return () => {
    for (const job of jobs) job.cancelled = true
  }
}

/** Test seam. Clears the memo caches as well as the queue: a reset that left
 *  half the module state behind would silently make the NEXT test pass for
 *  the wrong reason. */
export function _resetPrefetchState(): void {
  queue.length = 0
  active = 0
  throttled = false
  urlCache.clear()
  misses.clear()
}
