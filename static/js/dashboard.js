// dashboard.js
document.addEventListener('DOMContentLoaded', function () {
    const periodSelect = document.getElementById('periodSelect');
    const startDate = document.getElementById('startDate');
    const endDate = document.getElementById('endDate');

    function toggleDateInputs() {
        const isCustom = periodSelect.value === 'custom';
        startDate.disabled = !isCustom;
        endDate.disabled = !isCustom;
        if (!isCustom) { startDate.value = ''; endDate.value = ''; }
    }
    periodSelect.addEventListener('change', toggleDateInputs);
    toggleDateInputs();

    // Render helper
    function renderCharts(data) {
        const charts = Chart.instances;
        charts.forEach(chart => {
            if (chart.canvas.id === 'salesTrendChart') {
                chart.data.labels = data.sales_trend.dates;
                chart.data.datasets[0].data = data.sales_trend.revenues;
                chart.data.datasets[1].data = data.sales_trend.quantities;
            } else if (chart.canvas.id === 'inventoryChart') {
                chart.data.labels = data.inventory_by_category.labels;
                chart.data.datasets[0].data = data.inventory_by_category.values;
            } else if (chart.canvas.id === 'topProductsChart') {
                chart.data.labels = data.top_products.labels;
                chart.data.datasets[0].data = data.top_products.sales;
                chart.data.datasets[1].data = data.top_products.revenues;
            }
            chart.update();
        });
    }

    // Fetch with offline support
    async function updateCharts() {
        const key = `chart_${periodSelect.value}_${startDate.value}_${endDate.value}`;
        if (!navigator.onLine) {
            console.log("📉 Offline: loading cached chart data");
            const cached = await db.chartCache.get(key);
            if (cached && cached.data) renderCharts(cached.data);
            return;
        }
        try {
            const res = await fetch(`/api/chart-data/?period=${periodSelect.value}&start_date=${startDate.value}&end_date=${endDate.value}`);
            if (!res.ok) throw new Error("Chart API failed");
            const data = await res.json();
            await db.chartCache.put({ key, data });
            renderCharts(data);
        } catch (err) {
            console.error("Chart update failed:", err);
        }
    }

    setInterval(updateCharts, 5 * 60 * 1000);
    updateCharts();

    // Quick range buttons
    document.querySelectorAll('.chart-btn').forEach(btn => {
        btn.addEventListener('click', async function () {
            document.querySelectorAll('.chart-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            const range = this.dataset.range;
            if (!navigator.onLine) {
                console.log("📉 Offline range change ignored (use cached)");
                return;
            }
            const res = await fetch(`/api/chart-data/?period=custom&range=${range}&start_date=${startDate.value}&end_date=${endDate.value}`);
            const data = await res.json();
            renderCharts(data);
        });
    });
});
