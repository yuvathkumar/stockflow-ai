// Close success messages automatically after 5 seconds
document.querySelectorAll(".alert-success").forEach((alert) => {
    setTimeout(() => bootstrap.Alert.getOrCreateInstance(alert).close(), 5000);
});

// Live product search and "Low stock" filter
(function () {
    const search = document.getElementById("product-search");
    if (!search) return;

    const cards = document.querySelectorAll("[data-product-card]");
    const filterButtons = document.querySelectorAll("[data-filter]");
    const noResults = document.getElementById("no-results");
    let activeFilter = "all";

    function applyFilters() {
        const term = search.value.trim().toLowerCase();
        let visibleCount = 0;

        cards.forEach((card) => {
            const matchesText = card.dataset.name.includes(term);
            const matchesFilter = activeFilter === "all" || card.dataset.low === "true";
            const visible = matchesText && matchesFilter;
            card.hidden = !visible;
            if (visible) visibleCount++;
        });

        if (noResults) noResults.hidden = visibleCount !== 0 || cards.length === 0;
    }

    search.addEventListener("input", applyFilters);
    filterButtons.forEach((button) => {
        button.addEventListener("click", () => {
            activeFilter = button.dataset.filter;
            filterButtons.forEach((b) => b.classList.toggle("active", b === button));
            applyFilters();
        });
    });
})();