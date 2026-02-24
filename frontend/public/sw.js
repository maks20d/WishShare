const CACHE_VERSION = 'v4';
const STATIC_CACHE = `wishshare-static-${CACHE_VERSION}`;
const IMAGE_CACHE = `wishshare-images-${CACHE_VERSION}`;
const IS_LOCALHOST = self.location.hostname === 'localhost' || self.location.hostname === '127.0.0.1';

const PRECACHE_ASSETS = [
  '/',
  '/manifest.json',
  '/apple-touch-icon.png',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png',
];

if (IS_LOCALHOST) {
  self.addEventListener('install', (event) => {
    event.waitUntil(self.skipWaiting());
  });

  self.addEventListener('activate', (event) => {
    event.waitUntil((async () => {
      const keys = await caches.keys();
      await Promise.all(keys.map((key) => caches.delete(key)));
      await self.registration.unregister();
      const clients = await self.clients.matchAll({ type: 'window' });
      for (const client of clients) {
        client.navigate(client.url);
      }
    })());
  });
} else {
  self.addEventListener('install', (event) => {
    event.waitUntil(
      caches.open(STATIC_CACHE)
        .then((cache) => cache.addAll(PRECACHE_ASSETS))
        .then(() => self.skipWaiting())
    );
  });

  self.addEventListener('activate', (event) => {
    event.waitUntil((async () => {
      const keys = await caches.keys();
      await Promise.all(
        keys
          .filter((key) => key !== STATIC_CACHE && key !== IMAGE_CACHE)
          .map((key) => caches.delete(key))
      );
      await self.clients.claim();
    })());
  });

  async function cacheFirst(request, cacheName) {
    const cached = await caches.match(request);
    if (cached) return cached;

    const response = await fetch(request);
    if (response.ok) {
      const url = new URL(request.url);
      if (url.protocol === 'http:' || url.protocol === 'https:') {
        const cache = await caches.open(cacheName);
        await cache.put(request, response.clone());
      }
    }
    return response;
  }

  async function staleWhileRevalidateImage(request) {
    const cache = await caches.open(IMAGE_CACHE);
    const cached = await cache.match(request);

    const networkPromise = fetch(request)
      .then(async (response) => {
        if (response.ok) {
          const url = new URL(request.url);
          if (url.protocol === 'http:' || url.protocol === 'https:') {
            await cache.put(request, response.clone());
          }
        }
        return response;
      })
      .catch(() => null);

    if (cached) {
      return cached;
    }

    const network = await networkPromise;
    if (network) return network;

    return new Response('', { status: 404, statusText: 'Not Found' });
  }

  async function networkOnlyApi(request) {
    try {
      return await fetch(request);
    } catch {
      return new Response(
        JSON.stringify({ error: 'Offline', message: 'Нет подключения к сети' }),
        {
          status: 503,
          statusText: 'Service Unavailable',
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }
  }

  self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    if (request.method !== 'GET') {
      return;
    }

    if (url.protocol !== 'http:' && url.protocol !== 'https:') {
      return;
    }

    if (url.pathname.startsWith('/api/')) {
      event.respondWith(networkOnlyApi(request));
      return;
    }

    if (url.pathname.startsWith('/_next/')) {
      return;
    }

    if (url.origin !== self.location.origin) {
      return;
    }

    if (request.mode === 'navigate') {
      event.respondWith(
        fetch(request).catch(async () => {
          const cachedHome = await caches.match('/');
          return cachedHome || new Response('Offline', { status: 503 });
        })
      );
      return;
    }

    if (
      request.destination === 'image' ||
      url.pathname.match(/\.(png|jpg|jpeg|gif|webp|svg|ico)$/i)
    ) {
      event.respondWith(staleWhileRevalidateImage(request));
      return;
    }

    if (
      request.destination === 'style' ||
      request.destination === 'script' ||
      request.destination === 'font' ||
      url.pathname.match(/\.(js|css|woff2?|ttf|eot)$/i)
    ) {
      event.respondWith(cacheFirst(request, STATIC_CACHE));
    }
  });

  self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
      self.skipWaiting();
    }

    if (event.data && event.data.type === 'CLEAR_CACHE') {
      event.waitUntil(
        caches.keys().then((cacheNames) => Promise.all(cacheNames.map((name) => caches.delete(name))))
      );
    }
  });
}
