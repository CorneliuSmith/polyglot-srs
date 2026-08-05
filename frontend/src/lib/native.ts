/**
 * Native-shell wiring, for the iOS and Android builds.
 *
 * Everything here is a no-op in a browser: `Capacitor.isNativePlatform()`
 * is false, so the same bundle serves the web app, the PWA and both native
 * shells. Nothing below changes behaviour for a web visitor.
 *
 * These are the things that are WRONG by default in a WebView shell and
 * that a learner notices immediately:
 *   - the hardware Back button on Android closing the app mid-review;
 *   - the status bar rendering dark text on a dark header;
 *   - the splash screen outstaying the first paint.
 */
/** Screens that own the view: Back should leave the SESSION, not the app. */
const SESSION_ROUTES = [
  '/learn',
  '/review',
  '/cram',
  '/gym',
  '/read',
  '/tutor',
]

/**
 * Whether we're inside a Capacitor shell — read from the global the native
 * bridge injects before the app loads, NOT by importing @capacitor/core.
 *
 * Importing core would pull the runtime into the initial bundle for every
 * web visitor: ~11 KB of code whose entire job is to answer this question
 * with "no". The global is absent in a browser, so this is false there
 * without downloading anything to find out.
 */
export function isNative(): boolean {
  const cap = (window as unknown as {
    Capacitor?: { isNativePlatform?: () => boolean }
  }).Capacitor
  return typeof cap?.isNativePlatform === 'function' && cap.isNativePlatform()
}

/**
 * Wire the shell up. Safe to call unconditionally and more than once —
 * it returns immediately on web.
 *
 * *navigate* is the router's navigate, so Back moves through the app
 * rather than through WebView history, which on a hash-free SPA would
 * otherwise walk out of the app from the first screen.
 */
export async function initNative(navigate: (to: string) => void): Promise<void> {
  if (!isNative()) return

  // Imported here, never at the top of the file: a static import would put
  // the whole Capacitor runtime in the initial bundle for every web
  // visitor, where none of it can run.
  const [{ App }, { SplashScreen }, { StatusBar, Style }] = await Promise.all([
    import('@capacitor/app'),
    import('@capacitor/splash-screen'),
    import('@capacitor/status-bar'),
  ])

  // The status bar follows the theme, not the other way round. Reading the
  // class the app already sets avoids a second source of truth.
  const applyStatusBar = async () => {
    const dark = document.documentElement.classList.contains('dark')
    try {
      await StatusBar.setStyle({ style: dark ? Style.Dark : Style.Light })
    } catch {
      // Not fatal, and not worth a console line on every theme flip:
      // some Android versions refuse the call while backgrounded.
    }
  }
  await applyStatusBar()
  new MutationObserver(applyStatusBar).observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['class'],
  })

  // Android hardware Back. Default behaviour closes the app from any
  // screen, which mid-review means losing the session — so Back leaves the
  // session first, then walks up to Study, and only exits from there.
  App.addListener('backButton', ({ canGoBack }) => {
    const path = window.location.pathname
    if (SESSION_ROUTES.some((r) => path === r || path.startsWith(`${r}/`))) {
      navigate('/')
      return
    }
    if (path !== '/') {
      navigate('/')
      return
    }
    if (canGoBack) {
      window.history.back()
      return
    }
    void App.exitApp()
  })

  // Deep links (polyglot://... and https:// universal links) land on the
  // matching route instead of the home screen.
  App.addListener('appUrlOpen', ({ url }) => {
    try {
      const target = new URL(url)
      const to = `${target.pathname}${target.search}`
      if (to && to !== '/') navigate(to)
    } catch {
      // A malformed deep link should open the app, not crash it.
    }
  })

  // The web app paints its own skeletons within a frame or two; holding
  // the splash any longer just hides them.
  try {
    await SplashScreen.hide()
  } catch {
    // Already hidden by launchAutoHide.
  }
}
