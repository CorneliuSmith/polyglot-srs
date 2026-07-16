import { useRef, useState } from 'react'
import { getTTSUrl } from '../api/audio'
import { useSpeech } from '../hooks/useSpeech'

interface SpeakButtonProps {
  text: string
  languageCode: string
  /**
   * Optional pre-generated audio file. When present it's played instead of
   * browser speech synthesis — the seam for higher-quality cached TTS later.
   */
  audioUrl?: string | null
  label?: string
  className?: string
}

/**
 * A small speaker button that plays a pronunciation. Prefers a cached audio
 * file when given, otherwise falls back to the browser's speech synthesis.
 * Renders nothing when neither is available (e.g. a browser/device with no
 * voice for the language).
 */
export default function SpeakButton({
  text,
  languageCode,
  audioUrl,
  label,
  className,
}: SpeakButtonProps) {
  const { speak, speaking, supported } = useSpeech()
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [playing, setPlaying] = useState(false)

  const playUrl = (url: string) => {
    const el =
      audioRef.current && audioRef.current.src === url
        ? audioRef.current
        : new Audio(url)
    audioRef.current = el
    el.currentTime = 0
    setPlaying(true)
    el.onended = () => setPlaying(false)
    void el.play().catch(() => setPlaying(false))
  }

  const handlePlay = async () => {
    if (playing) return
    // Priority: explicit pre-generated file > cached neural TTS from the
    // backend > the browser's speech synthesis (the old, awful default —
    // now only the fallback for languages without a neural voice).
    if (audioUrl) {
      playUrl(audioUrl)
      return
    }
    setPlaying(true) // optimistic: shows activity while the URL resolves
    const url = await getTTSUrl(languageCode, text)
    if (url) {
      playUrl(url)
    } else {
      setPlaying(false)
      if (supported) speak(text, languageCode)
    }
  }

  const active = playing || speaking

  return (
    <button
      type="button"
      onClick={handlePlay}
      aria-label={label ?? 'Play pronunciation'}
      className={
        className ??
        `inline-flex items-center justify-center rounded p-1 hover:text-lang ${
          active ? 'text-lang' : 'text-gray-400'
        }`
      }
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path
          d="M11 5 6 9H3v6h3l5 4V5z"
          fill="currentColor"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
        <path
          d="M15.5 8.5a5 5 0 0 1 0 7M18 6a8 8 0 0 1 0 12"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          fill="none"
        />
      </svg>
    </button>
  )
}
