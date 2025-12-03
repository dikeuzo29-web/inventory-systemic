// static/js/offline_sync.js
// Ensure dexie.min.js is loaded before this script

// Dexie DB setup
const db = new Dexie('InventoryAppOfflineDB');
db.version(1).stores({
    products_to_sync: '++id,createdAt',
    sales_to_sync: '++id,createdAt,product_id,quantity,type,uuid',
    restocks_to_sync: '++id,createdAt,product_id,quantity,uuid',
    products_cache: 'id,name,price,quantity,is_returnable,deposit_amount,bottles_outstanding',
    queue_meta: 'key,value' // for storing backoff state, last sync times, etc.
});

// helpers (local)
async function setMeta(key, value) {
    await db.queue_meta.put({ key, value });
}
async function getMeta(key) {
    const rec = await db.queue_meta.get(key);
    return rec ? rec.value : null;
}

// Badges & UI helpers (minimal)
async function updatePendingSalesBadge() {
    const count = await db.sales_to_sync.count();
    const badge = document.getElementById('pending-sales-badge');
    if (badge) { badge.textContent = count; badge.style.display = count > 0 ? 'inline-block' : 'none'; }
}
async function updatePendingRestocksBadge() {
    const count = await db.restocks_to_sync.count();
    const badge = document.getElementById('pending-restocks-badge');
    if (badge) { badge.textContent = count; badge.style.display = count > 0 ? 'inline-block' : 'none'; }
}
async function updatePendingProductsBadge() {
    const count = await db.products_to_sync.count();
    const badge = document.getElementById('pending-products-badge');
    if (badge) { badge.textContent = count; badge.style.display = count > 0 ? 'inline-block' : 'none'; }
}

// Use the utils functions - assumes utils.js is loaded and creates global functions
// If you use modules, import { uuidv4, getCSRFToken, showToast, safeFetch } from './utils';
const _uuid = window.uuidv4 || (() => 'uid-' + Date.now());
const _showToast = window.showToast || (msg => console.log('TOAST:', msg));
const _safeFetch = window.safeFetch || (async (u, o, k) => fetch(u, o));

// Generic enqueue functions (sales / restocks / products)
async function enqueueSale({ product_id, quantity, type = 'sale' }) {
    const uuid = (window.uuidv4 && uuidv4()) || ('uuid-' + Date.now() + '-' + Math.random().toString(36).slice(2));
    await db.sales_to_sync.add({
        product_id, quantity, type,
        createdAt: new Date().toISOString(),
        uuid
    });
    await updatePendingSalesBadge();
    _showToast('Sale saved offline');
    return uuid;
}

async function enqueueRestock({ product_id, quantity }) {
    const uuid = (window.uuidv4 && uuidv4()) || ('uuid-' + Date.now() + '-' + Math.random().toString(36).slice(2));
    await db.restocks_to_sync.add({
        product_id, quantity,
        createdAt: new Date().toISOString(),
        uuid
    });
    await updatePendingRestocksBadge();
    _showToast('Restock saved offline');
    return uuid;
}

async function enqueueProductCreate(productData) {
    await db.products_to_sync.add({
        data: productData,
        createdAt: new Date().toISOString()
    });
    await updatePendingProductsBadge();
    _showToast('Product created offline');
}

// Product caching for offline UI
async function cacheProductsForOfflineUsage() {
    try {
        // try manage endpoint first
        let resp = await fetch('/api/stock/manage/products/');
        if (!resp.ok) resp = await fetch('/api/products/');
        if (!resp.ok) {
            console.warn('[CACHE] No products endpoint found');
            return;
        }
        const contentType = resp.headers.get('content-type') || '';
        if (!contentType.includes('application/json')) return;
        const payload = await resp.json();
        let arr = [];
        if (Array.isArray(payload)) arr = payload;
        else if (payload.results) arr = payload.results;
        else if (payload.products) arr = payload.products;
        if (!arr.length) return;
        await db.transaction('rw', db.products_cache, async () => {
            await db.products_cache.clear();
            await db.products_cache.bulkAdd(arr);
        });
        _showToast('Products cached for offline use');
    } catch (err) {
        console.warn('[CACHE] Product caching failed', err);
    }
}

