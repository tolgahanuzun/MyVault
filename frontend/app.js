document.addEventListener('DOMContentLoaded', () => {
    loadPortfolio();
    loadAssetsForSelect();
    
    // Form submit listeners
    document.getElementById('addAssetForm').addEventListener('submit', handleAddAsset);
    document.getElementById('addTransactionForm').addEventListener('submit', handleAddTransaction);
});

// Override global changeLanguage to reload data
const baseChangeLanguage = window.changeLanguage;
window.changeLanguage = function(lang) {
    if (baseChangeLanguage) {
        baseChangeLanguage(lang, loadPortfolio);
    }
}

async function loadPortfolio() {
    try {
        const response = await fetch(`${API_BASE}/portfolio/?user_id=1`);
        const data = await response.json();
        
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
        
        document.getElementById('totalValue').textContent = formatCurrency(totalVal);
        document.getElementById('totalCost').textContent = formatCurrency(totalCost);
        
        const totalProfitEl = document.getElementById('totalProfit');
        totalProfitEl.textContent = `${totalProf >= 0 ? '+' : ''}${formatCurrency(totalProf)}`;
        
        const profitCard = document.getElementById('profitCard');
        if (totalProf < 0) {
            profitCard.classList.remove('bg-success');
            profitCard.classList.add('bg-danger');
        } else {
            profitCard.classList.remove('bg-danger');
            profitCard.classList.add('bg-success');
        }
        
    } catch (error) {
        console.error('Error loading portfolio:', error);
    }
}

async function loadAssetsForSelect() {
    try {
        const response = await fetch(`${API_BASE}/assets/`);
        const data = await response.json();
        
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
        const response = await fetch(`${API_BASE}/assets/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            alert(t.alert_asset_added);
            loadAssetsForSelect(); // Refresh list
            const modal = bootstrap.Modal.getInstance(document.getElementById('addAssetModal'));
            modal.hide();
            e.target.reset();
        } else {
            alert(t.alert_error);
        }
    } catch (error) {
        console.error('Add asset error:', error);
    }
}

async function handleAddTransaction(e) {
    e.preventDefault();
    const t = TRANSLATIONS[currentLang];
    const formData = new FormData(e.target);
    const data = {
        asset_id: parseInt(formData.get('asset_id')),
        quantity: parseFloat(formData.get('quantity')),
        average_cost: parseFloat(formData.get('average_cost')),
        user_id: 1
    };
    
    try {
        const response = await fetch(`${API_BASE}/portfolio/transaction`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            alert(t.alert_transaction_added);
            loadPortfolio(); // Refresh table
            const modal = bootstrap.Modal.getInstance(document.getElementById('addTransactionModal'));
            modal.hide();
            e.target.reset();
        } else {
            alert(t.alert_error);
        }
    } catch (error) {
        console.error('Add transaction error:', error);
    }
}
