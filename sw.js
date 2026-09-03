/* Omashing — cache hors-ligne.
   La page : réseau d'abord, cache en secours. Tout le contenu de l'app tient
   dans index.html, donc un cache d'abord servirait indéfiniment une vieille
   version tant que le navigateur ne relance pas le service worker.
   Le reste (polices, icônes) : cache d'abord, rafraîchi en arrière-plan. */
const CACHE = 'omashing-v5';
const SHELL = ['./', './index.html', './manifest.webmanifest',
               './icons/icon-192.png', './icons/icon-512.png', './icons/apple-touch-icon.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE)
    // cache: 'reload' court-circuite le cache HTTP du navigateur, qui pourrait
    // resservir l'ancien index.html dans le nouveau cache.
    .then(c => Promise.allSettled(SHELL.map(u => c.add(new Request(u, { cache: 'reload' })))))
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

  if (req.mode === 'navigate') {
    e.respondWith(
      fetch(req).then(res => {
        const copy = res.clone();
        e.waitUntil(caches.open(CACHE).then(c => c.put('./index.html', copy)));
        return res;
      }).catch(() => caches.match('./index.html').then(hit => hit || caches.match('./')))
    );
    return;
  }

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
    }).catch(() => Response.error());
  }));
});
