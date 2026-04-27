/**
 * Service Worker для PWA
 */

const CACHE_NAME = 'nika-crm-v1';
const urlsToCache = [
  '/',
  '/static/themes.css',
  '/static/themes.js',
  '/static/js/notifications.js',
  '/static/js/search.js',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/7.0.0/css/all.min.css',
  'https://cdn.jsdelivr.net/npm/admin-lte@3.2/dist/css/adminlte.min.css'
];

// Установка Service Worker
self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        return cache.addAll(urlsToCache);
      })
  );
});

// Активация Service Worker
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
    })
  );
});

// Перехват запросов
self.addEventListener('fetch', function(event) {
  event.respondWith(
    caches.match(event.request)
      .then(function(response) {
        // Возвращаем из кэша или делаем сетевой запрос
        return response || fetch(event.request);
      })
  );
});

// Обработка push-уведомлений
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
  
  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

// Обработка клика по уведомлению
self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  
  const data = event.notification.data;
  let url = '/';
  
  if (data && data.entity_type && data.entity_id) {
    if (data.entity_type === 'order') {
      url = `/order/${data.entity_id}`;
    } else if (data.entity_type === 'customer') {
      url = `/clients/${data.entity_id}`;
    }
  }
  
  event.waitUntil(
    clients.openWindow(url)
  );
});
