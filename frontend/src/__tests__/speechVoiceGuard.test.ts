/**
 * The wrong-voice guard (owner report, 2026-08-09): the Catalan drill
 * "Els nens juguen al parc." played as "les nens juguen al parcela" —
 * Spanish phonology plus the Spanish abbreviation expansion of "parc.".
 * That's what happens when the neural clip fails (throttle, provider
 * hiccup, missing key) and the browser fallback runs on a device with no
 * Catalan voice: engines fall back to the DEFAULT voice, which reads the
 * text in the wrong language. For a language app, confidently wrong audio
 * is worse than silence — so speak() must refuse when the device
 * demonstrably has no voice for the language.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'

function mockVoices(langs: string[]) {
  const voices = langs.map((lang) => ({ lang, name: `voice-${lang}` }))
  const synth = {
    getVoices: vi.fn(() => voices),
    speak: vi.fn(),
    cancel: vi.fn(),
    addEventListener: vi.fn(),
  }
  Object.defineProperty(window, 'speechSynthesis', {
    value: synth,
    configurable: true,
  })
  ;(globalThis as Record<string, unknown>).SpeechSynthesisUtterance =
    class {
      text: string
      lang = ''
      voice: unknown = null
      onend: (() => void) | null = null
      onerror: (() => void) | null = null
      constructor(text: string) {
        this.text = text
      }
    }
  return synth
}

describe('the wrong-voice guard', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.useFakeTimers()
  })

  it('hasVoiceFor: yes for an installed language, no for a missing one, unknown for an empty list', async () => {
    mockVoices(['es-ES', 'en-US'])
    const { hasVoiceFor } = await import('../lib/speech')
    expect(hasVoiceFor('es')).toBe(true)
    expect(hasVoiceFor('ca')).toBe(false)

    vi.resetModules()
    mockVoices([])
    const fresh = await import('../lib/speech')
    expect(fresh.hasVoiceFor('ca')).toBeNull()
  })

  it('speak() refuses a language the device has no voice for', async () => {
    const synth = mockVoices(['es-ES', 'en-US'])
    const { useSpeech } = await import('../hooks/useSpeech')
    const { result } = renderHook(() => useSpeech())

    act(() => result.current.speak('Els nens juguen al parc.', 'ca'))
    vi.runAllTimers()
    // Neither spoken with the wrong voice nor queued at all.
    expect(synth.speak).not.toHaveBeenCalled()
  })

  it('speak() still speaks a language whose voice IS installed', async () => {
    const synth = mockVoices(['ca-ES', 'es-ES'])
    const { useSpeech } = await import('../hooks/useSpeech')
    const { result } = renderHook(() => useSpeech())

    act(() => result.current.speak('Els nens juguen al parc.', 'ca'))
    act(() => {
      vi.runAllTimers()
    })
    expect(synth.speak).toHaveBeenCalledTimes(1)
    const utterance = synth.speak.mock.calls[0][0] as {
      lang: string
      voice: { lang: string } | null
    }
    expect(utterance.lang).toBe('ca-ES')
    expect(utterance.voice?.lang).toBe('ca-ES')
  })

  it('speak() lets an unpopulated voice list through (lang-only matching may still work)', async () => {
    const synth = mockVoices([])
    const { useSpeech } = await import('../hooks/useSpeech')
    const { result } = renderHook(() => useSpeech())

    act(() => result.current.speak('Els nens juguen al parc.', 'ca'))
    act(() => {
      vi.runAllTimers()
    })
    expect(synth.speak).toHaveBeenCalledTimes(1)
  })
})
