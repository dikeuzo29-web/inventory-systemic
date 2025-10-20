// static/js/bottle_returns.js

document.addEventListener("DOMContentLoaded", function () {
    const productSelect = document.querySelector("#id_product");
    const quantityInput = document.querySelector("#id_quantity");
    const outstandingBottles = document.querySelector("#outstanding-bottles");

    if (!productSelect || !quantityInput || !outstandingBottles) {
        console.warn("Bottle returns form elements not found.");
        return;
    }

    async function updateOutstanding(productId) {
        if (navigator.onLine) {
            // Try server fetch first
            try {
                const response = await fetch(`/api/products/${productId}/`);
                if (!response.ok) throw new Error("Failed to fetch product data");
                const data = await response.json();
                outstandingBottles.textContent = data.bottles_outstanding;
                quantityInput.setAttribute("max", data.bottles_outstanding);
                return;
            } catch (err) {
                console.error("Error fetching product online:", err);
            }
        }

        // --- Offline fallback (IndexedDB via Dexie) ---
        try {
            const db = await getDB(); // defined in offline_logic.js
            const product = await db.products.get(parseInt(productId));
            if (product) {
                outstandingBottles.textContent = product.bottles_outstanding || 0;
                quantityInput.setAttribute("max", product.bottles_outstanding || 0);
            } else {
                outstandingBottles.textContent = "0";
                quantityInput.removeAttribute("max");
            }
        } catch (error) {
            console.error("Offline fallback failed:", error);
            outstandingBottles.textContent = "0";
        }
    }

    // Update outstanding bottles when product changes
    productSelect.addEventListener("change", function () {
        const productId = this.value;
        if (productId) {
            updateOutstanding(productId);
        } else {
            outstandingBottles.textContent = "0";
            quantityInput.removeAttribute("max");
        }
    });

    // Trigger change event if product is pre-selected
    if (productSelect.value) {
        productSelect.dispatchEvent(new Event("change"));
    }
});
