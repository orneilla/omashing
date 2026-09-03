/* Omashing — cache hors-ligne. Bump CACHE à chaque déploiement. */
const CACHE = 'omashing-v3';
const SHELL = ['./', './index.html', './manifest.webmanifest',
               './icons/icon-192.png', './icons/icon-512.png', './icons/apple-touch-icon.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE)
    .then(c => Promise.allSettled(SHELL.map(u => c.add(u))))
    .then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  e.respondWith(caches.match(req).then(hit => {
    if (hit) {
      e.waitUntil(fetch(req).then(res => {
        if (res && res.ok) return caches.open(CACHE).then(c => c.put(req, res));
      }).catch(() => {}));
      return hit;
    }
    return fetch(req).then(res => {
      if (res && (res.ok || res.type === 'opaque')) {
        const copy = res.clone();
        e.waitUntil(caches.open(CACHE).then(c => c.put(req, copy)));
      }
      return res;
    }).catch(() => req.mode === 'navigate' ? caches.match('./index.html') : Response.error());
  }));
});
