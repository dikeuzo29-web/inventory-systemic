// static/js/serviceworker.js

// Cache name and version. Increment this whenever you make changes to precached assets.
const CACHE_NAME = 'inventory-app-v3'; // Bumped version from v1
const OFFLINE_URL = '/offline/';

// URLs to precache on install.
const urlsToCache = [
    '/',
    '/api/accounts/login/',
    '/api/accounts/dashboard/',

    // These are your HTML pages that might need caching
    '/api/stock/manage/categories/', // Assuming these are HTML views
    '/api/stock/manage/products/',
    '/api/stock/sales/',
    '/api/stock/restock/',
    '/api/stock/returns/',

    // Critical static assets used across the app (you might need to add more)
    // Make sure these paths are correct, e.g., using collectstatic
    '/static/js/dexie.min.js', // NEW: Dexie.js for IndexedDB
    '/static/js/offline_sync.js', // NEW: Your main offline logic script
    '/static/image/itekton-logo.png',
    '/static/css/main.css', // If you have a main CSS file
    // Add other common CSS/JS if used (e.g., Bootstrap CSS/JS)
];



// INSTALL EVENT – Pre-cache essential assets
self.addEventListener('install', event => {
    console.log('[ServiceWorker] Install');
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('[ServiceWorker] Caching app shell');
                // Ensure all urlsToCache, plus the OFFLINE_URL, are added
                return cache.addAll([...urlsToCache, OFFLINE_URL]);
            })
            .then(() => self.skipWaiting()) // Activates the new SW immediately
            .catch(err => console.error('[ServiceWorker] Install failed:', err))
    );
});

// FETCH EVENT – Advanced caching strategies
self.addEventListener('fetch', event => {
    const requestUrl = new URL(event.request.url);

    // 1. Navigation requests (HTML pages) - Network-first then cache, or offline page
    if (event.request.mode === 'navigate') {
        event.respondWith(
            (async () => {
                try {
                    const networkResponse = await fetch(event.request);
                    // Put a copy of the response in the cache for next time
                    const cache = await caches.open(CACHE_NAME);
                    cache.put(event.request, networkResponse.clone());
                    return networkResponse;
                } catch (error) {
                    // If network fails, try cache, then offline page
                    console.log('[ServiceWorker] Navigation fetch failed, serving offline page or cache:', error);
                    const cachedResponse = await caches.match(event.request); // Try to serve cached version of the page
                    if (cachedResponse) return cachedResponse;
                    return caches.match(OFFLINE_URL); // Fallback to generic offline page
                }
            })()
        );
        return; // Stop further processing for navigation requests
    }

    // 2. API GET requests (e.g., /api/products/, /api/categories/) - Cache-first, falling back to network
    // This is for fetching data that *can* be stale.
    if (requestUrl.pathname.startsWith('/api/') && event.request.method === 'GET') {
        event.respondWith(
            caches.match(event.request).then(cachedResponse => {
                const fetchPromise = fetch(event.request).then(networkResponse => {
                    // Only cache successful API responses
                    if (networkResponse.ok) {
                        caches.open(CACHE_NAME).then(cache => {
                            cache.put(event.request, networkResponse.clone());
                        });
                    }
                    return networkResponse;
                }).catch(error => {
                    console.error('[ServiceWorker] API GET fetch failed:', error);
                    // If network fails, and no cached response, return an empty/error response
                    return new Response(JSON.stringify({ status: 'offline_data_unavailable', message: 'Network offline and no cached data.' }), {
                        headers: { 'Content-Type': 'application/json' },
                        status: 503 // Service Unavailable
                    });
                });
                // Return cached response immediately if available, otherwise fetch from network
                return cachedResponse || fetchPromise;
            })
        );
        return;
    }

    // 3. API POST requests (e.g., /api/sales/, /api/products/ creation) - Network-only.
    // The client-side JS (`offline_logic.js` and form handlers) is responsible for queuing
    // these if offline. The service worker just lets them pass through if online.
    if (requestUrl.pathname.startsWith('/api/') && event.request.method === 'POST') {
        // For POST requests, we primarily go straight to the network.
        // The offline queuing logic is handled in the main app's JS (offline_logic.js).
        event.respondWith(fetch(event.request).catch(error => {
            console.error('[ServiceWorker] API POST failed:', error);
            // If network fails for an online POST, the client-side JS should catch this
            // and then save offline. The service worker here doesn't queue.
            return new Response(JSON.stringify({ status: 'offline_fallback_needed', message: 'Network request failed for POST, client should queue.' }), {
                headers: { 'Content-Type': 'application/json' },
                status: 503 // Service Unavailable
            });
        }));
        return;
    }

    // Default: Cache-first for other static assets (images, other JS/CSS)
    event.respondWith(
        caches.match(event.request).then(response => {
            return response || fetch(event.request).catch(() => {
                // Fallback for non-HTML, non-API requests that fail (e.g., missing images)
                return new Response('<h1>Offline Asset</h1><p>This asset is not available offline.</p>', { headers: { 'Content-Type': 'text/html' }}); // Or a generic image/asset
            });
        })
    );
});

// ACTIVATE EVENT – Clean up old caches
self.addEventListener('activate', event => {
    console.log('[ServiceWorker] Activate');
    event.waitUntil(
        Promise.all([
            clients.claim(), // Take control of existing clients immediately
            caches.keys().then(keys => {
                return Promise.all(
                    keys.map(key => {
                        if (key !== CACHE_NAME) {
                            console.log('[ServiceWorker] Removing old cache:', key);
                            return caches.delete(key);
                        }
                    })
                );
            })
        ])
    );
});