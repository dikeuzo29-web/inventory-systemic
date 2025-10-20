// static/js/offline_sync.js

// Make sure Dexie.js is loaded BEFORE this script.
// <script src="{% static 'js/dexie.min.js' %}"></script>

// offline_logic.js
// Unified Offline Logic for Inventory App

// --- IndexedDB Setup ---
const db = new Dexie('InventoryAppOfflineDB');
db.version(1).stores({
    products_to_sync: '++id,data,csrf_token',
    sales_to_sync: '++id,product_id,quantity,timestamp,csrf_token,type', // sale or return
    restocks_to_sync: '++id,product_id,quantity,timestamp,csrf_token',   // restocks
    products_cache: 'id,name,price,quantity,is_returnable,deposit_amount,bottles_outstanding',
    chartCache: "key,data" // cached dashboard data
});

// --- Helper Functions ---
function formatNaira(amount) {
    return `₦${Number(amount).toLocaleString("en-NG")}`;
}

function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}

async function updatePendingSalesBadge() {
    const count = await db.sales_to_sync.count();
    const badge = document.getElementById('pending-sales-badge');
    if (badge) {
        badge.textContent = count;
        badge.style.display = count > 0 ? 'inline-block' : 'none';
    }
}

async function updatePendingProductsBadge() {
    const count = await db.products_to_sync.count();
    const badge = document.getElementById('pending-products-badge');
    if (badge) {
        badge.textContent = count;
        badge.style.display = count > 0 ? 'inline-block' : 'none';
    }
}

async function updatePendingRestocksBadge() {
    const count = await db.restocks_to_sync.count();
    const badge = document.getElementById('pending-restocks-badge');
    if (badge) {
        badge.textContent = count;
        badge.style.display = count > 0 ? 'inline-block' : 'none';
    }
}

// --- Offline Data Saving ---
async function saveOfflineProduct(formData) {
    try {
        const csrftoken = getCSRFToken();
        await db.products_to_sync.add({
            data: formData,
            csrf_token: csrftoken,
            timestamp: new Date().toISOString()
        });
        updatePendingProductsBadge();
        return true;
    } catch (error) {
        console.error('Failed to save product offline:', error);
        alert('Failed to save product offline: ' + error.message);
        return false;
    }
}

async function saveOfflineSale(productId, quantity) {
    try {
        const product = await db.products_cache.get(parseInt(productId));
        if (!product) {
            alert('Error: Product not found in offline data. Cannot save sale.');
            return false;
        }
        if (product.quantity < quantity) {
            alert(`Insufficient local stock for ${product.name}. Available: ${product.quantity}.`);
            return false;
        }
        await db.products_cache.update(product.id, { quantity: product.quantity - quantity });
        console.log(`[OFFLINE] Sale recorded: ${product.name} x${quantity}`);

        const csrftoken = getCSRFToken();
        await db.sales_to_sync.add({
            type: "sale",
            product_id: productId,
            quantity,
            timestamp: new Date().toISOString(),
            csrf_token: csrftoken
        });
        updatePendingSalesBadge();
        return true;
    } catch (error) {
        console.error('Failed to save sale offline:', error);
        return false;
    }
}

async function saveOfflineReturn(productId, quantity) {
    try {
        const product = await db.products_cache.get(parseInt(productId));
        if (!product) {
            alert('Error: Product not found in offline cache. Cannot save return.');
            return false;
        }
        await db.products_cache.update(product.id, {
            bottles_outstanding: (product.bottles_outstanding || 0) - quantity
        });

        const csrftoken = getCSRFToken();
        await db.sales_to_sync.add({
            type: "return",
            product_id: productId,
            quantity,
            timestamp: new Date().toISOString(),
            csrf_token: csrftoken
        });

        console.log(`[OFFLINE] Return recorded: ${product.name} x${quantity}`);
        updatePendingSalesBadge();
        return true;
    } catch (err) {
        console.error("Failed to save return offline:", err);
        return false;
    }
}

async function saveOfflineRestock(productId, quantity) {
    try {
        const product = await db.products_cache.get(parseInt(productId));
        if (!product) {
            alert('Error: Product not found in offline cache. Cannot save restock.');
            return false;
        }
        await db.products_cache.update(product.id, { quantity: product.quantity + quantity });
        console.log(`[OFFLINE] Restock recorded: ${product.name} +${quantity}`);

        const csrftoken = getCSRFToken();
        await db.restocks_to_sync.add({
            product_id: productId,
            quantity,
            timestamp: new Date().toISOString(),
            csrf_token: csrftoken
        });
        updatePendingRestocksBadge();
        return true;
    } catch (error) {
        console.error('Failed to save restock offline:', error);
        return false;
    }
}

