import { useEffect } from 'react'
import { usePrefsStore } from '../stores/prefsStore'

/**
 * Applies the theme preference (WP13h) by toggling `.dark` on <html>.
 * The dark palette itself lives in index.css — it remaps the gray ramp
 * (and card surfaces), so no component needs dark: variants.
 * In 'system' mode it tracks the OS preference live.
 */
export default function ThemeApplier() {
  const theme = usePrefsStore((s) => s.theme)

  useEffect(() => {
    const media = window.matchMedia?.('(prefers-color-scheme: dark)')
    const apply = () => {
      const dark = theme === 'dark' || (theme === 'system' && !!media?.matches)
      document.documentElement.classList.toggle('dark', dark)
    }
    apply()
    if (theme === 'system' && media?.addEventListener) {
      media.addEventListener('change', apply)
      return () => media.removeEventListener('change', apply)
    }
  }, [theme])

  return null
}
