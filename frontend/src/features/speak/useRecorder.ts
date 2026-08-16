import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * One recorded utterance, for Speak (docs/plans/speak.md stage 2).
 *
 * **Tap to start, tap to stop — not hold-to-talk.** The plan sketched
 * push-to-talk, and it is the better metaphor right up until you build it:
 * a pointerup that lands outside the button never fires, so the recorder
 * runs on with the microphone light lit and no way to stop it but
 * navigating away. It is also unreachable by keyboard, which makes the
 * only place in the app that practises production the only place a
 * keyboard user cannot go. A toggle is honest about when it is listening
 * — the button says so — and behaves identically for touch, mouse and
 * keyboard.
 *
 * **The format is the trap.** Chrome and Firefox record WebM/Opus; Safari
 * has no WebM encoder at all and produces MP4/AAC. Passing a mimeType the
 * browser cannot make throws, and passing none leaves Chrome's default,
 * which is fine, and older Safari's, which is not. So the list is probed
 * with isTypeSupported and the first survivor wins — with '' (browser
 * default) as the last resort rather than a crash.
 *
 * **The stream is released every time.** Not stopping the tracks leaves
 * the recording indicator on in the tab and, on mobile, the microphone
 * held against other apps. It is stopped on stop, on error, and on
 * unmount.
 */

const CANDIDATES = [
  'audio/webm;codecs=opus',
  'audio/webm',
  'audio/mp4',
  'audio/ogg;codecs=opus',
]

export function pickMimeType(
  supported: (type: string) => boolean = (t) =>
    typeof MediaRecorder !== 'undefined' &&
    MediaRecorder.isTypeSupported?.(t),
): string {
  for (const type of CANDIDATES) {
    try {
      if (supported(type)) return type
    } catch {
      // isTypeSupported throws on some polyfills rather than returning
      // false. Treat that as "no" and keep looking.
    }
  }
  return ''
}

export interface Recording {
  blob: Blob
  /** How long they actually spoke. The only real measurement behind the
   * summary's "you spoke 61% of the time". */
  ms: number
}

export interface RecorderState {
  /** Whether this browser can record at all. False on anything without
   * MediaRecorder, and on http:// origins where getUserMedia is blocked —
   * in both cases the page shows the typed path and no microphone. */
  supported: boolean
  recording: boolean
  /** Set when permission was refused or the device failed. Cleared on the
   * next attempt, so one denial doesn't poison the rest of the session. */
  error: 'denied' | 'failed' | null
  start: () => Promise<void>
  stop: () => Promise<Recording | null>
  cancel: () => void
}

export function useRecorder(): RecorderState {
  const [recording, setRecording] = useState(false)
  const [error, setError] = useState<'denied' | 'failed' | null>(null)
  const recorder = useRef<MediaRecorder | null>(null)
  const stream = useRef<MediaStream | null>(null)
  const chunks = useRef<Blob[]>([])
  const startedAt = useRef(0)

  const supported =
    typeof navigator !== 'undefined' &&
    !!navigator.mediaDevices?.getUserMedia &&
    typeof MediaRecorder !== 'undefined'

  const release = useCallback(() => {
    stream.current?.getTracks().forEach((track) => track.stop())
    stream.current = null
    recorder.current = null
    chunks.current = []
  }, [])

  useEffect(() => release, [release])

  const start = useCallback(async () => {
    if (!supported || recorder.current) return
    setError(null)
    let media: MediaStream
    try {
      media = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch (err) {
      // NotAllowedError is a refusal (or an insecure origin); anything else
      // is a device that couldn't open. They read differently to a learner,
      // so they are reported differently.
      setError(
        (err as { name?: string })?.name === 'NotAllowedError'
          ? 'denied'
          : 'failed',
      )
      return
    }
    try {
      const mimeType = pickMimeType()
      const rec = new MediaRecorder(media, mimeType ? { mimeType } : undefined)
      chunks.current = []
      rec.ondataavailable = (e) => {
        if (e.data?.size) chunks.current.push(e.data)
      }
      stream.current = media
      recorder.current = rec
      startedAt.current = Date.now()
      rec.start()
      setRecording(true)
    } catch {
      media.getTracks().forEach((track) => track.stop())
      setError('failed')
    }
  }, [supported])

  const stop = useCallback(async () => {
    const rec = recorder.current
    if (!rec) return null
    const ms = Date.now() - startedAt.current
    const blob = await new Promise<Blob>((resolve) => {
      rec.onstop = () =>
        resolve(
          new Blob(chunks.current, {
            // Chunks carry no type of their own; the recorder's is what the
            // server needs to tell the provider what it is holding.
            type: rec.mimeType || 'audio/webm',
          }),
        )
      rec.stop()
    })
    release()
    setRecording(false)
    return blob.size ? { blob, ms } : null
  }, [release])

  const cancel = useCallback(() => {
    // Thrown away without transcribing — they changed their mind. Stop the
    // recorder first so the browser doesn't keep the track alive.
    try {
      recorder.current?.stop()
    } catch {
      // Already stopped; nothing to undo.
    }
    release()
    setRecording(false)
  }, [release])

  return { supported, recording, error, start, stop, cancel }
}
