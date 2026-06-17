import { useCallback, useEffect, useState } from 'react'
import { speechSupported, toBcp47 } from '../lib/speech'

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
      window.speechSynthesis.cancel()
      const utterance = new SpeechSynthesisUtterance(text)
      utterance.lang = toBcp47(languageCode)
      utterance.onend = () => setSpeaking(false)
      utterance.onerror = () => setSpeaking(false)
      setSpeaking(true)
      window.speechSynthesis.speak(utterance)
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
