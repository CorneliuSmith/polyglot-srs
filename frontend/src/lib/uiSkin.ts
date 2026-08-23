/**
 * Which look the app is wearing, applied to <html data-ui="…">.
 *
 * The server decides (see backend/services/experiments.py) and the answer
 * arrives with the profile, which is fetched on every page load. That is
 * one round trip too late to paint with: the app would render Classic and
 * then swap, which is the exact jump the language-loading work went to
 * some trouble to remove. So the resolved skin is persisted into the prefs
 * store and pre-applied by the inline script in index.html before React
 * mounts — the server stays the authority, the cached value only decides
 * the first frame.
 *
 * Everything except the default is expressed as CSS variable overrides
 * under `[data-ui="…"]` in index.css. No component knows which skin it is
 * in, which is what keeps a skin removable: delete the token block and the
 * app is back to Classic with no other edit.
 */

/** The skin that needs no attribute — what the app has always looked like. */
export const DEFAULT_SKIN = 'classic'

const EDITORIAL_FONT_ID = 'ui-skin-editorial-font'

/** The Editorial (A) skin's serif, fetched only when someone is actually
 * wearing it — a CSS @import would make every Classic user pay for a font
 * they never see. Idempotent; left in place on switch-away (it's cached,
 * and removing it would flash anyone toggling back and forth). */
function ensureEditorialFont(): void {
  if (document.getElementById(EDITORIAL_FONT_ID)) return
  const link = document.createElement('link')
  link.id = EDITORIAL_FONT_ID
  link.rel = 'stylesheet'
  link.href =
    'https://fonts.googleapis.com/css2?family=Literata:opsz,wght@7..72,400;7..72,500;7..72,600;7..72,700&display=swap'
  document.head.appendChild(link)
}

export function applyUiSkin(variant: string | null | undefined): void {
  const root = document.documentElement
  if (!variant || variant === DEFAULT_SKIN) {
    root.removeAttribute('data-ui')
    return
  }
  if (variant === 'editorial') ensureEditorialFont()
  root.setAttribute('data-ui', variant)
}

/** What the document is wearing right now, normalized. */
export function currentUiSkin(): string {
  return document.documentElement.getAttribute('data-ui') || DEFAULT_SKIN
}
