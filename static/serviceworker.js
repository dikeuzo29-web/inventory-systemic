// static/serviceworker.js
const CACHE_NAME = 'inventory-app-v6';
const API_CACHE_NAME = 'api-cache-v1';
const OFFLINE_URL = '/offline/';
const SYNC_QUEUE = 'offline-queue';

// Static assets to cache
const urlsToCache = [
    '/',
    '/static/js/dexie.min.js',
    '/static/js/offline_sync.js', 
    '/static/image/itekton-logo.png',
    '/static/css/main.css',
    '/static/js/app.js',
    '/static/css/bootstrap.min.css',
    '/offline/'
];

// Critical API endpoints to pre-cache
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
            .then(cache => cache.addAll(urlsToCache))
            .then(() => cacheCriticalApiData())
            .then(() => self.skipWaiting())
            .catch(err => console.error('[ServiceWorker] Install failed:', err))
    );
});

async function cacheCriticalApiData() {
    try {
        const apiCache = await caches.open(API_CACHE_NAME);
        await Promise.all(
            criticalApis.map(async (apiUrl) => {
                try {
                    const response = await fetch(apiUrl);
                    if (response.ok) {
                        await apiCache.put(apiUrl, response);
                        console.log(`[ServiceWorker] Pre-cached: ${apiUrl}`);
                    }
                } catch (error) {
                    console.warn(`[ServiceWorker] Failed to pre-cache ${apiUrl}`);
                }
            })
        );
    } catch (error) {
        console.error('[ServiceWorker] API pre-caching failed:', error);
    }
}