// Populate product select UI (shared)
async function populateProductSelect() {
    const select = document.getElementById('product-select');
    if (!select) return;
    const products = await db.products_cache.toArray();
    select.innerHTML = '<option value="" disabled selected>-- Select Product --</option>';
    for (const p of products) {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = `${p.name} (Stock: ${p.quantity})`;
        select.appendChild(opt);
    }
}

// Sync worker: attempts to send local queued transactions to server with idempotency keys & backoff
let syncInProgress = false;

async function processQueueOnce({ maxRetries = 3, baseDelay = 1000 } = {}) {
    if (syncInProgress) return;
    syncInProgress = true;
    try {
        // Process products_to_sync first (creates)
        const products = await db.products_to_sync.toArray();
        for (const p of products) {
            try {
                const idempotency = (window.uuidv4 && uuidv4()) || ('pid-' + Date.now());
                const resp = await _safeFetch('/api/stock/manage/products/', {
                    method: 'POST',
                    body: JSON.stringify(p.data)
                }, idempotency);
                if (resp.ok) {
                    await db.products_to_sync.delete(p.id);
                    _showToast(`Product synced: ${p.data.name}`, { type: 'success' });
                } else {
                    console.warn('Product sync failed', await resp.text());
                }
            } catch (err) {
                console.error('Product sync exception', err);
            }
        }
        await updatePendingProductsBadge();

        // Process sales and returns
        const sales = await db.sales_to_sync.toArray();
        for (const s of sales) {
            try {
                const url = (s.type === 'return') ? '/api/stock/returns/' : '/api/transactions/';
                const payload = {
                    product: s.product_id,
                    quantity: s.quantity,
                    timestamp: s.createdAt,
                    client_uuid: s.uuid
                };
                const resp = await _safeFetch(url, {
                    method: 'POST',
                    body: JSON.stringify(payload)
                }, s.uuid); // idempotency key = uuid
                if (resp.ok) {
                    await db.sales_to_sync.delete(s.id);
                    _showToast(`Synced ${s.type} for product ${s.product_id}`, { type: 'success' });
                } else {
                    const text = await resp.text();
                    console.warn('Sale sync non-ok', text);
                }
            } catch (err) {
                console.error('Sale sync error', err);
            }
        }
        await updatePendingSalesBadge();

        // Process restocks
        const restocks = await db.restocks_to_sync.toArray();
        for (const r of restocks) {
            try {
                const payload = { product: r.product_id, quantity: r.quantity, timestamp: r.createdAt, client_uuid: r.uuid };
                const resp = await _safeFetch('/api/stock/restock/', {
                    method: 'POST',
                    body: JSON.stringify(payload)
                }, r.uuid);
                if (resp.ok) {
                    await db.restocks_to_sync.delete(r.id);
                    _showToast(`Synced restock for product ${r.product_id}`, { type: 'success' });
                } else {
                    console.warn('Restock sync not ok', await resp.text());
                }
            } catch (err) {
                console.error('Restock sync error', err);
            }
        }
        await updatePendingRestocksBadge();

        // refresh product cache after successful syncs
        await cacheProductsForOfflineUsage();

        // Inform UI
        try {
            const clientsList = await clients.matchAll({ includeUncontrolled: true });
            for (const c of clientsList) {
                c.postMessage({ type: 'SYNC_COMPLETE' });
            }
        } catch (e) { /* ignore */ }

    } finally {
        syncInProgress = false;
    }
}

// Robust sync loop with exponential backoff
async function startSyncLoop() {
    // Attempt to sync whenever we are online
    window.addEventListener('online', () => {
        _showToast('Online — syncing queued items...');
        processQueueOnce();
    });

    // Try on load if online
    if (navigator.onLine) {
        processQueueOnce();
    }
}

// Public API for other scripts
window.OfflineSync = {
    enqueueSale,
    enqueueRestock,
    enqueueProductCreate,
    cacheProductsForOfflineUsage,
    populateProductSelect,
    processQueueOnce,
    startSyncLoop,
    updatePendingBadges: async () => {
        await updatePendingSalesBadge();
        await updatePendingRestocksBadge();
        await updatePendingProductsBadge();
    }
};

// Start the loop on load
document.addEventListener('DOMContentLoaded', async () => {
    await cacheProductsForOfflineUsage();
    await populateProductSelect();
    await OfflineSync.updatePendingBadges();
    startSyncLoop();
});

