/* global workbox */
import { precacheAndRoute } from 'workbox-precaching';
import { registerRoute } from 'workbox-routing';
import { NetworkFirst } from 'workbox-strategies';
import { Queue } from 'workbox-background-sync';

// Precache manifest injected by vite-plugin-pwa
precacheAndRoute(self.__WB_MANIFEST || []);

// Basic runtime caching for API GET requests (adjust patterns as needed)
registerRoute(
  ({ url }) => url.pathname.startsWith('/api/'),
  new NetworkFirst({
    cacheName: 'api-cache',
    networkTimeoutSeconds: 10,
  }),
  'GET'
);

// Background queue for offline POST requests to API
const bgQueue = new Queue('post-requests-queue', {
  onSync: async ({ queue }) => {
    let entry;
    while ((entry = await queue.shiftRequest())) {
      try {
        await fetch(entry.request);
      } catch (err) {
        // re-queue and throw to retry later
        await queue.unshiftEntry(entry);
        throw err;
      }
    }
  },
});

// Intercept POSTs and use NetworkOnly with background queue plugin
registerRoute(
  ({ request }) => request.method === 'POST' && new URL(request.url).pathname.startsWith('/api/'),
  new workbox.strategies.NetworkOnly({
    plugins: [
      {
        fetchDidFail: async ({ request }) => {
          // If offline or fetch fails, put request into queue
          await bgQueue.pushRequest({ request });
        }
      }
    ],
  }),
  'POST'
);

// Optional: offline fallback page
self.addEventListener('install', (event) => {
  self.skipWaiting();
});
self.addEventListener('activate', (event) => {
  clients.claim();
});
