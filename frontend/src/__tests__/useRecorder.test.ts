import { describe, it, expect } from 'vitest'
import { pickMimeType } from '../features/speak/useRecorder'

/**
 * Format selection is the whole cross-browser story for Speak's microphone.
 *
 * Chrome and Firefox record WebM/Opus. Safari has no WebM encoder at all
 * and produces MP4/AAC. Handing MediaRecorder a mimeType the browser
 * cannot produce throws, and the failure is invisible from a dev machine
 * running Chrome — it appears only as "the microphone doesn't work" from
 * one platform's users.
 */
describe('pickMimeType', () => {
  it('prefers Opus in WebM where it exists', () => {
    expect(pickMimeType(() => true)).toBe('audio/webm;codecs=opus')
  })

  it('lands on MP4 on Safari', () => {
    const safari = (t: string) => t === 'audio/mp4'
    expect(pickMimeType(safari)).toBe('audio/mp4')
  })

  it('falls back to the browser default rather than throwing', () => {
    // '' means "you choose" — a recording in some unknown-but-real format
    // beats no recording, and the server reads the type off the blob.
    expect(pickMimeType(() => false)).toBe('')
  })

  it('survives a probe that throws instead of returning false', () => {
    // Some polyfills raise rather than answering. Treat that as "no".
    const throwing = (t: string) => {
      if (t !== 'audio/mp4') throw new Error('nope')
      return true
    }
    expect(pickMimeType(throwing)).toBe('audio/mp4')
  })
})
