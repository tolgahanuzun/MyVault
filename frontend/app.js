document.addEventListener('DOMContentLoaded', () => {
    if (!Auth.requireAuth()) return;
    
    // Check for price update success
    if (localStorage.getItem('priceUpdateSuccess') === 'true') {
        const alertEl = document.getElementById('priceUpdateAlert');
        if (alertEl) {
            alertEl.classList.remove('d-none');
            // Remove the flag so it doesn't show again on reload
            localStorage.removeItem('priceUpdateSuccess');
        }
    }
    
    // Initial Load
    updateUserInfo();
    loadPortfolio();
    loadAssetsForSelect();
    
    // Form submit listeners
    document.getElementById('addAssetForm').addEventListener('submit', handleAddAsset);
    document.getElementById('addTransactionForm').addEventListener('submit', handleAddTransaction);
});

// Update Topbar User Info
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

// Override global changeLanguage to reload data
const baseChangeLanguage = window.changeLanguage;
window.changeLanguage = function(lang) {
    if (baseChangeLanguage) {
        baseChangeLanguage(lang, loadPortfolio);
    }
}

async function loadPortfolio() {
    try {
        const data = await API.get(Config.ENDPOINTS.PORTFOLIO);
        
        const tableBody = document.getElementById('portfolioTable');
        tableBody.innerHTML = '';
        
        let totalVal = 0;
        let totalCost = 0;
        let totalProf = 0;
        
        data.forEach(item => {
            const itemCost = item.quantity * item.average_cost;
            totalVal += item.total_value;
            totalCost += itemCost;
            totalProf += item.profit_loss;
            
            const row = document.createElement('tr');
            
            // Add profit/loss background class
            if (item.profit_loss > 0) {
                row.classList.add('row-profit');
            } else if (item.profit_loss < 0) {
                row.classList.add('row-loss');
            }
            
            const profitClass = item.profit_loss >= 0 ? 'profit' : 'loss';
            const profitSign = item.profit_loss >= 0 ? '+' : '';
            
            row.innerHTML = `
                <td><a href="/static/asset_detail.html?id=${item.asset_id}" style="text-decoration:none; font-weight:bold;">${item.asset_code}</a></td>
                <td>${item.asset_name}</td>
                <td>${formatNumber(item.quantity)}</td>
                <td>${formatCurrency(item.average_cost)}</td>
                <td>${formatCurrency(item.current_price)}</td>
                <td>${formatCurrency(item.total_value)}</td>
                <td class="${profitClass}">
                    ${profitSign}${formatCurrency(item.profit_loss)} (%${formatNumber(item.profit_loss_percent)})
                </td>
            `;
            tableBody.appendChild(row);
        });
        
        document.getElementById('totalValue').textContent = formatCurrency(totalVal, 0, 0);
        document.getElementById('totalCost').textContent = formatCurrency(totalCost, 0, 0);
        
        const totalProfitEl = document.getElementById('totalProfit');
        totalProfitEl.textContent = `${totalProf >= 0 ? '+' : ''}${formatCurrency(totalProf, 0, 0)}`;
        
        // Calculate Profit/Loss Ratio
        const profitRatio = totalCost > 0 ? (totalProf / totalCost * 100) : 0;
        const totalProfitRatioEl = document.getElementById('totalProfitRatio');
        if (totalProfitRatioEl) {
             totalProfitRatioEl.textContent = `%${formatNumber(profitRatio)}`;
        }

        const profitCard = document.getElementById('profitCard');
        const profitRatioCard = document.getElementById('profitRatioCard');
        
        if (totalProf < 0) {
            profitCard.classList.remove('bg-success');
            profitCard.classList.add('bg-danger');
            
            if (profitRatioCard) {
                profitRatioCard.classList.remove('bg-info');
                profitRatioCard.classList.add('bg-danger');
            }
        } else {
            profitCard.classList.remove('bg-danger');
            profitCard.classList.add('bg-success');
            
            if (profitRatioCard) {
                profitRatioCard.classList.remove('bg-danger');
                profitRatioCard.classList.add('bg-info');
            }
        }
        
    } catch (error) {
        console.error('Error loading portfolio:', error);
    }
}

async function loadAssetsForSelect() {
    try {
        const data = await API.get(Config.ENDPOINTS.ASSETS);
        
        const select = document.getElementById('assetSelect');
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
    const t = TRANSLATIONS[currentLang];
    const formData = new FormData(e.target);
    const data = {
        code: formData.get('code').toUpperCase(),
        name: formData.get('name'),
        type: formData.get('type')
    };
    
    try {
        await API.post(Config.ENDPOINTS.ASSETS, data);
        
        alert(t.alert_asset_added);
        loadAssetsForSelect(); // Refresh list
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
    const t = TRANSLATIONS[currentLang];
    const formData = new FormData(e.target);
    const data = {
        asset_id: parseInt(formData.get('asset_id')),
        quantity: parseFloat(formData.get('quantity')),
        average_cost: parseFloat(formData.get('average_cost'))
    };
    
    try {
        await API.post(Config.ENDPOINTS.TRANSACTION, data);
        
        alert(t.alert_transaction_added);
        loadPortfolio(); // Refresh table
        const modal = bootstrap.Modal.getInstance(document.getElementById('addTransactionModal'));
        modal.hide();
        e.target.reset();

    } catch (error) {
        console.error('Add transaction error:', error);
        alert(t.alert_error);
    }
}
