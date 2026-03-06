document.addEventListener('DOMContentLoaded', () => {
    if (!Auth.requireAuth()) return;
    
    // Initial Load
    updateUserInfo();
    loadDashboardData();
    
    // Modal handlers (for Sidebar buttons)
    loadAssetsForSelect();
    document.getElementById('addAssetForm').addEventListener('submit', handleAddAsset);
    document.getElementById('addTransactionForm').addEventListener('submit', handleAddTransaction);
});

// Update Topbar User Info (Same as app.js)
async function updateUserInfo() {
    try {
        const user = await API.get(Config.ENDPOINTS.ME);
        const usernameEl = document.getElementById('topbarUsername');
        const avatarEl = document.getElementById('topbarAvatar');
        if (usernameEl) usernameEl.textContent = user.full_name || user.username;
        avatarEl.src = user.avatar_url;
    } catch (error) {
        console.error('Failed to load user info', error);
    }
}

// Override global changeLanguage
const baseChangeLanguage = window.changeLanguage;
window.changeLanguage = function(lang) {
    if (baseChangeLanguage) {
        baseChangeLanguage(lang, loadDashboardData);
    }
}

let historyChart = null;
let profitChart = null;

async function loadDashboardData() {
    try {
        const historyData = await API.get(Config.ENDPOINTS.HISTORY);
        
        // Update Summary Cards with latest day's data
        if (historyData.length > 0) {
            const lastDay = historyData[historyData.length - 1];
            
            document.getElementById('totalValue').textContent = formatCurrency(lastDay.total_value, 0, 0);
            document.getElementById('totalCost').textContent = formatCurrency(lastDay.total_cost, 0, 0);
            
            const totalProfitEl = document.getElementById('totalProfit');
            const profit = lastDay.total_profit;
            // Calculate percentage if cost > 0
            const percentage = lastDay.total_cost > 0 ? (profit / lastDay.total_cost * 100) : 0;
            
            totalProfitEl.textContent = `${profit >= 0 ? '+' : ''}${formatCurrency(profit, 0, 0)}`;
            
            const profitCard = document.getElementById('profitCard');
            const profitRatioCard = document.getElementById('profitRatioCard');
            const totalProfitRatioEl = document.getElementById('totalProfitRatio');

            if (profit < 0) {
                profitCard.classList.remove('bg-success');
                profitCard.classList.add('bg-danger');
                
                profitRatioCard.classList.remove('bg-info'); // or success
                profitRatioCard.classList.add('bg-danger');
            } else {
                profitCard.classList.remove('bg-danger');
                profitCard.classList.add('bg-success');
                
                profitRatioCard.classList.remove('bg-danger');
                profitRatioCard.classList.add('bg-info'); // or success
            }
            
            totalProfitRatioEl.textContent = `%${formatNumber(percentage)}`;

        } else {
            // No data
            document.getElementById('totalValue').textContent = formatCurrency(0);
            document.getElementById('totalCost').textContent = formatCurrency(0);
            document.getElementById('totalProfit').textContent = formatCurrency(0);
            document.getElementById('totalProfitRatio').textContent = '%0.00';
        }

        // Draw Chart
        renderChart(historyData);
        renderProfitChart(historyData);

    } catch (error) {
        console.error('Error loading dashboard data:', error);
    }
}

function renderChart(data) {
    const ctx = document.getElementById('historyChart').getContext('2d');
    
    const labels = data.map(item => item.date);
    const values = data.map(item => item.total_value);
    const costs = data.map(item => item.total_cost);
    // const profits = data.map(item => item.total_profit); // Maybe too crowded?

    if (historyChart) {
        historyChart.destroy();
    }

    historyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Total Value',
                    data: values,
                    borderColor: 'rgb(54, 162, 235)', // Blue
                    backgroundColor: 'rgba(54, 162, 235, 0.1)',
                    fill: true,
                    tension: 0.1
                },
                {
                    label: 'Total Cost',
                    data: costs,
                    borderColor: 'rgb(108, 117, 125)', // Grey
                    backgroundColor: 'rgba(108, 117, 125, 0.1)',
                    fill: true,
                    tension: 0.1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += formatCurrency(context.parsed.y, 0, 0);
                            }
                            return label;
                        }
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            },
            scales: {
                y: {
                    beginAtZero: false,
                    ticks: {
                        callback: function(value) {
                            return formatCurrency(value, 0, 0); // Simplified currency
                        }
                    }
                }
            }
        }
    });
}

