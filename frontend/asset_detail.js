let chartInstance = null;
let fullHistory = []; // Store full history for filtering

document.addEventListener('DOMContentLoaded', () => {
    if (!Auth.requireAuth()) return;

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
        const asset = await API.get(Config.ENDPOINTS.ASSETS + id);
        
        // Update Title
        const titleEl = document.getElementById('assetTitle');
        if (titleEl) {
            titleEl.textContent = `${asset.code} - ${asset.name}`;
        }
        
        // Process History
        if (asset.history && asset.history.length > 0) {
            fullHistory = asset.history;
            drawChart(asset.history, asset.code);
            loadPriceHistoryTable(asset.history);
        } else {
            document.getElementById('priceHistoryTable').innerHTML = '<tr><td colspan="2" class="text-center text-muted">No price data available</td></tr>';
        }
        
    } catch (error) {
        console.error("Error:", error);
    }
}

async function loadMyPosition(id) {
    try {
        const item = await API.get(Config.ENDPOINTS.PORTFOLIO + 'asset/' + id);
        
        // Use new IDs from refactored HTML
        const qtyEl = document.getElementById('detailQuantity');
        const costEl = document.getElementById('detailAvgCost');
        const valEl = document.getElementById('detailTotalValue');
        const profitEl = document.getElementById('detailProfitLoss');
        
        if (qtyEl) qtyEl.textContent = formatNumber(item.quantity);
        if (costEl) costEl.textContent = formatCurrency(item.average_cost);
        if (valEl) valEl.textContent = formatCurrency(item.total_value);
        
        if (profitEl) {
            const profitSign = item.profit_loss >= 0 ? '+' : '';
            profitEl.textContent = `${profitSign}${formatCurrency(item.profit_loss)} (%${formatNumber(item.profit_loss_percent)})`;
            
            if (item.profit_loss >= 0) {
                profitEl.classList.add('text-success');
                profitEl.classList.remove('text-danger');
            } else {
                profitEl.classList.add('text-danger');
                profitEl.classList.remove('text-success');
            }
        }
        
    } catch (error) {
        console.error("Error position:", error);
    }
}

function loadPriceHistoryTable(history) {
    const tableBody = document.getElementById('priceHistoryTable');
    if (!tableBody) return;
    
    tableBody.innerHTML = '';
    
    // Sort by date desc (newest first)
    const sortedHistory = [...history].sort((a, b) => new Date(b.date) - new Date(a.date));
    
    sortedHistory.forEach(h => {
        const row = document.createElement('tr');
        const date = new Date(h.date).toLocaleDateString(currentLang === 'tr' ? 'tr-TR' : 'en-US');
        
        row.innerHTML = `
            <td class="ps-3">${date}</td>
            <td class="text-end pe-3">${formatCurrency(h.price)}</td>
        `;
        tableBody.appendChild(row);
    });
}

function drawChart(history, label) {
    const ctx = document.getElementById('priceChart');
    if (!ctx) return;
    
    const dates = history.map(h => h.date);
    const prices = history.map(h => h.price);
    
    if (chartInstance) {
        chartInstance.destroy();
    }
    
    chartInstance = new Chart(ctx.getContext('2d'), {
        type: 'line',
        data: {
            labels: dates,
            datasets: [{
                label: label,
                data: prices,
                borderColor: '#0d6efd',
                backgroundColor: 'rgba(13, 110, 253, 0.1)',
                tension: 0.2, // Slightly smoother curve
                fill: true,
                pointRadius: 0, // Cleaner look without points
                pointHoverRadius: 6,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index',
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(255, 255, 255, 0.9)',
                    titleColor: '#000',
                    bodyColor: '#000',
                    borderColor: '#ddd',
                    borderWidth: 1,
                    padding: 10,
                    callbacks: {
                        label: function(context) {
                            return formatCurrency(context.parsed.y);
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'day', // Default to showing days
                        displayFormats: {
                            day: 'd MMM',
                            month: 'MMM yyyy'
                        }
                    },
                    grid: {
                        display: false
                    },
                    ticks: {
                        maxRotation: 0,
                        autoSkip: true,
                        maxTicksLimit: 6
                    }
                },
                y: {
                    beginAtZero: false, // Better for price charts
                    grid: {
                        borderDash: [5, 5],
                        color: '#f0f0f0'
                    },
                    ticks: {
                        callback: function(value) {
                            return value.toLocaleString();
                        }
                    }
                }
            }
        }
    });
}
