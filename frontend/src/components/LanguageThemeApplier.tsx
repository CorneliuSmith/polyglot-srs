import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getLanguages } from '../api/profile'
import { usePrefsStore } from '../stores/prefsStore'
import { applyLanguageTheme } from '../lib/languageColors'

/**
 * Recolors the whole app to the active language's flag palette by writing
 * the `--lang-*` CSS variables (see index.css). Signed out — or until the
 * languages list loads — everything stays on the default indigo.
 */
export default function LanguageThemeApplier() {
  const activeLanguageId = usePrefsStore((s) => s.activeLanguageId)

  const { data: languages } = useQuery({
    queryKey: ['languages'],
    queryFn: getLanguages,
    staleTime: Infinity, // the language list never changes mid-session
    enabled: !!activeLanguageId,
    retry: false,
  })

  const code = languages?.find((l) => l.id === activeLanguageId)?.code

  useEffect(() => {
    applyLanguageTheme(code)
  }, [code])

  return null
}
