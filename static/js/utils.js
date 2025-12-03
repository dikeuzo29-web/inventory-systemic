// static/js/utils.js

// Small UUID v4 generator for idempotency keys
function uuidv4() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
        const r = crypto.getRandomValues(new Uint8Array(1))[0] & 15;
        const v = c === 'x' ? r : (r & 0x3) | 0x8;
        return v.toString(16);
    });
}

function getCSRFToken() {
    const el = document.querySelector('[name=csrfmiddlewaretoken]');
    return el ? el.value : '';
}

function formatNaira(amount) {
    if (amount === undefined || amount === null) return '₦0';
    return `₦${Number(amount).toLocaleString('en-NG')}`;
}

function showToast(message, { type = 'info', timeout = 3500 } = {}) {
    // Minimal toast — create container if not exists
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.position = 'fixed';
        container.style.right = '16px';
        container.style.bottom = '16px';
        container.style.zIndex = '99999';
        document.body.appendChild(container);
    }
    const el = document.createElement('div');
    el.className = `toast toast-${type}`;
    el.textContent = message;
    el.style.marginTop = '8px';
    el.style.padding = '10px 14px';
    el.style.borderRadius = '8px';
    el.style.background = type === 'error' ? '#ff595e' : (type === 'success' ? '#4CAF50' : '#333');
    el.style.color = '#fff';
    el.style.boxShadow = '0 6px 18px rgba(0,0,0,0.2)';
    container.appendChild(el);
    setTimeout(() => {
        el.style.transition = 'opacity 300ms';
        el.style.opacity = '0';
        setTimeout(() => el.remove(), 350);
    }, timeout);
}

// safeFetch wrapper: adds idempotency-key and CSRF; returns fetch response or throws
async function safeFetch(url, opts = {}, idempotencyKey = null) {
    const headers = new Headers(opts.headers || {});
    // Set JSON content-type unless body is FormData
    if (!(opts.body instanceof FormData) && !headers.has('Content-Type')) {
        headers.set('Content-Type', 'application/json');
    }
    const csrftoken = getCSRFToken();
    if (csrftoken && !headers.has('X-CSRFToken')) headers.set('X-CSRFToken', csrftoken);
    if (idempotencyKey) headers.set('Idempotency-Key', idempotencyKey);

    const fetchOpts = Object.assign({}, opts, { headers });
    const resp = await fetch(url, fetchOpts);
    return resp;
}

export { uuidv4, getCSRFToken, formatNaira, showToast, safeFetch };
