// static/js/restock.js
document.addEventListener("DOMContentLoaded", function () {
    const restockForm = document.getElementById("restockForm");

    if (!restockForm) {
        console.warn("Restock form not found on page.");
        return;
    }

    restockForm.addEventListener("submit", async function (e) {
        e.preventDefault();

        const productId = this.querySelector("#product-select").value;
        const quantity = parseInt(this.querySelector("#quantity-input").value);

        if (!productId || isNaN(quantity) || quantity <= 0) {
            alert("Please select a product and enter a valid quantity.");
            return;
        }

        const csrftoken = getCSRFToken(); // from offline_logic.js

        if (navigator.onLine) {
            try {
                const response = await fetch(this.action, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrftoken,
                    },
                    body: JSON.stringify({
                        product: productId,
                        quantity: quantity,
                    }),
                });

                if (response.ok) {
                    alert("Restock recorded successfully!");
                    this.reset();
                    await cacheProductsForOfflineUsage();
                    await populateProductSelect();
                    await updatePendingRestocksBadge();
                } else {
                    const errorData = await response.json();
                    console.error("Online restock failed:", errorData);
                    const saved = await saveOfflineRestock(productId, quantity);
                    if (saved) {
                        alert("Online submission failed, restock saved offline.");
                        this.reset();
                    }
                }
            } catch (error) {
                console.error("Network error during restock:", error);
                const saved = await saveOfflineRestock(productId, quantity);
                if (saved) {
                    alert("Network error, restock saved offline.");
                    this.reset();
                }
            }
        } else {
            // Offline
            const saved = await saveOfflineRestock(productId, quantity);
            if (saved) {
                alert("Restock saved offline. Will sync later.");
                this.reset();
            }
        }
    });
});
