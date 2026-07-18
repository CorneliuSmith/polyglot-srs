import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { initSentry } from './lib/sentry'

initSentry()

// PWA (WP19b): register the minimal shell service worker — production
// only, so dev/HMR never fights a cache.
if (import.meta.env.PROD && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {
      // Installability is progressive enhancement — never block the app.
    })
  })
}

// A dynamic-import chunk that 404s means this tab is running against a bundle
// that a deploy has since replaced. Reload once (guarded) to pick up the new
// index and its fresh asset hashes.
window.addEventListener('vite:preloadError', () => {
  if (!sessionStorage.getItem('polyglot-chunk-reloaded')) {
    sessionStorage.setItem('polyglot-chunk-reloaded', '1')
    window.location.reload()
  }
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
