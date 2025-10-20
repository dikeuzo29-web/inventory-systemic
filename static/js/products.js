// products.js
document.addEventListener('DOMContentLoaded', function () {
    // Bootstrap styling
    document.querySelectorAll('input[type="text"], input[type="number"], input[type="email"], textarea')
        .forEach(el => el.classList.add('form-control'));
    document.querySelectorAll('input[type="date"]')
        .forEach(el => el.classList.add('form-control', 'date-picker'));
    document.querySelectorAll('select')
        .forEach(el => el.classList.add('form-select'));

    // Returnable radio toggle
    const returnableRadios = document.querySelectorAll('input[name="is_returnable"]');
    const depositGroup = document.getElementById('deposit-group');
    function toggleDeposit() {
        if (document.querySelector('input[name="is_returnable"]:checked')?.value === 'True') {
            depositGroup.style.display = 'block';
        } else {
            depositGroup.style.display = 'none';
        }
    }
    returnableRadios.forEach(r => r.addEventListener('change', toggleDeposit));
    toggleDeposit();

    // Flatpickr init
    const dateInput = document.querySelector('input[type="date"]');
    if (dateInput) {
        flatpickr(dateInput, { dateFormat: "m/d/Y", allowInput: true, placeholder: "mm/dd/yyyy" });
    }

    // Deposit default
    const depositField = document.querySelector('#id_deposit_amount');
    if (depositField && !depositField.value) depositField.value = '0.00';

    // Handle product form submit
    const form = document.getElementById("productForm");
    if (form) {
        form.addEventListener("submit", async function (e) {
            e.preventDefault();
            const formData = Object.fromEntries(new FormData(form).entries());
            if (navigator.onLine) {
                try {
                    const csrftoken = getCSRFToken();
                    const res = await fetch(form.action, {
                        method: "POST",
                        headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
                        body: JSON.stringify(formData)
                    });
                    if (res.ok) {
                        alert("✅ Product saved online");
                        form.reset();
                        await cacheProductsForOfflineUsage();
                        await populateProductSelect();
                    } else {
                        throw new Error("Server rejected product");
                    }
                } catch (err) {
                    console.warn("Online product save failed, falling back offline:", err);
                    await saveOfflineProduct(formData);
                    alert("💾 Product saved offline, will sync later.");
                    form.reset();
                }
            } else {
                await saveOfflineProduct(formData);
                alert("💾 Product saved offline, will sync later.");
                form.reset();
            }
        });
    }
});
