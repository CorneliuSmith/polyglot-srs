import { useCallback, useEffect, useState } from 'react'
import { hasVoiceFor, speechSupported, toBcp47, voiceFor } from '../lib/speech'

/**
 * Browser speech synthesis for the target language. Free and offline (uses the
 * device's installed voices). Quality and language coverage vary by device, so
 * callers that have a pre-generated audio file should prefer that instead.
 */
export function useSpeech() {
  const supported = speechSupported()
  const [speaking, setSpeaking] = useState(false)

  const cancel = useCallback(() => {
    if (!supported) return
    window.speechSynthesis.cancel()
    setSpeaking(false)
  }, [supported])

  const speak = useCallback(
    (text: string, languageCode: string) => {
      if (!supported || !text) return
      // No installed voice for the language → refuse rather than let the
      // engine "help" with its default voice. A Spanish default reading the
      // Catalan "Els nens juguen al parc." mangles the phonology AND
      // expands the abbreviation "parc." to "parcela" — confidently wrong
      // audio that teaches a learner the wrong sounds. Silence is the
      // lesser harm. (null = the voice list hasn't loaded; let those
      // through, lang-only matching may still find the right voice.)
      if (hasVoiceFor(languageCode) === false) return
      window.speechSynthesis.cancel()
      const utterance = new SpeechSynthesisUtterance(text)
      utterance.lang = toBcp47(languageCode)
      // Setting the voice explicitly is far more reliable than lang-only
      // matching; without a match some engines speak in the UI language or
      // drop the utterance silently.
      const voice = voiceFor(languageCode)
      if (voice) utterance.voice = voice
      utterance.onend = () => setSpeaking(false)
      utterance.onerror = () => setSpeaking(false)
      setSpeaking(true)
      // Chrome swallows an utterance queued in the same tick as cancel().
      window.setTimeout(() => window.speechSynthesis.speak(utterance), 0)
    },
    [supported],
  )

  // Stop any in-flight speech if the component unmounts. Check support
  // freshly rather than trusting a captured flag.
  useEffect(() => () => {
    if (speechSupported()) window.speechSynthesis.cancel()
  }, [])

  return { speak, cancel, speaking, supported }
}
