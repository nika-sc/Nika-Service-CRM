/**
 * Service Worker для PWA (уведомления + кэш статики).
 * HTML-навигация — network-first без кэша документа, иначе при быстрых
 * переходах UI «зависает» на устаревшем ответе из cache-first.
 */

const CACHE_NAME = 'nika-crm-v2-static';
const STATIC_URLS = [
  '/static/themes.css',
  '/static/themes.js',
  '/static/favicon.svg',
];

self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function(cache) {
      return cache.addAll(STATIC_URLS).catch(function() {});
    }).then(function() {
      return self.skipWaiting();
    })
  );
});

self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.map(function(cacheName) {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    }).then(function() {
      return self.clients.claim();
    })
  );
});

function isNavigationRequest(request) {
  if (request.mode === 'navigate') return true;
  const accept = request.headers.get('accept') || '';
  return request.method === 'GET' && accept.indexOf('text/html') !== -1;
}

function isStaticAsset(pathname) {
  return pathname.indexOf('/static/') === 0;
}

self.addEventListener('fetch', function(event) {
  const request = event.request;
  if (request.method !== 'GET') return;

  let url;
  try {
    url = new URL(request.url);
  } catch (e) {
    return;
  }
  if (url.origin !== self.location.origin) return;

  // Документы приложения — только сеть
  if (isNavigationRequest(request)) {
    event.respondWith(
      fetch(request).catch(function() {
        return caches.match(request);
      })
    );
    return;
  }

  // Только /static/* — stale-while-revalidate
  if (!isStaticAsset(url.pathname)) return;

  event.respondWith(
    caches.open(CACHE_NAME).then(function(cache) {
      return cache.match(request).then(function(cached) {
        const network = fetch(request).then(function(response) {
          if (response && response.ok) {
            cache.put(request, response.clone());
          }
          return response;
        }).catch(function() {
          return cached;
        });
        return cached || network;
      });
    })
  );
});

self.addEventListener('push', function(event) {
  const data = event.data ? event.data.json() : {};
  const title = data.title || 'Nika CRM';
  const options = {
    body: data.message || 'Новое уведомление',
    icon: '/static/favicon.svg',
    badge: '/static/favicon.svg',
    tag: data.entity_type || 'notification',
    data: data
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  const data = event.notification.data;
  let url = '/';
  if (data && data.entity_type && data.entity_id) {
    if (data.entity_type === 'order') {
      url = '/order/' + data.entity_id;
    } else if (data.entity_type === 'customer') {
      url = '/clients/' + data.entity_id;
    }
  }
  event.waitUntil(clients.openWindow(url));
});
