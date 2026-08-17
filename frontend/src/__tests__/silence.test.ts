import { describe, it, expect, vi } from 'vitest'
import { canDetectSilence, level, watchSilence } from '../features/speak/silence'
import type { AnalyserLike, AudioProbe } from '../features/speak/silence'

/**
 * Voice activity detection for hands-free Speak.
 *
 * jsdom has no AudioContext, so the browser probe, the clock and the timer
 * are all injected and the tests drive a scripted waveform through the same
 * arithmetic the browser runs. What's being pinned is the decision, not the
 * Web Audio API: when does a pause mean "they finished", and when does it
 * mean "nobody is there" — because those two lead to different actions and
 * only one of them should cost a transcription request.
 */

/** A sample buffer at a given loudness, 0…1, as the analyser would fill it. */
function samplesAt(loudness: number, size = 8): Uint8Array {
  const deviation = Math.round(loudness * 128)
  const buffer = new Uint8Array(size)
  buffer.fill(128 + deviation)
  return buffer
}

/**
 * Feeds a scripted sequence of loudness values, one per tick, and runs the
 * clock forward in `intervalMs` steps. The last value repeats forever, so a
 * script can end in silence without spelling out fifty zeroes.
 */
function scripted(script: number[], intervalMs = 100) {
  let tick = 0
  let clock = 0
  const ticks: Array<() => void> = []

  const analyser: AnalyserLike = {
    fftSize: 8,
    getByteTimeDomainData(array) {
      const loudness = script[Math.min(tick, script.length - 1)]
      array.set(samplesAt(loudness, array.length))
      tick += 1
    },
  }
  const probe = (): AudioProbe => ({ analyser, close: closeSpy })
  const closeSpy = vi.fn()

  return {
    probe,
    closeSpy,
    options: {
      intervalMs,
      now: () => clock,
      probe,
      schedule: (fn: () => void) => {
        ticks.push(fn)
        return 1
      },
      unschedule: vi.fn(),
    },
    /** Advance the clock and fire the interval callback n times. */
    run(n: number) {
      for (let i = 0; i < n; i += 1) {
        clock += intervalMs
        ticks.forEach((fn) => fn())
      }
    },
  }
}

const STREAM = {} as MediaStream

describe('level', () => {
  it('reads silence as zero and a full-scale signal as one', () => {
    expect(level(samplesAt(0))).toBe(0)
    expect(level(samplesAt(0.5))).toBeCloseTo(0.5, 2)
    expect(level(new Uint8Array(0))).toBe(0)
  })
})

describe('watchSilence', () => {
  it('stops with "silence" once they have spoken and then paused', () => {
    // Half a second of speech, then quiet. The pause has to outlast
    // silenceMs before the turn is over — not the first quiet sample.
    const onStop = vi.fn()
    const harness = scripted([...Array(5).fill(0.3), 0])
    watchSilence(STREAM, { ...harness.options, onStop, silenceMs: 500 })

    harness.run(5) // speaking
    expect(onStop).not.toHaveBeenCalled()
    harness.run(4) // 400ms of quiet — not yet
    expect(onStop).not.toHaveBeenCalled()
    harness.run(1) // 500ms
    expect(onStop).toHaveBeenCalledWith('silence')
  })

  it('does not treat the silence BEFORE the first word as the end of a turn', () => {
    // The learner takes two seconds to think. Ending the turn there would
    // make hands-free unusable for anyone who pauses to compose a sentence.
    const onStop = vi.fn()
    const harness = scripted([0])
    watchSilence(STREAM, {
      ...harness.options,
      onStop,
      silenceMs: 500,
      minSpeechMs: 400,
      noSpeechMs: 9_000,
    })

    harness.run(20)
    expect(onStop).not.toHaveBeenCalled()
  })

  it('reports "nothing" for an empty room, which must not be transcribed', () => {
    // The caller throws this recording away WITHOUT calling the provider —
    // an empty transcription costs money and buys nothing.
    const onStop = vi.fn()
    const harness = scripted([0])
    watchSilence(STREAM, { ...harness.options, onStop, noSpeechMs: 1_000 })

    harness.run(10)
    expect(onStop).toHaveBeenCalledWith('nothing')
  })

  it('caps a monologue with "max" so the microphone cannot stay open', () => {
    const onStop = vi.fn()
    const harness = scripted([0.3])
    watchSilence(STREAM, {
      ...harness.options,
      onStop,
      maxMs: 800,
      silenceMs: 5_000,
    })

    harness.run(8)
    expect(onStop).toHaveBeenCalledWith('max')
  })

  it('fires once and releases the audio context', () => {
    const onStop = vi.fn()
    const harness = scripted([...Array(5).fill(0.3), 0])
    watchSilence(STREAM, { ...harness.options, onStop, silenceMs: 300 })

    harness.run(40)
    expect(onStop).toHaveBeenCalledTimes(1)
    expect(harness.closeSpy).toHaveBeenCalledTimes(1)
  })

  it('hears a quiet voice in a quiet room', () => {
    // The gate adapts to the noise floor. At a fixed 5% threshold this
    // 3%-amplitude speaker would be inaudible and every turn would end as
    // "nothing" — which is what a fixed threshold does to soft speakers.
    const onStop = vi.fn()
    const harness = scripted([0.002, ...Array(6).fill(0.03), 0.002])
    watchSilence(STREAM, { ...harness.options, onStop, silenceMs: 400 })

    harness.run(7)
    expect(onStop).not.toHaveBeenCalled()
    harness.run(4)
    expect(onStop).toHaveBeenCalledWith('silence')
  })

  it('is not fooled into a runaway gate by someone already talking', () => {
    // If the floor were taken from the first sample unclamped, a learner
    // who starts loud would set gate = 3× their own voice and never clear
    // it. The ceiling on the gate is what keeps this case working.
    const onStop = vi.fn()
    const harness = scripted([...Array(6).fill(0.4), 0])
    watchSilence(STREAM, { ...harness.options, onStop, silenceMs: 300 })

    harness.run(6)
    expect(onStop).not.toHaveBeenCalled()
    harness.run(3)
    expect(onStop).toHaveBeenCalledWith('silence')
  })

  it('cancelling releases the context and prevents any callback', () => {
    const onStop = vi.fn()
    const harness = scripted([...Array(3).fill(0.3), 0])
    const cancel = watchSilence(STREAM, {
      ...harness.options, onStop, silenceMs: 200,
    })

    harness.run(3)
    cancel()
    harness.run(20)
    expect(onStop).not.toHaveBeenCalled()
    expect(harness.closeSpy).toHaveBeenCalledTimes(1)
  })

  it('is inert — never a silent no-op — where audio cannot be measured', () => {
    // No AudioContext (an old browser, or a WebView without it): the cancel
    // function is safe to call and nothing is ever reported, which is why
    // the page checks canDetectSilence() before offering auto-send at all.
    const onStop = vi.fn()
    const cancel = watchSilence(STREAM, { onStop, probe: () => null })
    expect(() => cancel()).not.toThrow()
    expect(onStop).not.toHaveBeenCalled()
  })
})

describe('canDetectSilence', () => {
  it('follows whether the browser has an AudioContext', () => {
    const globals = globalThis as unknown as {
      window?: { AudioContext?: unknown; webkitAudioContext?: unknown }
    }
    const original = globals.window?.AudioContext
    expect(canDetectSilence()).toBe(false) // jsdom has none

    globals.window!.AudioContext = class {}
    expect(canDetectSilence()).toBe(true)

    if (original === undefined) delete globals.window!.AudioContext
    else globals.window!.AudioContext = original
  })
})
