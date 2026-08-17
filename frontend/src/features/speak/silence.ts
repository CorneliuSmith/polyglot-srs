/**
 * "They stopped talking" — voice activity detection for hands-free Speak.
 *
 * The owner asked for a conversation that listens the moment the partner
 * finishes and sends when the learner pauses, so nobody has to find a button
 * mid-sentence. That needs one thing the recorder can't tell us: whether the
 * microphone is currently carrying speech or a quiet room.
 *
 * How it decides:
 *
 * - **The gate adapts to the room.** A fixed threshold works in a study and
 *   fails in a café, so the quietest level seen so far is treated as the
 *   noise floor and the gate sits a few times above it, clamped at both ends.
 *   Clamping matters in both directions: without a ceiling, a learner who
 *   starts talking before the first sample would set the "floor" from their
 *   own voice and nothing would ever clear the gate.
 * - **A pause only counts once they've actually said something.** Otherwise
 *   the silence before the first word ends the turn instantly.
 * - **Three ways to stop, and they mean different things.** `silence` is a
 *   finished sentence: transcribe it. `max` is a monologue hitting the cap:
 *   transcribe it, it's real speech. `nothing` is an empty room — the caller
 *   should throw the recording away WITHOUT transcribing, because a
 *   transcription request costs money and an empty one buys nothing.
 *
 * Everything injectable is injected: `AudioContext` doesn't exist in jsdom,
 * so the analyser factory and the clock are parameters and the tests drive a
 * scripted waveform through the same arithmetic the browser runs.
 */

export type AutoStopReason = 'silence' | 'max' | 'nothing'

/** The slice of Web Audio this needs. Narrow on purpose — a fake in a test
 * implements three members instead of the whole API surface. */
export interface AnalyserLike {
  fftSize: number
  getByteTimeDomainData(array: Uint8Array): void
}

export interface AudioProbe {
  analyser: AnalyserLike
  /** Release the context and the source node. */
  close: () => void
}

export interface SilenceOptions {
  /** How long a pause has to last before the turn is treated as finished. */
  silenceMs?: number
  /** Speech has to have been heard for at least this long before any pause
   * counts — a cough shouldn't end a turn. */
  minSpeechMs?: number
  /** Hard ceiling on one turn, so a stuck gate can't hold the microphone
   * open (or run up an unbounded transcription). */
  maxMs?: number
  /** Give up when nothing was ever said. */
  noSpeechMs?: number
  /** How often to sample. */
  intervalMs?: number
  onStop: (reason: AutoStopReason) => void
  /** Test seams. */
  now?: () => number
  probe?: (stream: MediaStream) => AudioProbe | null
  schedule?: (fn: () => void, ms: number) => number
  unschedule?: (handle: number) => void
}

const DEFAULTS = {
  silenceMs: 1500,
  minSpeechMs: 400,
  maxMs: 30_000,
  noSpeechMs: 9_000,
  intervalMs: 100,
}

/** Absolute floor for the gate: below this everything is room noise. */
const MIN_GATE = 0.015
/** …and a ceiling, so an immediately-talking learner can still clear it. */
const MAX_GATE = 0.06

/** Whether this browser can measure the microphone at all. Without it,
 * hands-free sending is not offered — a toggle that silently does nothing is
 * worse than an absent one. */
export function canDetectSilence(): boolean {
  if (typeof window === 'undefined') return false
  const w = window as unknown as { AudioContext?: unknown; webkitAudioContext?: unknown }
  return !!(w.AudioContext || w.webkitAudioContext)
}

function browserProbe(stream: MediaStream): AudioProbe | null {
  const w = window as unknown as {
    AudioContext?: new () => AudioContext
    webkitAudioContext?: new () => AudioContext
  }
  const Ctor = w.AudioContext || w.webkitAudioContext
  if (!Ctor) return null
  const ctx = new Ctor()
  const source = ctx.createMediaStreamSource(stream)
  const analyser = ctx.createAnalyser()
  analyser.fftSize = 512
  source.connect(analyser)
  return {
    // One cast, at the boundary: AnalyserNode's signature is stricter about
    // its buffer's backing store than this module needs to care about.
    analyser: analyser as unknown as AnalyserLike,
    close: () => {
      try {
        source.disconnect()
      } catch {
        // Already torn down with the stream; nothing to undo.
      }
      void ctx.close?.()
    },
  }
}

/** Mean deviation from silence, 0…1. Cheap, and steadier than a peak. */
export function level(samples: Uint8Array): number {
  if (!samples.length) return 0
  let total = 0
  for (const sample of samples) total += Math.abs(sample - 128)
  return total / samples.length / 128
}

/**
 * Watch *stream* and call back once when the turn is over. Returns a cancel
 * function; calling it (or letting the callback fire) releases the audio
 * context. Returns a no-op canceller when this browser can't measure — the
 * caller checks `canDetectSilence()` before offering the feature.
 */
export function watchSilence(
  stream: MediaStream,
  options: SilenceOptions,
): () => void {
  const {
    silenceMs = DEFAULTS.silenceMs,
    minSpeechMs = DEFAULTS.minSpeechMs,
    maxMs = DEFAULTS.maxMs,
    noSpeechMs = DEFAULTS.noSpeechMs,
    intervalMs = DEFAULTS.intervalMs,
    onStop,
    now = () => Date.now(),
    probe = browserProbe,
    schedule = (fn, ms) => setInterval(fn, ms) as unknown as number,
    unschedule = (handle) => clearInterval(handle),
  } = options

  const audio = probe(stream)
  if (!audio) return () => {}

  const samples = new Uint8Array(audio.analyser.fftSize)
  const startedAt = now()
  let lastLoudAt = startedAt
  let speechMs = 0
  let floor = Number.POSITIVE_INFINITY
  let done = false
  let handle: number | null = null

  const finish = (reason: AutoStopReason) => {
    if (done) return
    done = true
    if (handle !== null) unschedule(handle)
    audio.close()
    onStop(reason)
  }

  const tick = () => {
    if (done) return
    audio.analyser.getByteTimeDomainData(samples)
    const current = level(samples)
    floor = Math.min(floor, current)
    const gate = Math.min(MAX_GATE, Math.max(MIN_GATE, floor * 3))
    const at = now()

    if (current > gate) {
      lastLoudAt = at
      speechMs += intervalMs
    }
    if (speechMs >= minSpeechMs && at - lastLoudAt >= silenceMs) {
      finish('silence')
      return
    }
    if (at - startedAt >= maxMs) {
      finish('max')
      return
    }
    if (speechMs < minSpeechMs && at - startedAt >= noSpeechMs) {
      finish('nothing')
    }
  }

  handle = schedule(tick, intervalMs)
  return () => {
    if (done) return
    done = true
    if (handle !== null) unschedule(handle)
    audio.close()
  }
}
