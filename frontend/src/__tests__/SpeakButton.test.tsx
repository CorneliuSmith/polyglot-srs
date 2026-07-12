import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import SpeakButton from '../components/SpeakButton'

class FakeUtterance {
  text: string
  lang = ''
  onend: (() => void) | null = null
  onerror: (() => void) | null = null
  constructor(text: string) {
    this.text = text
  }
}

describe('SpeakButton', () => {
  let speak: ReturnType<typeof vi.fn>

  beforeEach(() => {
    speak = vi.fn()
    ;(window as unknown as { speechSynthesis: unknown }).speechSynthesis = {
      speak,
      cancel: vi.fn(),
    }
    ;(globalThis as unknown as { SpeechSynthesisUtterance: unknown }).SpeechSynthesisUtterance =
      FakeUtterance
  })

  afterEach(() => {
    delete (window as unknown as { speechSynthesis?: unknown }).speechSynthesis
  })

  it('speaks the text in the mapped locale when clicked', () => {
    // the utterance is queued a tick after cancel() (Chrome swallows
    // same-tick speak-after-cancel)
    vi.useFakeTimers()
    render(<SpeakButton text="hola" languageCode="es" />)
    fireEvent.click(screen.getByRole('button'))
    vi.runAllTimers()
    expect(speak).toHaveBeenCalledTimes(1)
    const utterance = speak.mock.calls[0][0] as FakeUtterance
    expect(utterance.text).toBe('hola')
    expect(utterance.lang).toBe('es-ES') // es → es-ES
    vi.useRealTimers()
  })

  it('renders nothing when speech is unsupported and no audio file is given', () => {
    delete (window as unknown as { speechSynthesis?: unknown }).speechSynthesis
    const { container } = render(<SpeakButton text="hola" languageCode="es" />)
    expect(container.querySelector('button')).toBeNull()
  })

  it('plays a pre-generated audio file when an audioUrl is provided', () => {
    const play = vi.fn().mockResolvedValue(undefined)
    ;(globalThis as unknown as { Audio: unknown }).Audio = vi.fn(() => ({
      play,
      currentTime: 0,
    }))
    // No speech support, but an audio file is available → still renders.
    delete (window as unknown as { speechSynthesis?: unknown }).speechSynthesis
    render(<SpeakButton text="hola" languageCode="es" audioUrl="https://cdn/x.mp3" />)
    fireEvent.click(screen.getByRole('button'))
    expect(play).toHaveBeenCalled()
    expect(speak).not.toHaveBeenCalled()
  })
})