self.addEventListener('fetch', event => {
    const requestUrl = new URL(event.request.url);
    
    // Skip browser extensions and non-HTTPs
    if (requestUrl.protocol === 'chrome-extension:') return;

    // 1. Handle API WRITE operations (POST, PUT, DELETE) - Queue for offline
    if (requestUrl.pathname.startsWith('/api/') && 
        ['POST', 'PUT', 'DELETE', 'PATCH'].includes(event.request.method)) {
        
        event.respondWith(
            (async () => {
                try {
                    // Try to send the request online
                    const response = await fetch(event.request);
                    
                    if (response.ok) {
                        console.log(`[ServiceWorker] ${event.request.method} request successful`);
                        
                        // Invalidate related caches since data changed
                        await invalidateRelatedCaches(requestUrl.pathname);
                    }
                    
                    return response;
                } catch (error) {
                    // Network failed - queue for later sync
                    console.log(`[ServiceWorker] Offline ${event.request.method} request, queuing:`, requestUrl.pathname);
                    
                    // Store the request in IndexedDB for later sync
                    await queueOfflineRequest(event.request);
                    
                    // Return success response to user (operation queued)
                    return new Response(
                        JSON.stringify({ 
                            status: 'queued',
                            message: 'Operation queued for sync when online',
                            queued_at: new Date().toISOString()
                        }), 
                        { 
                            headers: { 
                                'Content-Type': 'application/json',
                                'X-Offline-Queued': 'true'
                            },
                            status: 202 // Accepted
                        }
                    );
                }
            })()
        );
        return;
    }

    // 2. API GET requests - Network First
    if (requestUrl.pathname.startsWith('/api/') && event.request.method === 'GET') {
        event.respondWith(
            (async () => {
                try {
                    const networkResponse = await fetch(event.request);
                    
                    if (networkResponse.ok) {
                        const apiCache = await caches.open(API_CACHE_NAME);
                        apiCache.put(event.request, networkResponse.clone());
                    }
                    return networkResponse;
                } catch (error) {
                    console.log('[ServiceWorker] API offline, trying cache');
                    const cachedResponse = await caches.match(event.request);
                    
                    if (cachedResponse) {
                        return cachedResponse;
                    }
                    
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
                }
            })()
        );
        return;
    }

    // 3. Static assets - Cache First
    if (requestUrl.pathname.startsWith('/static/')) {
        event.respondWith(
            caches.match(event.request).then(response => {
                return response || fetch(event.request).then(networkResponse => {
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

    // 4. HTML pages - Network First
    if (event.request.mode === 'navigate') {
        event.respondWith(
            (async () => {
                try {
                    const networkResponse = await fetch(event.request);
                    if (networkResponse.ok) {
                        const cache = await caches.open(CACHE_NAME);
                        cache.put(event.request, networkResponse.clone());
                    }
                    return networkResponse;
                } catch (error) {
                    const cachedResponse = await caches.match(event.request);
                    if (cachedResponse) return cachedResponse;
                    
                    const offlineResponse = await caches.match(OFFLINE_URL);
                    return offlineResponse || new Response('Offline - Please check connection');
                }
            })()
        );
        return;
    }

    // 5. Default strategy
    event.respondWith(
        caches.match(event.request).then(response => {
            return response || fetch(event.request);
        })
    );
});

// Queue offline requests in IndexedDB
async function queueOfflineRequest(request) {
    // This should work with your existing offline_sync.js Dexie setup
    const requestData = {
        url: request.url,
        method: request.method,
        headers: Object.fromEntries(request.headers.entries()),
        body: await request.clone().text(),
        timestamp: new Date().toISOString(),
        id: Date.now() + Math.random()
    };

    // Store in IndexedDB - this assumes you have Dexie setup
    if (typeof window !== 'undefined' && window.offlineDB) {
        await window.offlineDB.offlineRequests.add(requestData);
    } else {
        // Fallback to localStorage if Dexie not available
        const queue = JSON.parse(localStorage.getItem(SYNC_QUEUE) || '[]');
        queue.push(requestData);
        localStorage.setItem(SYNC_QUEUE, JSON.stringify(queue));
    }
    
    console.log(`[ServiceWorker] Queued ${request.method} request to ${request.url}`);
}

// Invalidate caches when data changes
async function invalidateRelatedCaches(apiPath) {
    const apiCache = await caches.open(API_CACHE_NAME);
    const keys = await apiCache.keys();
    
    // Remove cached GET requests that might be affected by this write
    keys.forEach(request => {
        if (request.method === 'GET' && 
            request.url.includes(apiPath.split('/').slice(0, 4).join('/'))) {
            apiCache.delete(request);
            console.log(`[ServiceWorker] Invalidated cache: ${request.url}`);
        }
    });
}

// Background sync for queued requests
self.addEventListener('sync', event => {
    if (event.tag === 'sync-queue') {
        console.log('[ServiceWorker] Background sync triggered');
        event.waitUntil(syncQueuedRequests());
    }
});

// Sync all queued requests when back online
async function syncQueuedRequests() {
    try {
        let queuedRequests = [];
        
        // Get from IndexedDB
        if (typeof window !== 'undefined' && window.offlineDB) {
            queuedRequests = await window.offlineDB.offlineRequests.toArray();
        } else {
            // Get from localStorage
            queuedRequests = JSON.parse(localStorage.getItem(SYNC_QUEUE) || '[]');
        }
        
        console.log(`[ServiceWorker] Syncing ${queuedRequests.length} queued requests`);
        
        for (const requestData of queuedRequests) {
            try {
                const response = await fetch(requestData.url, {
                    method: requestData.method,
                    headers: requestData.headers,
                    body: requestData.body
                });
                
                if (response.ok) {
                    // Remove from queue on success
                    if (typeof window !== 'undefined' && window.offlineDB) {
                        await window.offlineDB.offlineRequests.delete(requestData.id);
                    } else {
                        const queue = JSON.parse(localStorage.getItem(SYNC_QUEUE) || '[]');
                        const newQueue = queue.filter(req => req.id !== requestData.id);
                        localStorage.setItem(SYNC_QUEUE, JSON.stringify(newQueue));
                    }
                    console.log(`[ServiceWorker] Successfully synced: ${requestData.method} ${requestData.url}`);
                }
            } catch (error) {
                console.error(`[ServiceWorker] Failed to sync: ${requestData.method} ${requestData.url}`, error);
            }
        }
    } catch (error) {
        console.error('[ServiceWorker] Sync failed:', error);
    }
}

self.addEventListener('activate', event => {
    event.waitUntil(
        Promise.all([
            clients.claim(),
            caches.keys().then(keys => {
                return Promise.all(
                    keys.map(key => {
                        if (key !== CACHE_NAME && key !== API_CACHE_NAME) {
                            console.log('[ServiceWorker] Removing old cache:', key);
                            return caches.delete(key);
                        }
                    })
                );
            })
        ])
    );
});