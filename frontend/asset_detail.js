let chartInstance = null;

document.addEventListener('DOMContentLoaded', () => {
    // Get Asset ID from URL
    const urlParams = new URLSearchParams(window.location.search);
    const assetId = urlParams.get('id');

    if (assetId) {
        // Translations handled by common.js auto-run
        loadAssetDetail(assetId);
        loadMyPosition(assetId);
    } else {
        alert("Asset ID missing!");
        window.location.href = "/";
    }
});

// Override global changeLanguage to reload detail
const baseChangeLanguage = window.changeLanguage;
window.changeLanguage = function(lang) {
    if (baseChangeLanguage) {
        baseChangeLanguage(lang, () => {
            // Reload detail to refresh chart labels or currency formats
            const urlParams = new URLSearchParams(window.location.search);
            const assetId = urlParams.get('id');
            if(assetId) {
                 loadAssetDetail(assetId);
                 loadMyPosition(assetId);
            }
        });
    }
}

async function loadAssetDetail(id) {
    try {
        const response = await fetch(`${API_BASE}/assets/${id}`);
        if (!response.ok) throw new Error("Failed to fetch asset");
        
        const asset = await response.json();
        
        // Update Info
        document.getElementById('assetCode').textContent = asset.code;
        document.getElementById('assetName').textContent = asset.name;
        document.getElementById('breadcrumbName').textContent = asset.code;
        
        // Update Current Price (Last history item)
        if (asset.history && asset.history.length > 0) {
            const lastPrice = asset.history[asset.history.length - 1].price;
            document.getElementById('currentPrice').textContent = formatCurrency(lastPrice);
            
            // Draw Chart
            drawChart(asset.history, asset.code);
        }
        
    } catch (error) {
        console.error("Error:", error);
    }
}

async function loadMyPosition(id) {
    try {
        const response = await fetch(`${API_BASE}/portfolio/asset/${id}?user_id=1`);
        if (!response.ok) throw new Error("Failed to fetch position");
        
        const item = await response.json();
        
        document.getElementById('myQuantity').textContent = formatNumber(item.quantity);
        document.getElementById('myAvgCost').textContent = formatCurrency(item.average_cost);
        document.getElementById('myTotalValue').textContent = formatCurrency(item.total_value);
        
        const profitEl = document.getElementById('myProfitLoss');
        const profitSign = item.profit_loss >= 0 ? '+' : '';
        profitEl.textContent = `${profitSign}${formatCurrency(item.profit_loss)}`;
        
        if (item.profit_loss >= 0) {
            profitEl.classList.add('text-success');
            profitEl.classList.remove('text-danger');
        } else {
            profitEl.classList.add('text-danger');
            profitEl.classList.remove('text-success');
        }
        
    } catch (error) {
        console.error("Error position:", error);
    }
}

function drawChart(history, label) {
    const ctx = document.getElementById('priceChart').getContext('2d');
    
    const dates = history.map(h => h.date);
    const prices = history.map(h => h.price);
    
    if (chartInstance) {
        chartInstance.destroy();
    }
    
    chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [{
                label: `${label}`,
                data: prices,
                borderColor: 'rgba(75, 192, 192, 1)',
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                tension: 0.1,
                fill: true
            }]
        },
        options: {
            responsive: true,
            scales: {
                x: {
                    display: true
                },
                y: {
                    display: true
                }
            }
        }
    });
}
