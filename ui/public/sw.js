/* PhotoSearch PWA service worker.
 *
 * Scope: offline app shell only.
 *  - API/media traffic is never cached (the backend owns photo bytes and the
 *    serve-time photo policy lives there, not in the browser cache).
 *  - Hashed build assets are cached at runtime; navigations fall back to the
 *    cached shell when the network is unavailable.
 *
 * The shell is mounted under a different base per build target — `/` for the
 * desktop bundle Tauri embeds, `/app/` for the companion bundle FastAPI
 * serves — so every URL is derived from this script's own location.
 */

const CACHE_NAME = 'photosearch-shell-v1';
const BASE = new URL('./', self.location).pathname;
const SHELL_URLS = [BASE, `${BASE}index.html`, `${BASE}manifest.json`];
const ASSET_RE = /\.(?:js|mjs|css|woff2?|ttf|png|jpe?g|webp|gif|svg|ico)$/i;
const NEVER_CACHE_PREFIXES = ['/api', '/search', '/image', '/video', '/file'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => Promise.allSettled(SHELL_URLS.map((url) => cache.add(url))))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (NEVER_CACHE_PREFIXES.some((prefix) => url.pathname.startsWith(prefix))) return;

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() => caches.match(`${BASE}index.html`).then((hit) => hit || Response.error())),
    );
    return;
  }

  if (!ASSET_RE.test(url.pathname)) return;

  event.respondWith(
    caches.match(request).then((hit) => {
      if (hit) return hit;
      return fetch(request).then((response) => {
        if (!response || response.status !== 200 || response.type !== 'basic') return response;
        const copy = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
        return response;
      });
    }),
  );
});
