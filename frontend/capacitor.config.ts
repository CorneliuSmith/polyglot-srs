import type { CapacitorConfig } from '@capacitor/cli'

/**
 * The native shells for iOS and Android.
 *
 * Capacitor rather than a rewrite: the app is already a mobile-first PWA
 * with a bottom tab bar, safe-area insets, an on-screen keyboard for
 * non-Latin scripts, and a service worker. A React Native port would
 * reimplement all of it — including 22 letter guides, six UI locales and
 * the whole review session — to arrive at the same screens.
 *
 * The web assets are BUNDLED (webDir), not pointed at the live site. A
 * remote `server.url` is quicker to set up and gets an app rejected under
 * App Store guideline 4.2 for being a website in a shell, and it breaks
 * completely when the learner is offline. Bundled assets ship with the
 * binary and talk to the API over HTTPS like any other client.
 */
const config: CapacitorConfig = {
  // Reverse-DNS, must match the App Store / Play Console registration.
  // Changing it later orphans every installed app, so it is deliberate.
  appId: 'com.polyglotsrs.app',
  appName: 'Polyglot',
  webDir: 'dist',

  ios: {
    // The app draws its own dark/light surfaces; without this the WebView
    // paints white behind them and flashes on rotate and on cold start.
    backgroundColor: '#f9fafb',
    // Long review sessions on cellular: let the WebView keep its cookies
    // so an auth session survives the app being backgrounded.
    limitsNavigationsToAppBoundDomains: true,
  },

  android: {
    backgroundColor: '#f9fafb',
    // Release builds only ever load bundled assets over https://; cleartext
    // stays off so a misconfigured API base can't silently downgrade.
    allowMixedContent: false,
  },

  plugins: {
    SplashScreen: {
      // The web app renders its own skeletons within a frame or two, so a
      // long native splash just delays the thing it is covering for.
      launchShowDuration: 500,
      launchAutoHide: true,
      backgroundColor: '#f9fafb',
      showSpinner: false,
    },
    Keyboard: {
      // The answer input must stay visible when the keyboard opens —
      // resizing the body is what keeps a cloze sentence and its input on
      // screen together on a short phone.
      resize: 'body',
      resizeOnFullScreen: true,
    },
  },
}

export default config
