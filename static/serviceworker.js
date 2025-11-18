// static/js/serviceworker.js
const CACHE_NAME = 'inventory-app-v4'; // Increment version
const OFFLINE_URL = '/offline/';

// ONLY cache static assets - remove all API routes
const urlsToCache = [
    '/',
    '/static/js/dexie.min.js',
    '/static/js/offline_sync.js', 
    '/static/image/itekton-logo.png',
    '/static/css/main.css',
    // Add other actual static files
    '/static/js/app.js',
    '/static/css/bootstrap.min.css', // if using Bootstrap
    '/offline/' // Make sure this route exists in your Django URLs
];

self.addEventListener('install', event => {
    console.log('[ServiceWorker] Install');
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('[ServiceWorker] Caching app shell');
                return cache.addAll(urlsToCache);
            })
            .then(() => self.skipWaiting())
            .catch(err => console.error('[ServiceWorker] Install failed:', err))
    );
});

self.addEventListener('fetch', event => {
    const requestUrl = new URL(event.request.url);
    
    // Skip non-GET requests and browser extensions
    if (event.request.method !== 'GET' || 
        requestUrl.protocol === 'chrome-extension:') {
        return;
    }

    // 1. Static assets - Cache First
    if (requestUrl.pathname.startsWith('/static/')) {
        event.respondWith(
            caches.match(event.request).then(response => {
                return response || fetch(event.request).then(networkResponse => {
                    // Cache new static assets
                    if (networkResponse.ok) {
                        caches.open(CACHE_NAME).then(cache => {
                            cache.put(event.request, networkResponse.clone());
                        });
                    }
                    return networkResponse;
                });
            })
        );
        return;
    }

    // 2. API GET requests - Network First with proper offline fallback
    if (requestUrl.pathname.startsWith('/api/')) {
        event.respondWith(
            fetch(event.request).then(networkResponse => {
                // Cache successful API responses
                if (networkResponse.ok) {
                    caches.open('api-cache').then(cache => {
                        cache.put(event.request, networkResponse.clone());
                    });
                }
                return networkResponse;
            }).catch(async error => {
                // Network failed - try cache
                console.log('[ServiceWorker] API offline, trying cache');
                const cached = await caches.match(event.request);
                if (cached) {
                    return cached;
                }
                // No cache - return offline response
                return new Response(
                    JSON.stringify({ 
                        error: 'offline', 
                        message: 'You are offline and no cached data is available' 
                    }), 
                    { 
                        headers: { 'Content-Type': 'application/json' },
                        status: 503 
                    }
                );
            })
        );
        return;
    }

    // 3. HTML pages - Network First for navigation
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request).then(response => {
                // Cache the main page
                if (response.ok) {
                    caches.open(CACHE_NAME).then(cache => {
                        cache.put(event.request, response.clone());
                    });
                }
                return response;
            }).catch(async error => {
                // Try to serve cached version
                const cached = await caches.match(event.request);
                if (cached) {
                    return cached;
                }
                // Fallback to offline page
                return caches.match(OFFLINE_URL);
            })
        );
        return;
    }

    // 4. Default strategy for everything else
    event.respondWith(
        caches.match(event.request).then(response => {
            return response || fetch(event.request);
        })
    );
});

// ACTIVATE EVENT (keep your existing one)
self.addEventListener('activate', event => {
    console.log('[ServiceWorker] Activate');
    event.waitUntil(
        Promise.all([
            clients.claim(),
            caches.keys().then(keys => {
                return Promise.all(
                    keys.map(key => {
                        if (key !== CACHE_NAME && key !== 'api-cache') {
                            console.log('[ServiceWorker] Removing old cache:', key);
                            return caches.delete(key);
                        }
                    })
                );
            })
        ])
    );
});