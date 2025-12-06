/* global workbox */
import { precacheAndRoute } from 'workbox-precaching';
import { registerRoute } from 'workbox-routing';
import { NetworkFirst, NetworkOnly } from 'workbox-strategies';
import { BackgroundSyncQueue } from 'workbox-background-sync';

// Precache manifest injected by vite-plugin-pwa
precacheAndRoute(self.__WB_MANIFEST || []);

// --- 1. Runtime Caching for GET Requests (APIs) ---
// Use NetworkFirst for API reads to get fresh data but fall back to cache if offline
registerRoute(
  ({ url, request }) => url.pathname.startsWith('/api/') && request.method === 'GET',
  new NetworkFirst({
    cacheName: 'api-read-cache',
    networkTimeoutSeconds: 10,
  })
);

// --- 2. Background Sync for POST Requests (Transactions) ---
const bgQueue = new BackgroundSyncQueue('post-requests-queue', {
  // Optional custom logic when sync event triggers
  onSync: async ({ queue }) => {
    let entry;
    while ((entry = await queue.shiftEntry())) {
      try {
        const response = await fetch(entry.request);
        // You might want to notify the user/app that a sync occurred
        console.log(`Synced request: ${entry.request.url}`, response.status);
      } catch (err) {
        // If fetch fails again (e.g., temporary network drop), re-queue for next sync
        await queue.unshiftEntry(entry);
        throw err;
      }
    }
  },
});

// Intercept all POST requests to /api/ and use NetworkOnly
// If the request fails (due to being offline), put it into the background queue.
registerRoute(
  ({ request, url }) => request.method === 'POST' && url.pathname.startsWith('/api/'),
  new NetworkOnly({
    plugins: [
      {
        // fetchDidFail is triggered when the request fails (e.g., browser offline)
        fetchDidFail: async ({ request }) => {
          await bgQueue.pushRequest(request);
          // Optional: send a message back to the client UI (App.jsx)
        }
      }
    ],
  }),
  'POST'
);

// Optional: Force activation immediately
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', () => self.clients.claim());