// serviceworker.js — CLEAN VERSION (No Write Queueing)
const CACHE_NAME = 'inventory-app-v8';
const STATIC_ASSETS = [
    "/",
    "/offline/",
    "/static/css/styles.css",
    "/static/js/offline_sync.js",
    "/static/js/dexie.min.js",
    "/static/images/logo.png",
];

// INSTALL EVENT
self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(STATIC_ASSETS);
        })
    );
    self.skipWaiting();
});

// ACTIVATE EVENT
self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(
                keys
                    .filter((key) => key !== CACHE_NAME)
                    .map((key) => caches.delete(key))
            )
        )
    );
    self.clients.claim();
});

// FETCH HANDLER (GET requests ONLY)
self.addEventListener("fetch", (event) => {
    const req = event.request;

    // ❌ Never touch POST/PUT/PATCH/DELETE — handled by offline_sync.js
    if (req.method !== "GET") return;

    event.respondWith(
        caches.match(req).then((cached) => {
            if (cached) return cached;

            return fetch(req)
                .then((response) => {
                    // Save clone into cache (GET only)
                    const copy = response.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(req, copy);
                    });
                    return response;
                })
                .catch(() => {
                    // Offline fallback for navigation
                    if (req.mode === "navigate") {
                        return caches.match("/offline/");
                    }
                });
        })
    );
});
