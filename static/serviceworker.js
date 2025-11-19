// static/serviceworker.js
const CACHE_NAME = 'inventory-app-v5'; // Incremented version
const API_CACHE_NAME = 'api-cache-v1';
const OFFLINE_URL = '/offline/';

// Static assets to cache
const urlsToCache = [
    '/',
    '/static/js/dexie.min.js',
    '/static/js/offline_sync.js', 
    '/static/image/itekton-logo.png',
    '/static/css/main.css',
    '/static/js/app.js',
    '/static/css/bootstrap.min.css',
    '/offline/' // This will be cached after first visit
];

// Critical API endpoints to pre-cache on install
const criticalApis = [
    '/api/stock/manage/categories/',
    '/api/stock/manage/products/',
    '/api/stock/sales/',
    '/api/stock/restock/',
    '/api/stock/returns/',
    '/api/accounts/dashboard/'
];

self.addEventListener('install', event => {
    console.log('[ServiceWorker] Install');
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('[ServiceWorker] Caching app shell');
                return cache.addAll(urlsToCache);
            })
            .then(() => {
                console.log('[ServiceWorker] Pre-caching critical API data');
                return cacheCriticalApiData();
            })
            .then(() => self.skipWaiting())
            .catch(err => console.error('[ServiceWorker] Install failed:', err))
    );
});

// Function to pre-cache critical API data
async function cacheCriticalApiData() {
    try {
        const apiCache = await caches.open(API_CACHE_NAME);
        const cachePromises = criticalApis.map(async (apiUrl) => {
            try {
                const response = await fetch(apiUrl);
                if (response.ok) {
                    await apiCache.put(apiUrl, response);
                    console.log(`[ServiceWorker] Pre-cached API: ${apiUrl}`);
                }
            } catch (error) {
                console.warn(`[ServiceWorker] Failed to pre-cache ${apiUrl}:`, error);
            }
        });
        await Promise.all(cachePromises);
    } catch (error) {
        console.error('[ServiceWorker] API pre-caching failed:', error);
    }
}

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
                }).catch(error => {
                    console.log('[ServiceWorker] Static asset fetch failed:', error);
                    // Return a fallback for missing static assets
                    if (requestUrl.pathname.match(/\.(css|js)$/)) {
                        return new Response('/* Offline - Resource not available */', {
                            headers: { 'Content-Type': 'text/css' }
                        });
                    }
                    return new Response('Offline - Resource not available');
                });
            })
        );
        return;
    }

    // 2. API GET requests - Network First with proper offline fallback
    if (requestUrl.pathname.startsWith('/api/')) {
        event.respondWith(
            (async () => {
                try {
                    // Try network first
                    const networkResponse = await fetch(event.request);
                    
                    // Cache successful API responses
                    if (networkResponse.ok) {
                        const apiCache = await caches.open(API_CACHE_NAME);
                        apiCache.put(event.request, networkResponse.clone());
                    }
                    return networkResponse;
                } catch (error) {
                    // Network failed - try cache
                    console.log('[ServiceWorker] API offline, trying cache for:', event.request.url);
                    const cachedResponse = await caches.match(event.request);
                    
                    if (cachedResponse) {
                        console.log('[ServiceWorker] Serving cached API response');
                        return cachedResponse;
                    }
                    
                    // No cache available - return structured offline response
                    console.log('[ServiceWorker] No cached API data available');
                    return new Response(
                        JSON.stringify({ 
                            error: 'offline', 
                            message: 'You are offline and no cached data is available',
                            timestamp: new Date().toISOString()
                        }), 
                        { 
                            headers: { 
                                'Content-Type': 'application/json',
                                'X-Offline': 'true'
                            },
                            status: 503 
                        }
                    );
                }
            })()
        );
        return;
    }

    // 3. HTML pages - Network First for navigation
    if (event.request.mode === 'navigate') {
        event.respondWith(
            (async () => {
                try {
                    const networkResponse = await fetch(event.request);
                    
                    // Cache the main page
                    if (networkResponse.ok) {
                        const cache = await caches.open(CACHE_NAME);
                        cache.put(event.request, networkResponse.clone());
                    }
                    return networkResponse;
                } catch (error) {
                    console.log('[ServiceWorker] Navigation failed, trying cache');
                    
                    // Try to serve cached version
                    const cachedResponse = await caches.match(event.request);
                    if (cachedResponse) {
                        return cachedResponse;
                    }
                    
                    // Fallback to offline page
                    const offlineResponse = await caches.match(OFFLINE_URL);
                    if (offlineResponse) {
                        return offlineResponse;
                    }
                    
                    // Ultimate fallback
                    return new Response(
                        '<h1>Offline</h1><p>Please check your internet connection.</p>',
                        { headers: { 'Content-Type': 'text/html' } }
                    );
                }
            })()
        );
        return;
    }

    // 4. Default strategy for everything else
    event.respondWith(
        caches.match(event.request).then(response => {
            return response || fetch(event.request).catch(error => {
                console.log('[ServiceWorker] Fetch failed:', error);
                // Generic offline response for other requests
                return new Response('Offline', {
                    status: 503,
                    statusText: 'Service Unavailable'
                });
            });
        })
    );
});

self.addEventListener('activate', event => {
    console.log('[ServiceWorker] Activate');
    event.waitUntil(
        Promise.all([
            clients.claim(),
            caches.keys().then(keys => {
                return Promise.all(
                    keys.map(key => {
                        // Remove old caches (both app and api caches)
                        if (key !== CACHE_NAME && key !== API_CACHE_NAME) {
                            console.log('[ServiceWorker] Removing old cache:', key);
                            return caches.delete(key);
                        }
                    })
                );
            })
        ]).then(() => {
            console.log('[ServiceWorker] Ready to handle fetches!');
        })
    );
});

// Background sync for queued requests when coming back online
self.addEventListener('sync', event => {
    if (event.tag === 'background-sync') {
        console.log('[ServiceWorker] Background sync triggered');
        event.waitUntil(doBackgroundSync());
    }
});

async function doBackgroundSync() {
    // This would sync any queued operations from IndexedDB
    console.log('[ServiceWorker] Performing background sync');
    // Implementation depends on your offline_sync.js logic
}