// --- Sync Functions ---
async function syncProducts() {
    console.log('[SYNC] Products...');
    const pending = await db.products_to_sync.toArray();
    for (const tx of pending) {
        try {
            const response = await fetch('/api/stock/manage/products/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': tx.csrf_token,
                },
                body: JSON.stringify(tx.data),
            });
            if (response.ok) {
                await db.products_to_sync.delete(tx.id);
                console.log(`[SYNC] Product ${tx.id} synced.`);
            }
        } catch (error) {
            console.error('[SYNC] Product error:', error);
        }
    }
    updatePendingProductsBadge();
    await cacheProductsForOfflineUsage();
    await populateProductSelect();
}

async function syncSales() {
    console.log('[SYNC] Sales/Returns...');
    const pending = await db.sales_to_sync.toArray();
    for (const tx of pending) {
        try {
            let url = tx.type === "return" ? "/api/stock/returns/" : "/api/transactions/";
            const response = await fetch(url, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": tx.csrf_token,
                },
                body: JSON.stringify({
                    product: tx.product_id,
                    quantity: tx.quantity,
                    timestamp: tx.timestamp
                }),
            });
            if (response.ok) {
                await db.sales_to_sync.delete(tx.id);
                console.log(`[SYNC] ${tx.type} ${tx.id} synced.`);
            }
        } catch (error) {
            console.error('[SYNC] Sale error:', error);
        }
    }
    updatePendingSalesBadge();
    await cacheProductsForOfflineUsage();
    await populateProductSelect();
}

async function syncRestocks() {
    console.log('[SYNC] Restocks...');
    const pending = await db.restocks_to_sync.toArray();
    for (const tx of pending) {
        try {
            const response = await fetch("/api/stock/restock/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": tx.csrf_token,
                },
                body: JSON.stringify({
                    product: tx.product_id,
                    quantity: tx.quantity,
                    timestamp: tx.timestamp
                }),
            });
            if (response.ok) {
                await db.restocks_to_sync.delete(tx.id);
                console.log(`[SYNC] Restock ${tx.id} synced.`);
            }
        } catch (error) {
            console.error('[SYNC] Restock error:', error);
        }
    }
    updatePendingRestocksBadge();
    await cacheProductsForOfflineUsage();
    await populateProductSelect();
}

// --- Product Cache ---
async function cacheProductsForOfflineUsage() {
    try {
        const response = await fetch('/api/stock/products/');
        if (!response.ok) return;
        const products = await response.json();
        await db.products_cache.clear();
        await db.products_cache.bulkAdd(products);
        console.log('[CACHE] Products updated.');
    } catch (error) {
        console.warn('[CACHE] Product caching failed:', error);
    }
}

async function populateProductSelect() {
    const select = document.getElementById('product-select');
    if (!select) return;
    const products = await db.products_cache.toArray();
    select.innerHTML = '<option value="" disabled selected>-- Select Product --</option>';
    products.forEach(p => {
        const option = document.createElement('option');
        option.value = p.id;
        option.textContent = `${p.name} (Stock: ${p.quantity}, Deposit: ${formatNaira(p.deposit_amount || 0)})`;
        select.appendChild(option);
    });
}

// --- Dashboard Charts ---
async function updateCharts() {
    const key = `chart_${periodSelect.value}_${startDate.value}_${endDate.value}`;
    if (!navigator.onLine) {
        console.log("[OFFLINE] Charts from cache...");
        const cached = await db.chartCache.get(key);
        if (cached) renderCharts(cached.data);
        return;
    }
    try {
        const response = await fetch(`/api/chart-data/?period=${periodSelect.value}&start_date=${startDate.value}&end_date=${endDate.value}`);
        if (response.ok) {
            const data = await response.json();
            await db.chartCache.put({ key, data });
            renderCharts(data);
        }
    } catch (error) {
        console.error("[CHART] Fetch failed:", error);
    }
}

// --- Initialization ---
document.addEventListener('DOMContentLoaded', async () => {
    await cacheProductsForOfflineUsage();
    await populateProductSelect();

    const offlineStatus = document.getElementById('offline-status');
    const updateOnlineStatus = () => {
        if (offlineStatus) offlineStatus.style.display = navigator.onLine ? 'none' : 'inline-block';
    };
    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);
    updateOnlineStatus();

    window.addEventListener('online', () => {
        syncProducts();
        syncSales();
        syncRestocks();
    });

    if (navigator.onLine) {
        syncProducts();
        syncSales();
        syncRestocks();
    }

    updatePendingProductsBadge();
    updatePendingSalesBadge();
    updatePendingRestocksBadge();
});
