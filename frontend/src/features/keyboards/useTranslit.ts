import { usePrefsStore } from '../../stores/prefsStore'
import { hasTranslit } from './translit'

/** QWERTY-transliteration preference for one language (default: on). */
export function useTranslit(languageCode: string) {
  const prefs = usePrefsStore((s) => s.qwertyTranslit)
  const setPref = usePrefsStore((s) => s.setQwertyTranslit)
  const supported = hasTranslit(languageCode)
  const enabled = supported && (prefs[languageCode] ?? true)
  return {
    supported,
    enabled,
    toggle: () => setPref(languageCode, !enabled),
  }
}