function renderProfitChart(data) {
    const ctx = document.getElementById('profitChart').getContext('2d');
    
    const labels = data.map(item => item.date);
    const profits = data.map(item => item.total_profit);

    if (profitChart) {
        profitChart.destroy();
    }

    profitChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Total Profit/Loss',
                    data: profits,
                    borderColor: 'rgb(153, 102, 255)', // Purple line
                    // Gradient fill logic is complex in simple config, let's use simple fill
                    backgroundColor: 'rgba(153, 102, 255, 0.1)',
                    fill: {
                        target: 'origin',
                        above: 'rgba(75, 192, 192, 0.2)',   // Green above 0
                        below: 'rgba(255, 99, 132, 0.2)'    // Red below 0
                    },
                    tension: 0.1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += formatCurrency(context.parsed.y, 0, 0);
                            }
                            return label;
                        }
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            },
            scales: {
                y: {
                    beginAtZero: false,
                    grid: {
                        color: (context) => {
                            if (context.tick.value === 0) {
                                return 'rgba(0, 0, 0, 0.5)';
                            }
                            return 'rgba(0, 0, 0, 0.1)';
                        },
                        lineWidth: (context) => {
                             if (context.tick.value === 0) {
                                return 2;
                            }
                            return 1;
                        }
                    },
                    ticks: {
                        callback: function(value) {
                            return formatCurrency(value, 0, 0); 
                        }
                    }
                }
            }
        }
    });
}

// Modal Handlers (Copied from app.js)
async function loadAssetsForSelect() {
    try {
        const data = await API.get(Config.ENDPOINTS.ASSETS);
        const select = document.getElementById('assetSelect');
        if (!select) return;
        select.innerHTML = '';
        data.forEach(asset => {
            const option = document.createElement('option');
            option.value = asset.id;
            option.textContent = `${asset.code} - ${asset.name}`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading assets:', error);
    }
}

async function handleAddAsset(e) {
    e.preventDefault();
    // Assuming TRANSLATIONS is available via common.js or we rely on hardcoded for now?
    // app.js used TRANSLATIONS[currentLang].
    // Let's assume common.js sets it up or use fallbacks.
    const t = (window.TRANSLATIONS && window.TRANSLATIONS[window.currentLang]) || {
        alert_asset_added: "Asset added successfully",
        alert_error: "An error occurred"
    };

    const formData = new FormData(e.target);
    const data = {
        code: formData.get('code').toUpperCase(),
        name: formData.get('name'),
        type: formData.get('type')
    };
    
    try {
        await API.post(Config.ENDPOINTS.ASSETS, data);
        alert(t.alert_asset_added);
        loadAssetsForSelect(); 
        const modal = bootstrap.Modal.getInstance(document.getElementById('addAssetModal'));
        modal.hide();
        e.target.reset();
    } catch (error) {
        console.error('Add asset error:', error);
        alert(t.alert_error);
    }
}

async function handleAddTransaction(e) {
    e.preventDefault();
    const t = (window.TRANSLATIONS && window.TRANSLATIONS[window.currentLang]) || {
        alert_transaction_added: "Transaction added successfully",
        alert_error: "An error occurred"
    };

    const formData = new FormData(e.target);
    const data = {
        asset_id: parseInt(formData.get('asset_id')),
        quantity: parseFloat(formData.get('quantity')),
        average_cost: parseFloat(formData.get('average_cost'))
    };
    
    try {
        await API.post(Config.ENDPOINTS.TRANSACTION, data);
        alert(t.alert_transaction_added);
        // Reload dashboard data to reflect changes
        loadDashboardData(); 
        const modal = bootstrap.Modal.getInstance(document.getElementById('addTransactionModal'));
        modal.hide();
        e.target.reset();
    } catch (error) {
        console.error('Add transaction error:', error);
        alert(t.alert_error);
    }
}
