// static/js/sales.js

document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("salesForm");
    if (!form) return; // Safety guard if form doesn't exist

    // 🔍 Product search filtering
    const productSearch = document.getElementById("product-search");
    const productSelect = document.getElementById("product-select");
    
    if (productSearch && productSelect) {
        productSearch.addEventListener("input", function () {
            const searchValue = this.value.toLowerCase();
    
            Array.from(productSelect.options).forEach(option => {
                if (!option.value) return; // keep placeholder
    
                const text = option.text.toLowerCase();
                option.style.display = text.includes(searchValue) ? "" : "none";
            });
        });
    
        // Optional: clear search once product is chosen
        productSelect.addEventListener("change", function () {
            productSearch.value = "";
        });
    }


    form.addEventListener("submit", async function (e) {
        e.preventDefault(); // Always prevent default

        const productId = form.querySelector("#product-select").value;
        const quantity = parseInt(form.querySelector("#quantity-input").value);

        if (!productId || isNaN(quantity) || quantity <= 0) {
            alert("Please select a product and enter a valid quantity.");
            return;
        }

        if (navigator.onLine) {
            // Online submission attempt
            try {
                const csrftoken = getCSRFToken(); // from utils.js/offline_logic.js
                const response = await fetch(form.action, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrftoken,
                    },
                    body: JSON.stringify({ product: productId, quantity: quantity }),
                });

                if (response.ok) {
                    alert("✅ Sale recorded successfully!");
                    form.reset();
                    // Refresh product cache + dropdown after online success
                    await cacheProductsForOfflineUsage();
                    await populateProductSelect();
                    await updatePendingSalesBadge();
                } else {
                    const errorData = await response.json();
                    const errorMessage = errorData.message || "Failed to record sale online.";
                    alert(`❌ Error recording sale online: ${errorMessage}`);
                    console.error("Online sale failed:", errorData);

                    // Try to save offline
                    const saved = await saveOfflineSale(productId, quantity);
                    if (saved) {
                        alert("⚠️ Sale saved offline. Will sync when back online.");
                        form.reset();
                    }
                }
            } catch (error) {
                // Network error during online submission
                console.error("Network error during online sale attempt:", error);
                const saved = await saveOfflineSale(productId, quantity);
                if (saved) {
                    alert("⚠️ Network error, sale saved offline. Will sync when back online.");
                    form.reset();
                }
            }
        } else {
            // Direct offline save
            const saved = await saveOfflineSale(productId, quantity);
            if (saved) {
                alert("📦 Sale saved offline. Will sync when back online.");
                form.reset();
            }
        }
    });
});

