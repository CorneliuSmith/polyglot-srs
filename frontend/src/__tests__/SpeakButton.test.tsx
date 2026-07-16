import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

vi.mock('../api/audio', () => ({ getTTSUrl: vi.fn(() => Promise.resolve(null)) }))

import SpeakButton from '../components/SpeakButton'
import { getTTSUrl } from '../api/audio'

const mockGetTTSUrl = getTTSUrl as ReturnType<typeof vi.fn>

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

  it('falls back to browser speech when no cached TTS exists', async () => {
    // the utterance is queued a tick after cancel() (Chrome swallows
    // same-tick speak-after-cancel)
    vi.useFakeTimers()
    mockGetTTSUrl.mockResolvedValue(null)
    render(<SpeakButton text="hola" languageCode="es" />)
    fireEvent.click(screen.getByRole('button'))
    await vi.runAllTimersAsync() // flush the TTS lookup + the speech queue
    expect(speak).toHaveBeenCalledTimes(1)
    const utterance = speak.mock.calls[0][0] as FakeUtterance
    expect(utterance.text).toBe('hola')
    expect(utterance.lang).toBe('es-ES') // es → es-ES
    vi.useRealTimers()
  })

  it('prefers the cached neural TTS clip when the backend has one', async () => {
    const play = vi.fn().mockResolvedValue(undefined)
    ;(globalThis as unknown as { Audio: unknown }).Audio = vi.fn(() => ({
      play,
      currentTime: 0,
      src: 'https://cdn/voce.mp3',
    }))
    mockGetTTSUrl.mockResolvedValue('https://cdn/voce.mp3')
    render(<SpeakButton text="você" languageCode="pt" />)
    fireEvent.click(screen.getByRole('button'))
    await waitFor(() => expect(play).toHaveBeenCalledTimes(1))
    expect(mockGetTTSUrl).toHaveBeenCalledWith('pt', 'você')
    expect(speak).not.toHaveBeenCalled() // never the robot when we have real audio
  })

  it('still renders without browser speech — the backend may have a voice', () => {
    delete (window as unknown as { speechSynthesis?: unknown }).speechSynthesis
    render(<SpeakButton text="hola" languageCode="es" />)
    expect(screen.getByRole('button')).toBeDefined()
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
