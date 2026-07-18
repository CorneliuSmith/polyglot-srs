/* PolyglotSRS service worker (WP19b) — deliberately minimal.
 *
 * Strategy chosen so a deploy can never be broken by a stale cache:
 *  - navigations: network-first, falling back to the cached shell offline
 *  - hashed /assets/*: cache-first (immutable by construction)
 *  - everything else (API calls included): straight to the network
 */
const CACHE = 'polyglot-shell-v2';

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(['/'])),
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))),
      )
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || url.origin !== self.location.origin) {
    return; // API writes, cross-origin (Supabase, CDN audio): untouched
  }

  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .then((resp) => {
          // Only cache a good shell — never a 404/500 page, which would then
          // be served offline as a broken fallback.
          if (resp.ok) {
            const copy = resp.clone();
            caches.open(CACHE).then((cache) => cache.put('/', copy));
          }
          return resp;
        })
        .catch(() => caches.match('/')),
    );
    return;
  }

  if (url.pathname.startsWith('/assets/')) {
    event.respondWith(
      caches.match(event.request).then(
        (hit) =>
          hit ||
          fetch(event.request).then((resp) => {
            // A 404 for a hashed asset means a stale shell asked for a bundle
            // that no longer exists — don't poison the cache with it.
            if (resp.ok) {
              const copy = resp.clone();
              caches.open(CACHE).then((cache) => cache.put(event.request, copy));
            }
            return resp;
          }),
      ),
    );
  }
});
